#!/usr/bin/env python3
"""
Organise automatiquement la boîte Gmail en appliquant des labels
via classification intelligente (Claude Sonnet).

Usage:
  # Dry run (défaut) — affiche les classifications sans rien modifier
  python3 organize_inbox.py --max-emails 20

  # Appliquer les labels
  python3 organize_inbox.py --max-emails 50 --apply

  # Appliquer sans archiver
  python3 organize_inbox.py --apply --skip-archive

  # Depuis une date
  python3 organize_inbox.py --apply --since 2026-03-01
"""

import os
import sys
import json
import time
import base64
import argparse
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import anthropic

# ── Config ──────────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token_gmail_organize.json")

LABELS = {
    "notifications":  "🔔 Notifications",
    "outreach":       "📤 Outreach - Réponses",
    "demandes":       "🤝 Demandes & Partenariats",
    "paiements":      "💰 Paiements & Factures",
    "clients":        "👥 Clients",
    "reunions":       "📅 Réunions",
    "administratif":  "🏛️ Administratif",
    "autre":          "📁 Autre",
}

# All categorized emails get archived (removed from inbox, live in their label)
ARCHIVE_CATEGORIES = set(LABELS.keys())

CLASSIFICATION_SYSTEM_PROMPT = """Tu es un assistant qui classe des emails pour Farel Vignon Honvoh, consultant AI basé en Turquie (farel@honvoh.com).

Contexte business:
- Il envoie des messages de prospection (cold outreach) à des créateurs YouTube en anglais
- Il a des clients actifs (consulting AI, scripting YouTube, automatisation)
- Il reçoit des emails en français et en anglais

Classe chaque email dans UNE SEULE catégorie parmi:

1. "notifications" — Alertes réseaux sociaux, newsletters, emails marketing, notifications automatiques de services (GitHub, Vercel, Slack, LinkedIn notifs, promotions, etc.)

2. "outreach" — Réponses à ses messages de prospection. Indices: Re: dans le sujet + référence à une analyse de chaîne, un rapport gratuit, une proposition de call, ou un créateur YouTube qui répond à un premier contact.

3. "demandes" — Demandes entrantes: quelqu'un qui contacte Farel pour une collaboration, un partenariat, une demande de devis, une opportunité business, ou une question sur ses services.

4. "paiements" — Factures, confirmations de paiement, reçus Stripe/PayPal/Wise, relevés bancaires, rappels de paiement.

5. "clients" — Communications directes avec des clients actifs ou récents: suivi de projet, feedback, livrables, questions sur le travail en cours. PAS les notifications Zoom/Google Meet.

6. "reunions" — Notifications de réunions et visioconférences: invitations Zoom, Google Meet, rappels de meeting, enregistrements de réunion, ressources post-réunion, Transkriptor, récapitulatifs de call. Tout ce qui concerne la logistique des meetings.

7. "administratif" — Emails administratifs: banque, gouvernement, impôts, hébergement, domaines, renouvellements, sécurité de compte, vérification d'identité.

8. "autre" — Emails utiles qui ne rentrent dans aucune autre catégorie.

Réponds UNIQUEMENT avec un tableau JSON. Chaque entrée:
{"id": "email_id", "category": "category_key", "confidence": 0-100, "reason": "explication courte en français"}

Si la confiance est < 40, classe en "autre".
En cas de doute entre deux catégories, choisis la plus spécifique."""

BATCH_SIZE = 10
BODY_MAX_CHARS = 500

# ── Auth ────────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# ── Labels ──────────────────────────────────────────────────────────────────

def get_existing_labels(service):
    results = service.users().labels().list(userId="me").execute()
    return {l["name"]: l["id"] for l in results.get("labels", [])}


def ensure_labels(service):
    """Create missing labels, return {category_key: gmail_label_id}."""
    existing = get_existing_labels(service)
    label_ids = {}

    for key, name in LABELS.items():
        if name in existing:
            label_ids[key] = existing[name]
        else:
            body = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            result = service.users().labels().create(userId="me", body=body).execute()
            label_ids[key] = result["id"]
            print(f"  Label créé: {name}")

    return label_ids


def get_our_label_ids(label_ids):
    """Return set of all our label IDs for skip-detection."""
    return set(label_ids.values())


# ── Email Fetching ──────────────────────────────────────────────────────────

def get_email_body(msg):
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])

    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for part in parts:
        for subpart in part.get("parts", []):
            if subpart.get("mimeType") == "text/plain":
                data = subpart.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""


