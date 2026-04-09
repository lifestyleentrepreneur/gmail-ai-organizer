# Gmail AI Organizer

Un script Python qui range automatiquement ta boîte Gmail chaque jour, avec l'aide de Claude AI. Il classe chaque email dans la bonne catégorie, archive le bruit, et met une étoile sur les emails importants auxquels tu n'as pas encore répondu.

Pas besoin d'y toucher une fois installé — ça tourne tout seul à l'heure que tu choisis.

## Installation (avec Claude Code)

Ce projet est conçu pour être installé via **Claude Code**, sans que tu aies besoin de savoir coder.

### Ce qu'il te faut avant de commencer

- Un compte Gmail
- Un compte Google Cloud (gratuit) pour activer l'API Gmail
- Une clé API Anthropic (≈ 5 $ de crédit minimum — coûte ensuite environ 7 $/mois en usage quotidien)
- Claude Code installé sur ton ordinateur → https://claude.com/claude-code
- Python 3.9 ou plus récent

### Les 3 étapes

**1. Télécharge ce projet**

Clique sur "Code" → "Download ZIP" en haut de la page GitHub, puis dézippe le fichier sur ton bureau ou dans ton dossier Documents.

**2. Ouvre Claude Code dans le dossier**

Ouvre ton terminal (sur Mac : Applications → Utilitaires → Terminal), puis :

```bash
cd ~/Desktop/gmail-ai-organizer
claude
```

(Remplace le chemin par celui de ton dossier)

**3. Dis à Claude Code d'installer le système**

Colle ce message :

> Installe ce système pour moi, étape par étape. Lis d'abord CLAUDE.md pour comprendre le projet, puis guide-moi tout au long de l'installation. Mon email Gmail est **[ton email]**. Mon activité : **[1-2 phrases sur ton business]**. Je ne suis pas développeur — explique chaque étape simplement et demande-moi confirmation avant toute action qui modifie ma boîte Gmail ou mon système.

Claude Code va ensuite te guider clic par clic pour :

- Installer les dépendances Python
- Créer les identifiants Google OAuth (la partie la plus délicate, mais Claude Code te tient la main)
- Configurer ta clé Anthropic
- Adapter les catégories et le prompt à ton business
- Tester sur 20 emails (sans rien modifier)
- Lancer le tri pour de vrai après ta confirmation
- Planifier le script pour qu'il tourne chaque jour à 17h automatiquement

## Les 8 catégories par défaut

Le script classe les emails dans 8 catégories. Claude Code t'aidera à les adapter à ton business au moment de l'installation.

| Catégorie | Ce qu'elle contient | Étoilé si sans réponse ? |
|---|---|---|
| Notifications | Alertes réseaux sociaux, newsletters, emails automatiques | Non |
| Outreach - Réponses | Réponses à tes messages de prospection | Oui |
| Demandes & Partenariats | Demandes entrantes, collaborations, devis | Oui |
| Paiements & Factures | Stripe, PayPal, Wise, factures, reçus | Non |
| Clients | Communications avec tes clients actifs | Oui |
| Réunions | Invitations Zoom, Meet, rappels | Non |
| Administratif | Banque, impôts, hébergement, sécurité | Non |
| Autre | Ce qui ne rentre nulle part ailleurs | Non |

## Coût

Environ **7 $ par mois** (moins qu'un café par semaine) pour traiter 200 emails par jour. C'est ce que coûtent les appels à l'API Anthropic — pas d'abonnement, pas d'autre frais.

## Tu ne veux pas l'installer toi-même ?

Je peux te le construire sur-mesure et adapter les catégories et le prompt à ton business. Réserve un appel gratuit de 20 minutes :

**→ https://cal.eu/honvoh/decouverte**

## Licence

Ce code est fourni librement. Fais-en ce que tu veux — adapte-le, modifie-le, redistribue-le.
