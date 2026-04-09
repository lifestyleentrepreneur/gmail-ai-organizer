# Gmail AI Organizer — Guide d'installation pour Claude Code

Ce fichier est destiné à Claude Code. Il contient toutes les instructions pour aider un utilisateur **non-développeur** à installer et configurer ce système.

## Le projet

`organize_inbox.py` est un script Python qui range automatiquement une boîte Gmail. Il utilise l'API Gmail et Claude (Anthropic) pour classer chaque email dans l'une de 8 catégories, archiver le bruit, et mettre une étoile sur les emails importants auxquels l'utilisateur n'a pas encore répondu.

Le script tourne via une tâche planifiée (launchd sur Mac, cron sur Linux, Task Scheduler sur Windows) une fois par jour à 17h.

---

## TON RÔLE (Claude Code)

Tu aides un utilisateur **non-développeur** francophone à installer ce système chez lui. Tu dois :

1. **Parler en français** et utiliser des termes simples. Évite le jargon technique sans l'expliquer.
2. **Ne jamais supposer** que l'utilisateur connaît Python, Git, ou la ligne de commande. Explique chaque commande avant de la lancer.
3. **Demander confirmation** avant toute action qui modifie le système de l'utilisateur ou sa boîte Gmail.
4. **Toujours faire un dry-run avant d'appliquer**. Jamais de `--apply` sans avoir montré le tableau de classification et obtenu l'accord explicite.
5. **Expliquer les erreurs en français simple** et proposer une solution, jamais de jargon technique brut.
6. **Faire un récap final** avec tout ce qui a été installé, où c'est situé, et comment vérifier que ça marche.

Ne lance pas tout d'un coup. Procède section par section et attends que l'utilisateur confirme avant de passer à la suivante.

---

## WORKFLOW D'INSTALLATION

### Étape 1 — Récupérer le contexte utilisateur

Demande à l'utilisateur :

