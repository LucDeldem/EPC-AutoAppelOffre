# 🏗️ EPC AutoAppelOffre

Système automatisé de détection et filtrage des appels d'offre publics français (BOAMP) pour EPC France.

## 📋 Pipeline

```
BOAMP API
   ↓ (récupération par CPV)
Filtrage CPV
   ↓
Filtrage par mots-clés
   ↓
Scoring métier
   ↓
Email formaté
```

## 🚀 Installation

### Prérequis
- Python 3.8+
- pip
- Un compte Gmail (ou autre SMTP)

### Setup local

1. **Clone le repo**
```bash
git clone https://github.com/LucDeldem/EPC-AutoAppelOffre.git
cd EPC-AutoAppelOffre
```

2. **Crée un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # sur Windows: venv\Scripts\activate
```

3. **Installe les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configure les variables d'environnement**
```bash
cp .env.example .env
# Édite .env avec tes credentials email
```

### Configuration Gmail

Pour utiliser Gmail :

1. Active la [vérification en 2 étapes](https://myaccount.google.com/security)
2. Génère un [mot de passe d'application](https://myaccount.google.com/apppasswords)
3. Copie ce mot de passe dans `.env` (variable `SENDER_PASSWORD`)

### Configuration personnalisée (optionnel)

Édite `config.py` pour :
- Ajouter/modifier les **codes CPV** ciblés
- Ajuster les **scores des mots-clés**
- Modifier les **seuils de filtrage**
- Changer le **destinataire email**

## 🎯 Utilisation

### Test local (sans email)
```bash
python main.py --no-email --lookback 7
```

### Avec envoi d'email
```bash
python main.py --lookback 30
```

### Options
- `--lookback DAYS` : Nombre de jours à remonter (défaut: 30)
- `--no-email` : Mode debug sans envoi d'email

## 📊 Résultats

Le script génère :
- **Logs console** : suivi en temps réel
- **app.log** : historique complet
- **Email HTML** : mise en forme professionnelle des annonces

### Format de l'email
Chaque annonce inclut :
- ✅ Titre et score
- 📋 Objet et descriptif
- 🏢 Acheteur et région
- 💰 Budget estimé
- 📅 Date limite
- 🔗 Lien BOAMP direct

## 🔄 CI/CD (GitHub Actions)

Configure une action automatisée (à venir) :
- ⏰ Exécution quotidienne/hebdomadaire
- 🔐 Secrets chiffrés pour credentials
- 📧 Email automatique
- 📊 Logs et rapports

## 📁 Architecture

```
EPC-AutoAppelOffre/
├── config.py              # Configuration centralisée
├── boamp_fetcher.py       # Récupération API BOAMP
├── filtering.py           # Filtrage et scoring
├── email_sender.py        # Envoi emails HTML
├── main.py                # Orchestration du pipeline
├── requirements.txt       # Dépendances
├── .env.example          # Template variables d'env
├── .gitignore            # Exclusions Git
└── README.md             # Cette doc
```

## 🎯 Logique de filtrage

### 1. Codes CPV (Common Procurement Vocabulary)
Filtrage initial par codes métier :
- `45232200` : Travaux de fondation
- `45233000` : Travaux de forage
- `45234100` : Travaux géotechniques
- `45235000` : Travaux de soutènement
- etc.

### 2. Mots-clés avec scoring
Chaque mot-clé a un poids (1-10 pts) :
- **10 pts** : micropieux, soutènement, paroi berlinoise
- **9 pts** : confortement, tirant d'ancrage
- **8 pts** : travaux acrobatiques, béton projeté
- **5 pts** : forage, talus, stabilisation
- **2-3 pts** : terrassement, excavation

Score minimum pour passer au filtrage final : **5 pts**

### 3. Seuil final
Seules les annonces avec un score **≥ 6** sont incluses dans l'email.

## ⚙️ Configuration recommandée

**Codes CPV à ajouter** (si besoin d'élargir) :
```python
"45232100",  # Travaux de pilotage
"45234200",  # Travaux de décontamination des sols
"45239100",  # Autres travaux géotechniques
```

**Mots-clés** (testés et validés pour EPC) :
```python
"micropieux": 10,
"soutènement": 10,
"paroi berlinoise": 10,
"tirant d'ancrage": 9,
"stabilisation de talus": 9,
# ... voir config.py pour la liste complète
```

## 🐛 Dépannage

### Erreur : "Credentials email manquantes"
→ Crée un fichier `.env` avec `SENDER_EMAIL` et `SENDER_PASSWORD`

### Erreur SMTP 535 (Gmail)
→ Utilise un mot de passe d'application, pas ton mot de passe de compte

### API BOAMP timeout
→ Augmente `BOAMP_TIMEOUT` dans `config.py` (par défaut: 10s)

### Pas d'annonces trouvées
→ Vérifie les codes CPV dans `config.py`
→ Augmente `--lookback` pour remonter plus loin dans le temps

## 📈 Métriques & Monitoring

Fichier `app.log` :
- ✅ Nombre d'annonces trouvées par étape
- 📊 Scores par annonce
- ⏱️ Durée du pipeline
- ❌ Erreurs et warnings

## 🔒 Sécurité

- ✅ **Pas de secrets en Git** : utilise `.env` (exclu via `.gitignore`)
- ✅ **Variables chiffrées** en GitHub Actions
- ✅ **HTTPS** sur l'API BOAMP
- ✅ **TLS** sur SMTP

## 📝 Licence

Propriété EPC France

## 👤 Auteur

Luc Deldem - luc.deldem@epc-france.com

## 🚀 Prochaines étapes

- [ ] GitHub Actions (CI/CD)
- [ ] Stockage des résultats (CSV/DB)
- [ ] Dashboard web
- [ ] Notification Slack/Teams
- [ ] Historique et tendances

---

**Mis à jour** : 23/06/2026