def fetch_emails(service, max_emails, since_date=None):
    """Fetch inbox emails, return list of dicts with id, from, subject, date, body."""
    query = "in:inbox"
    if since_date:
        query += f" after:{since_date}"

    emails = []
    page_token = None

    while len(emails) < max_emails:
        batch_size = min(100, max_emails - len(emails))
        result = service.users().messages().list(
            userId="me", q=query, maxResults=batch_size, pageToken=page_token
        ).execute()

        messages = result.get("messages", [])
        if not messages:
            break

        for msg_ref in messages:
            if len(emails) >= max_emails:
                break
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            body = get_email_body(msg)

            emails.append({
                "id": msg["id"],
                "label_ids": msg.get("labelIds", []),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", "(sans objet)"),
                "date": headers.get("Date", ""),
                "body": body[:BODY_MAX_CHARS],
            })

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return emails


def filter_already_labeled(emails, our_label_ids):
    """Skip emails that already have one of our labels."""
    filtered = []
    skipped = 0
    for email in emails:
        if our_label_ids.intersection(set(email["label_ids"])):
            skipped += 1
        else:
            filtered.append(email)
    return filtered, skipped


# ── Classification ──────────────────────────────────────────────────────────

def classify_batch(emails_batch, client):
    """Send a batch of emails to Claude for classification."""
    email_descriptions = []
    for i, email in enumerate(emails_batch):
        email_descriptions.append(
            f"--- Email {i+1} ---\n"
            f"ID: {email['id']}\n"
            f"De: {email['from']}\n"
            f"Objet: {email['subject']}\n"
            f"Date: {email['date']}\n"
            f"Corps (extrait): {email['body']}\n"
        )

    user_message = (
        f"Classe ces {len(emails_batch)} emails. "
        f"Réponds UNIQUEMENT avec le tableau JSON.\n\n"
        + "\n".join(email_descriptions)
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=CLASSIFICATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()
    # Extract JSON from potential markdown code blocks
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    parsed = json.loads(text)
    # Re-map IDs from original batch (Claude may mangle IDs)
    for idx, item in enumerate(parsed):
        if idx < len(emails_batch):
            item["id"] = emails_batch[idx]["id"]
    return parsed


def classify_all(emails, client, verbose=False):
    """Classify all emails in batches, return list of {id, category, confidence, reason}."""
    results = []

    for i in range(0, len(emails), BATCH_SIZE):
        batch = emails[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(emails) + BATCH_SIZE - 1) // BATCH_SIZE

        if verbose:
            print(f"\n  Classification batch {batch_num}/{total_batches} ({len(batch)} emails)...")

        try:
            batch_results = classify_batch(batch, client)
            for r in batch_results:
                if r.get("category") not in LABELS:
                    r["category"] = "autre"
            results.extend(batch_results)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  Erreur batch {batch_num}: {e}")
            # Fallback: classify as "autre"
            for email in batch:
                results.append({
                    "id": email["id"],
                    "category": "autre",
                    "confidence": 0,
                    "reason": f"Erreur de classification: {e}",
                })

        if i + BATCH_SIZE < len(emails):
            time.sleep(0.5)

    return results


# ── Label Application ───────────────────────────────────────────────────────

def apply_labels(service, classifications, label_ids, skip_archive=False, verbose=False):
    """Apply Gmail labels based on classifications."""
    applied = 0
    archived = 0

    for cls in classifications:
        category = cls.get("category", "autre")
        if category not in label_ids:
            category = "autre"

        gmail_label_id = label_ids[category]
        msg_id = cls["id"]

        add_labels = [gmail_label_id]
        remove_labels = []

        if not skip_archive and category in ARCHIVE_CATEGORIES:
            remove_labels.append("INBOX")
            archived += 1

        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": add_labels, "removeLabelIds": remove_labels},
        ).execute()
        applied += 1

        if verbose:
            action = "labellé + archivé" if remove_labels else "labellé"
            print(f"    {action}: {cls.get('reason', '')[:60]}")

        time.sleep(0.05)  # Rate limit safety

    return applied, archived


# ── Flag Unreplied ──────────────────────────────────────────────────────────

# Categories that should be flagged if unreplied
FLAG_CATEGORIES = {"clients", "demandes", "outreach"}

MY_EMAIL = os.getenv("USER_EMAIL", "").strip().lower()


