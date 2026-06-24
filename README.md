# 🏗️ EPC AutoAppelOffre

Système automatisé de **veille sur les appels d'offre publics** (BOAMP) pour EPC France.

Chaque jour, le script interroge la base nationale BOAMP, note chaque annonce selon un barème de mots-clés métier, et envoie par email un rapport HTML des marchés les plus pertinents pour les activités d'EPC (micropieux, soutènement, travaux géotechniques, etc.).

---

## 📋 Sommaire

- [Comment ça marche](#-comment-ça-marche)
- [Modifier les mots-clés et le scoring](#️-modifier-les-mots-clés-et-le-scoring-fichier-configpy)
- [Modifier la zone géographique](#-modifier-la-zone-géographique)
- [Modifier le destinataire email](#-modifier-le-destinataire-email)
- [Variables d'environnement](#-variables-denvironnement-fichier-env)
- [Mettre en place l'automatisation GitHub Actions](#-automatisation-github-actions)
- [Lancer le script manuellement](#-lancer-le-script-manuellement)
- [Dépannage](#-dépannage)
- [Architecture du projet](#-architecture-du-projet)

---

## 🔄 Comment ça marche

```
API BOAMP (boamp-datadila.opendatasoft.com)
        │
        ▼
  Recherche par mots-clés discriminants
  (micropieux, soutènement, paroi berlinoise…)
        │
        ▼
  Filtrage géographique
  (PACA, Occitanie, Nouvelle-Aquitaine)
        │
        ▼
  Scoring par mots-clés (0 à ~50 pts)
        │
        ▼
  Seuil : score ≥ 8 → inclus dans l'email
        │
        ▼
  Email HTML récapitulatif envoyé au(x) destinataire(s)
```

---

## ⚙️ Modifier les mots-clés et le scoring (fichier `config.py`)

> **Pas besoin de toucher au code** : tout ce qui concerne la pertinence métier est centralisé dans `config.py`.

### Où trouver le fichier

Dans le repo GitHub : cliquer sur `config.py` à la racine.

### Les mots-clés (`KEYWORDS_SCORING`)

C'est un dictionnaire `"mot-clé": points`. Plus le score est élevé, plus le terme est considéré comme pertinent pour EPC.

```python
KEYWORDS_SCORING = {
    # Cœur de métier → 10 pts
    "micropieux": 10,
    "soutènement": 10,
    "paroi berlinoise": 10,
    "paroi clouée": 10,

    # Très pertinent → 8-9 pts
    "confortement": 9,
    "tirant d'ancrage": 9,
    "protection de talus": 9,
    "béton projeté": 8,
    "travaux acrobatiques": 8,

    # Pertinent mais contextuel → 5-6 pts
    "géotechnique": 6,
    "forage": 5,
    "talus": 5,

    # Faible / ambigu → 2-4 pts
    "fondation": 3,
    "terrassement": 2,
}
```

**Ajouter un mot-clé :** il suffit d'ajouter une ligne dans ce bloc, en respectant le format `"terme": score,`.

Exemple — ajouter "jet grouting" avec un score de 9 :
```python
"jet grouting": 9,
```

> ⚠️ Le script gère automatiquement les accents, la casse et le pluriel (micropieux/micropieu, soutènement/soutenement…). Inutile de dupliquer les variantes.

### Les termes envoyés à l'API (`SEARCH_TERMS`)

Cette liste contrôle ce qui est recherché côté serveur BOAMP (pré-filtrage). Elle doit contenir uniquement des termes **discriminants** — pas de mots trop génériques comme "fondation" ou "renforcement" qui remonteraient des milliers d'annonces hors sujet.

```python
SEARCH_TERMS = [
    "micropieux", "pieux",
    "paroi berlinoise", "micro-berlinoise", "paroi clouée",
    "soutènement", "confortement",
    "tirant d'ancrage",
    "protection de talus", "stabilisation de talus",
    "travaux acrobatiques", "travaux sur cordes",
    "falaise", "éboulement",
    # Ajouter ici si besoin…
]
```

### Les seuils de score

```python
SCORE_THRESHOLD_KEEP = 6       # Score minimum pour être loggé (mais pas forcément envoyé)
SCORE_THRESHOLD_FOR_EMAIL = 8  # Score minimum pour apparaître dans l'email
```

- **Trop de résultats peu pertinents dans l'email** → monter `SCORE_THRESHOLD_FOR_EMAIL` à 10 ou 12.
- **Pas assez de résultats** → descendre à 6 ou 7.

---

## 🗺️ Modifier la zone géographique

Dans `config.py`, la section `GEO_FILTER_ENABLED` et `SOUTH_DEPARTMENTS` :

```python
GEO_FILTER_ENABLED = True   # Mettre False pour chercher sur toute la France

GEO_KEEP_UNKNOWN = True     # Garder les annonces sans département identifiable
                             # (marchés nationaux, multi-régions…)

SOUTH_DEPARTMENTS = {
    # PACA
    "04", "05", "06", "13", "83", "84",
    # Occitanie
    "09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82",
    # Nouvelle-Aquitaine
    "16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87",
}
```

Pour ajouter une région, il suffit d'ajouter les numéros de départements correspondants entre guillemets, séparés par des virgules.

---

## 📧 Modifier le destinataire email

Dans `config.py` :

```python
EMAIL_RECIPIENT = "luc.deldem@epc-france.com"
```

Remplacer par l'adresse souhaitée. Pour envoyer à plusieurs personnes, séparer les adresses par une virgule :

```python
EMAIL_RECIPIENT = "direction@epc-france.com, commercial@epc-france.com"
```

---

## 🔐 Variables d'environnement (fichier `.env`)

Le script a besoin de credentials email pour envoyer le rapport. Ces informations **ne doivent jamais être écrites directement dans le code** — elles sont stockées dans un fichier `.env` (en local) ou dans les Secrets GitHub (pour l'automatisation).

### En local

Créer un fichier `.env` à la racine du projet (copier `.env.example` comme base) :

```env
SENDER_EMAIL=votre-adresse@gmail.com
SENDER_PASSWORD=xxxx xxxx xxxx xxxx   # Mot de passe d'application Gmail (voir ci-dessous)
SMTP_HOST=smtp.gmail.com              # Optionnel, smtp.gmail.com par défaut
SMTP_PORT=587                         # Optionnel, 587 par défaut
```

> ⚠️ Le fichier `.env` est listé dans `.gitignore` : il ne sera jamais envoyé sur GitHub. Ne pas le partager.

#### Obtenir un mot de passe d'application Gmail

Gmail n'accepte pas votre mot de passe habituel pour les scripts automatiques. Il faut générer un **mot de passe d'application** (16 caractères) :

1. Aller sur [myaccount.google.com/security](https://myaccount.google.com/security)
2. Activer la **validation en 2 étapes** si ce n'est pas déjà fait
3. Chercher "Mots de passe des applications" (ou aller directement sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))
4. Créer un nouveau mot de passe, nommer-le "EPC AutoAppelOffre"
5. Copier le code généré (format `xxxx xxxx xxxx xxxx`) dans la variable `SENDER_PASSWORD`

---

## ⚡ Automatisation GitHub Actions

GitHub Actions permet d'exécuter le script automatiquement tous les jours, sans qu'un ordinateur soit allumé.

### Étape 1 — Placer le fichier workflow au bon endroit

> ⚠️ **Point critique** : GitHub n'exécute les workflows que s'ils se trouvent dans `.github/workflows/`. Le fichier `daily-run.yml` actuellement à la racine du repo **ne sera pas détecté**.

Il faut le déplacer :
```
.github/
  workflows/
    daily-run.yml    ← le fichier doit être ici
```

Pour faire ça sur GitHub directement :
1. Cliquer sur `daily-run.yml` dans le repo
2. Cliquer sur l'icône crayon (Edit)
3. Modifier le nom du fichier en haut : écrire `.github/workflows/daily-run.yml`
4. Valider avec "Commit changes"

### Étape 2 — Ajouter les Secrets GitHub

Les credentials email doivent être stockés dans les **Secrets** du repo (chiffrés, jamais visibles) :

1. Aller sur la page du repo GitHub
2. Cliquer sur **Settings** (onglet en haut)
3. Dans le menu gauche : **Secrets and variables** → **Actions**
4. Cliquer sur **New repository secret** pour chaque variable :

| Nom du secret | Valeur |
|---|---|
| `SENDER_EMAIL` | L'adresse Gmail utilisée pour envoyer |
| `SENDER_PASSWORD` | Le mot de passe d'application Gmail |
| `SMTP_HOST` | `smtp.gmail.com` (optionnel, valeur par défaut) |
| `SMTP_PORT` | `587` (optionnel, valeur par défaut) |

> Les secrets ne sont jamais affichés en clair, même pour les administrateurs du repo.

### Étape 3 — Vérifier le planning

Dans `daily-run.yml`, le planning est défini par cette ligne :

```yaml
- cron: '0 8 * * *'   # tous les jours à 08h00 UTC = 09h00 / 10h00 heure française
```

Format : `minute heure jour_du_mois mois jour_de_semaine`

Exemples utiles :
```yaml
'0 7 * * 1-5'    # du lundi au vendredi à 07h00 UTC
'0 6 * * 1'      # uniquement le lundi à 06h00 UTC
```

> GitHub UTC = heure française - 1h en hiver, - 2h en été.

### Étape 4 — Tester manuellement

Une fois le fichier dans `.github/workflows/`, aller sur :
**Actions** (onglet du repo) → **EPC AutoAppelOffre - Daily Run** → **Run workflow**

Les logs s'affichent en temps réel. Le fichier `app.log` est conservé 30 jours en tant qu'artifact téléchargeable.

---

## 💻 Lancer le script manuellement

### Prérequis

- Python 3.8 ou supérieur installé
- Git installé

### Installation

```bash
# 1. Cloner le repo
git clone https://github.com/LucDeldem/EPC-AutoAppelOffre.git
cd EPC-AutoAppelOffre

# 2. Créer un environnement virtuel (bonne pratique pour isoler les dépendances)
python -m venv venv

# Sur Windows :
venv\Scripts\activate
# Sur Mac/Linux :
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Créer le fichier .env (voir section Variables d'environnement)
cp .env.example .env
# Puis éditer .env avec vos credentials
```

### Commandes disponibles

```bash
# Test rapide : affiche les résultats dans la console, SANS envoyer d'email
python main.py --no-email --lookback 7

# Test sur 30 jours, sans email
python main.py --no-email --lookback 30

# Exécution complète avec envoi d'email (nécessite .env configuré)
python main.py --lookback 7

# Remonter plus loin (utile pour un premier test ou après une coupure)
python main.py --lookback 60
```

| Option | Description | Valeur par défaut |
|---|---|---|
| `--lookback JOURS` | Nombre de jours à remonter dans les annonces | 30 |
| `--no-email` | Ne pas envoyer d'email (mode test/debug) | — |

---

## 🐛 Dépannage

### "Credentials email manquantes" au lancement

→ Le fichier `.env` est absent ou mal rempli. Vérifier que `SENDER_EMAIL` et `SENDER_PASSWORD` sont bien définis.

### Erreur SMTP 535 (Authentication failed) — Gmail

→ Vous utilisez le mot de passe du compte Gmail et non un **mot de passe d'application**. Voir la section [Obtenir un mot de passe d'application Gmail](#obtenir-un-mot-de-passe-dapplication-gmail).

### Le workflow GitHub Actions ne se déclenche pas

→ Vérifier que le fichier `.yml` est bien dans `.github/workflows/` et non à la racine du repo.

→ Vérifier que la branche par défaut du repo est bien `main` (et non `master`).

### Aucune annonce trouvée

→ Essayer avec `--lookback 60` pour remonter plus loin.

→ Vérifier les codes CPV dans `config.py` (section `CPV_CODES`).

### Trop d'annonces peu pertinentes

→ Augmenter `SCORE_THRESHOLD_FOR_EMAIL` à 10 ou 12 dans `config.py`.

### Timeout sur l'API BOAMP

→ Augmenter `BOAMP_TIMEOUT` dans `config.py` (valeur par défaut : 20 secondes).

---

## 📁 Architecture du projet

```
EPC-AutoAppelOffre/
│
├── config.py           ← ✏️  À modifier pour adapter les mots-clés, seuils, destinataire
├── boamp_fetcher.py    ←     Interroge l'API BOAMP (Opendatasoft Explore v2.1)
├── filtering.py        ←     Scoring des annonces par mots-clés
├── email_sender.py     ←     Formate et envoie le rapport HTML
├── gpt_validator.py    ←     (optionnel) Validation supplémentaire via GPT
├── main.py             ←     Point d'entrée : orchestre tout le pipeline
│
├── daily-run.yml       ← ⚠️  À déplacer dans .github/workflows/ pour activer l'automatisation
├── requirements.txt    ←     Dépendances Python (ne pas modifier)
├── .env.example        ←     Modèle pour créer votre .env local
├── .gitignore          ←     Exclut .env et autres fichiers sensibles de Git
└── README.md
```

---

## 🔒 Sécurité

- Le fichier `.env` contenant les credentials est exclu de Git via `.gitignore` → il ne sera jamais publié sur GitHub.
- En GitHub Actions, les credentials sont stockés en tant que **Secrets chiffrés** et ne sont jamais visibles dans les logs.
- L'API BOAMP est interrogée uniquement en HTTPS.
- L'envoi email se fait en TLS (port 587).

---

## 👤 Auteur & Contact

**Luc Deldem** — Stagiaire DSI, EPC France  
[luc.deldem@epc-france.com](mailto:luc.deldem@epc-france.com)

---

*Propriété EPC France — Mise à jour : juin 2026*