- **Son adresse Gmail** (pour l'authentification OAuth plus tard)
- **Son activité / métier** en 1 à 3 phrases (ex: "Je suis photographe freelance, je travaille avec des mariés et des entreprises pour des shootings corporate")
- **Les types d'emails qu'il reçoit** principalement (ex: "Demandes de clients, factures de sous-traitants, newsletters photo, notifications Instagram")
- **Son système d'exploitation** (macOS, Linux, ou Windows)

Garde ces infos de côté — tu en auras besoin aux étapes 5 et 8.

### Étape 2 — Installer les dépendances Python

Vérifie que Python 3.9+ est installé :

```bash
python3 --version
```

Si ce n'est pas le cas, guide l'utilisateur pour l'installer :
- **macOS** : `brew install python@3.11` (ou via python.org)
- **Windows** : télécharger depuis https://www.python.org/downloads/
- **Linux** : `sudo apt install python3 python3-pip` (Debian/Ubuntu)

Puis installe les dépendances :

```bash
pip3 install -r requirements.txt
```

Si `pip3 install` échoue avec une erreur "externally-managed-environment", ajoute `--break-system-packages` (macOS récents) ou utilise un venv.

### Étape 3 — Créer les identifiants OAuth Google (LA PARTIE LA PLUS DURE)

C'est l'étape la plus délicate pour un non-dev. Prends ton temps, guide l'utilisateur clic par clic. Voici la procédure :

1. **Ouvrir Google Cloud Console** : https://console.cloud.google.com
2. **Se connecter** avec le compte Google de l'utilisateur (le même que son Gmail).
3. **Créer un projet** :
   - Menu en haut à gauche → "Sélectionner un projet" → "NOUVEAU PROJET"
   - Nom suggéré : `gmail-ai-organizer`
   - Cliquer "CRÉER"
   - Attendre quelques secondes, puis sélectionner ce projet.
4. **Activer l'API Gmail** :
   - Menu → "APIs et services" → "Bibliothèque"
   - Chercher "Gmail API"
   - Cliquer dessus → "ACTIVER"
5. **Configurer l'écran de consentement OAuth** :
   - Menu → "APIs et services" → "Écran de consentement OAuth"
   - Type d'utilisateur : "Externe" → "CRÉER"
   - Nom de l'application : `Gmail Organizer`
   - Email d'assistance : l'email de l'utilisateur
   - Coordonnées du développeur : l'email de l'utilisateur
   - Cliquer "ENREGISTRER ET CONTINUER" jusqu'à "Utilisateurs de test"
   - **Ajouter l'email Gmail de l'utilisateur comme utilisateur de test** (important, sinon OAuth refuse la connexion)
   - Enregistrer.
6. **Créer les identifiants OAuth** :
   - Menu → "APIs et services" → "Identifiants"
   - "+ CRÉER DES IDENTIFIANTS" → "ID client OAuth"
   - Type d'application : **"Application de bureau"** (important, pas "Application Web")
   - Nom : `Gmail Organizer Desktop`
   - Cliquer "CRÉER"
7. **Télécharger le fichier JSON** :
   - Cliquer sur l'icône de téléchargement à côté de l'ID client qui vient d'être créé
   - Sauvegarder le fichier
   - **Renommer le fichier en `credentials.json`**
   - **Le déplacer dans le dossier du projet** (le même dossier que `organize_inbox.py` et ce fichier CLAUDE.md)

Une fois `credentials.json` en place, vérifie avec :

```bash
ls credentials.json
```

Si le fichier n'est pas là, aide l'utilisateur à le retrouver et le déplacer.

### Étape 4 — Obtenir la clé API Anthropic et configurer .env

1. Ouvrir https://console.anthropic.com
2. Créer un compte ou se connecter.
3. **Ajouter du crédit sur le compte** (minimum 5 $). Sans crédit, l'API ne répond pas.
4. Aller dans "API Keys" dans le menu.
5. "Create Key" → nommer par exemple `gmail-organizer` → copier la clé (elle commence par `sk-ant-`).
6. **Créer le fichier `.env`** dans le dossier du projet en copiant `.env.example` :

```bash
cp .env.example .env
```

7. Ouvrir `.env` et remplir les deux variables :

```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
USER_EMAIL=son.adresse@gmail.com
```

**Important :**
- `ANTHROPIC_API_KEY` est la clé qu'il vient de créer sur console.anthropic.com
- `USER_EMAIL` est son adresse Gmail (celle que tu as récupérée à l'étape 1). Cette variable sert à détecter les conversations où l'utilisateur n'a pas encore répondu — sans elle, la fonction "étoiler les emails importants sans réponse" sera désactivée.

### Étape 5 — Adapter le prompt de classification au business de l'utilisateur

Ouvre `organize_inbox.py` et trouve la variable `CLASSIFICATION_SYSTEM_PROMPT` (vers la ligne 58).

Le prompt actuel est adapté à un consultant AI. Il faut le remplacer par le contexte de l'utilisateur. Remplace ce bloc :

```
Tu es un assistant qui classe des emails pour Farel Vignon Honvoh, consultant AI basé en Turquie (farel@honvoh.com).

Contexte business:
- Il envoie des messages de prospection (cold outreach) à des créateurs YouTube en anglais
- Il a des clients actifs (consulting AI, scripting YouTube, automatisation)
- Il reçoit des emails en français et en anglais
```

Par quelque chose qui colle à l'utilisateur, basé sur ce qu'il t'a dit à l'étape 1. Exemple pour un photographe freelance :

```
Tu es un assistant qui classe des emails pour [PRÉNOM NOM], photographe freelance basé à [VILLE] ([EMAIL]).

Contexte business:
- Shootings de mariage et corporate
- Clients particuliers et entreprises
- Sous-traite parfois avec des photographes assistants
- Reçoit des demandes de devis, des confirmations de paiement, et beaucoup de newsletters photo
```

Regarde aussi les 8 catégories (liste `LABELS` vers la ligne 44) et propose à l'utilisateur de les ajuster si c'est pertinent. Par exemple, un photographe pourrait remplacer "Outreach - Réponses" par "Demandes de shooting" et "Administratif" par "Sous-traitants".

**Montre les changements à l'utilisateur avant de sauvegarder.** Demande-lui s'il veut modifier autre chose.

### Étape 6 — Test en mode dry-run

Lance :

```bash
python3 organize_inbox.py --max-emails 20
```

**La première fois, ça va ouvrir un navigateur** pour l'authentification Google OAuth. L'utilisateur devra :
- Choisir son compte Google
- Cliquer "Continuer" malgré l'avertissement "L'application n'est pas validée par Google" (c'est normal, c'est son propre projet perso)
- Cocher les permissions demandées
- Cliquer "Continuer"

Un fichier `token_gmail_organize.json` sera créé automatiquement — c'est normal, c'est la session OAuth sauvegardée.

Le script va ensuite afficher un **tableau de classification** pour les 20 derniers emails, sans rien modifier. Regarde ce tableau avec l'utilisateur :

- Est-ce que les catégories assignées sont correctes ?
- Est-ce qu'il y a des surprises ?

Si c'est bon, passe à l'étape 7. Sinon, retourne à l'étape 5 et ajuste le prompt jusqu'à ce que les classifications correspondent aux attentes.

### Étape 7 — Premier run réel

**Avertis l'utilisateur** : ce qui va suivre va VRAIMENT classer, labelliser et archiver ses emails. Demande confirmation explicite.

Lance :

```bash
python3 organize_inbox.py --max-emails 100 --apply
```

Montre la sortie à l'utilisateur. Il devrait voir dans son Gmail :
- Les 8 labels qui apparaissent dans la barre latérale
- Les emails rangés dans leurs catégories
- Les emails importants sans réponse qui sont étoilés

Si ça n'a pas marché comme prévu, dé-archive manuellement les emails concernés dans Gmail et retourne à l'étape 5 pour ajuster.

### Étape 8 — Planifier le script pour qu'il tourne tous les jours

Selon le système de l'utilisateur :

#### Sur macOS (launchd)

1. Ouvre `com.honvoh.gmail-organizer.plist.template` et remplace les placeholders :
   - `__PYTHON_PATH__` → résultat de `which python3`
   - `__SCRIPT_DIR__` → chemin absolu du dossier du projet
   - `__SCRIPT_PATH__` → chemin absolu vers `organize_inbox.py`
   - `__LOG_PATH__` → chemin vers un fichier de log (ex: `[SCRIPT_DIR]/organize_inbox.log`)
2. Sauvegarde le fichier sous un nouveau nom : `com.honvoh.gmail-organizer.plist` (sans `.template`).
3. Copie-le dans `~/Library/LaunchAgents/` :

```bash
cp com.honvoh.gmail-organizer.plist ~/Library/LaunchAgents/
```

4. Charge-le dans launchd :

```bash
launchctl load ~/Library/LaunchAgents/com.honvoh.gmail-organizer.plist
```

5. Vérifie qu'il est bien chargé :

```bash
launchctl list | grep honvoh
```

#### Sur Linux (cron)

1. Ouvre crontab :

```bash
crontab -e
```

2. Ajoute cette ligne (remplace les chemins par les vrais) :

```
0 17 * * * /usr/bin/python3 /chemin/absolu/vers/organize_inbox.py --apply --max-emails 200 >> /chemin/absolu/vers/organize_inbox.log 2>&1
```

3. Sauvegarde et quitte.

#### Sur Windows (Task Scheduler)

1. Ouvrir le "Planificateur de tâches".
2. Créer une tâche de base.
3. Nom : `Gmail AI Organizer`
4. Déclencheur : Quotidien à 17h00.
5. Action : Démarrer un programme
   - Programme : `python` (ou le chemin complet vers python.exe)
   - Arguments : `organize_inbox.py --apply --max-emails 200`
   - Commencer dans : le chemin absolu du dossier du projet.
6. Terminer.

### Étape 9 — Récap final

Une fois tout installé, donne un récap à l'utilisateur :

- **Où est le script** : `[chemin absolu]/organize_inbox.py`
- **Quand il tourne** : tous les jours à 17h
- **Où sont les logs** : `[chemin vers le log]`
- **Comment vérifier demain** : ouvrir le log, ou regarder Gmail pour voir les nouveaux emails classés
- **Comment désactiver** : `launchctl unload ~/Library/LaunchAgents/com.honvoh.gmail-organizer.plist` (macOS) ou supprimer la ligne crontab (Linux), ou supprimer la tâche dans Task Scheduler (Windows)
- **Coût estimé** : environ 7 $ par mois sur la clé API Anthropic

Demande à l'utilisateur si tout est clair et s'il a des questions.

---

## DÉPANNAGE (erreurs courantes)

### "credentials.json not found"
L'utilisateur n'a pas téléchargé ou n'a pas placé le fichier au bon endroit. Retour à l'étape 3, point 7.

### "Anthropic API key not found" ou "401 Unauthorized"
Le fichier `.env` n'existe pas, ou la clé est incorrecte. Vérifier :
```bash
cat .env
```
La clé doit commencer par `sk-ant-api03-`.

### "Access blocked: Gmail Organizer has not completed the Google verification process"
L'utilisateur n'a pas ajouté son email comme utilisateur de test. Retour à l'étape 3, point 5.

### "ModuleNotFoundError: No module named 'googleapiclient'"
Les dépendances n'ont pas été installées. Retour à l'étape 2.

### "Quota exceeded"
Rare, mais peut arriver si l'utilisateur lance le script plusieurs fois rapidement. Attendre quelques minutes et réessayer.

### Les classifications sont mauvaises
Le prompt de l'étape 5 n'est pas bien adapté. Demander à l'utilisateur ce qui est mal classé, et ajuster le contexte business ou les catégories.

---

## MODIFICATIONS AVANCÉES (après installation)

Si l'utilisateur veut plus tard modifier le comportement, voici les points clés du code :

- **`LABELS`** (ligne ~44) : les 8 catégories et leurs noms Gmail
- **`CLASSIFICATION_SYSTEM_PROMPT`** (ligne ~58) : le prompt envoyé à Claude
- **`ARCHIVE_CATEGORIES`** (ligne ~56) : quelles catégories sont automatiquement archivées
- **`FLAG_CATEGORIES`** (ligne ~345) : quelles catégories déclenchent l'étoilage si non répondues
- **`BATCH_SIZE`** (ligne ~89) : combien d'emails envoyés par appel Claude (10 par défaut, peut être augmenté pour réduire le coût)
- **`BODY_MAX_CHARS`** (ligne ~90) : combien de caractères du corps d'email envoyés à Claude (500 par défaut)

---

## RAPPEL FINAL

- **Français simple**. Pas de jargon technique sans explication.
- **Confirmation** avant toute action destructive.
- **Dry-run** avant apply, toujours.
- **Récap** à la fin, clair et complet.
- **Soit patient** sur l'étape 3 (OAuth Google) — c'est la plus frustrante, mais la plus importante.