def check_unreplied_and_flag(service, classifications, emails, verbose=False):
    """Star emails in important categories that haven't been replied to."""
    if not MY_EMAIL:
        print("  ⚠️  USER_EMAIL not set in .env — skipping the unreplied check.")
        print("     Add USER_EMAIL=your@email.com to .env to enable auto-starring.")
        return 0

    # Build email lookup
    email_map = {e["id"]: e for e in emails}
    flagged = 0

    for cls in classifications:
        category = cls.get("category", "autre")
        if category not in FLAG_CATEGORIES:
            continue

        msg_id = cls["id"]

        # Get the full message to find its threadId
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="metadata", metadataHeaders=["From"]
        ).execute()
        thread_id = msg.get("threadId")

        # Get all messages in the thread
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata", metadataHeaders=["From"]
        ).execute()
        thread_messages = thread.get("messages", [])

        # Check if any message in the thread is from us (reply sent)
        replied = False
        for tmsg in thread_messages:
            headers = {h["name"]: h["value"] for h in tmsg["payload"].get("headers", [])}
            sender = headers.get("From", "")
            if MY_EMAIL in sender.lower():
                replied = True
                break

        if not replied:
            # Star the message
            service.users().messages().modify(
                userId="me", id=msg_id,
                body={"addLabelIds": ["STARRED"]},
            ).execute()
            flagged += 1

            if verbose:
                email = email_map.get(msg_id, {})
                print(f"    ⭐ {LABELS.get(category, category)}: {email.get('subject', '')[:55]}")

            time.sleep(0.05)

    return flagged


# ── Display ─────────────────────────────────────────────────────────────────

def print_classifications(emails, classifications):
    """Print a table of classifications for dry-run review."""
    # Build lookup
    cls_map = {c["id"]: c for c in classifications}

    print(f"\n{'='*90}")
    print(f"{'Catégorie':<28} {'Conf':>4}  {'De':<25} {'Objet'}")
    print(f"{'='*90}")

    for email in emails:
        cls = cls_map.get(email["id"], {})
        category = cls.get("category", "?")
        confidence = cls.get("confidence", 0)
        label_name = LABELS.get(category, category)
        sender = email["from"][:24]
        subject = email["subject"][:35]

        print(f"{label_name:<28} {confidence:>3}%  {sender:<25} {subject}")

    print(f"{'='*90}")

    # Summary
    counts = {}
    for cls in classifications:
        cat = cls.get("category", "autre")
        counts[cat] = counts.get(cat, 0) + 1

    print("\nRésumé:")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {LABELS.get(cat, cat)}: {count}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Organiser la boîte Gmail avec classification AI")
    parser.add_argument("--max-emails", type=int, default=20, help="Nombre max d'emails à traiter (défaut: 20)")
    parser.add_argument("--apply", action="store_true", help="Appliquer les labels (sinon dry-run)")
    parser.add_argument("--skip-archive", action="store_true", help="Ne pas archiver, juste labelliser")
    parser.add_argument("--since", type=str, help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true", help="Afficher les détails")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n{'='*50}")
    print(f"  Gmail Inbox Organizer — Mode: {mode}")
    print(f"  Max emails: {args.max_emails}")
    if args.since:
        print(f"  Depuis: {args.since}")
    print(f"{'='*50}\n")

    # Auth
    print("Connexion Gmail...")
    service = get_gmail_service()

    # Ensure labels exist
    print("Vérification des labels...")
    label_ids = ensure_labels(service)
    our_ids = get_our_label_ids(label_ids)
    print(f"  {len(label_ids)} labels prêts")

    # Fetch emails
    print(f"\nRécupération des emails (max {args.max_emails})...")
    emails = fetch_emails(service, args.max_emails, since_date=args.since)
    print(f"  {len(emails)} emails récupérés")

    # Filter already labeled
    emails, skipped = filter_already_labeled(emails, our_ids)
    if skipped:
        print(f"  {skipped} emails déjà organisés (ignorés)")

    if not emails:
        print("\nAucun email à traiter.")
        return

    print(f"  {len(emails)} emails à classifier")

    # Classify with Claude
    print("\nClassification avec Claude...")
    client = anthropic.Anthropic()
    classifications = classify_all(emails, client, verbose=args.verbose)

    # Display results
    print_classifications(emails, classifications)

    # Apply if requested
    if args.apply:
        print(f"\nApplication des labels...")
        applied, archived = apply_labels(
            service, classifications, label_ids,
            skip_archive=args.skip_archive, verbose=args.verbose
        )
        print(f"\nTerminé: {applied} emails labellisés, {archived} archivés")

        # Flag unreplied important emails
        print("\nVérification des emails importants sans réponse...")
        flagged = check_unreplied_and_flag(
            service, classifications, emails, verbose=args.verbose
        )
        if flagged:
            print(f"  ⭐ {flagged} emails marqués comme importants (sans réponse)")
        else:
            print("  Aucun email important sans réponse")
    else:
        print(f"\n[DRY-RUN] Aucune modification. Relancez avec --apply pour appliquer.")


if __name__ == "__main__":
    main()
