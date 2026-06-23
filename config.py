"""
Configuration centralisée pour le système de filtrage des appels d'offre BOAMP.
"""

# ==================== CODES CPV (référence métier) ====================
CPV_CODES = [
    "45232200", "45233000", "45234100", "45234110",
    "45235000", "45235100", "45239000",
]

# ==================== MOTS-CLÉS ET SCORING ====================
# Détection insensible : casse, accents, pluriel (-s/-x), espaces, traits
# d'union et apostrophes (voir filtering.py). Couvre les besoins métier :
# paroi (micro-)berlinoise, confortement, soutènement, renforcement, pieux,
# tirant, ancrage, talus, protection de talus, travaux acrobatiques, etc.
KEYWORDS_SCORING = {
    # Cœur de métier (10)
    "micropieux": 10,
    "soutènement": 10,
    "paroi berlinoise": 10,
    "paroi micro-berlinoise": 10,
    "micro-berlinoise": 10,
    "paroi clouée": 10,

    # Très pertinent (8-9)
    "confortement": 9,
    "tirant d'ancrage": 9,
    "protection de talus": 9,
    "stabilisation de talus": 9,
    "stabilisation de versant": 9,
    "berlinoise": 8,
    "pieux": 8,
    "ancrage": 8,
    "clouage": 8,
    "béton projeté": 8,
    "gunite": 8,
    "travaux acrobatiques": 8,
    "travaux sur cordes": 8,

    # Pertinent mais contextuel (5-6)
    "tirant": 6,
    "géotechnique": 6,
    "paroi rocheuse": 6,
    "éboulement": 6,
    "renforcement": 5,
    "talus": 5,
    "falaise": 5,
    "forage": 5,

    # Faible / ambigu (1-4)
    "stabilisation": 4,
    "paroi": 3,
    "fondation": 3,
    "terrassement": 2,
    "excavation": 2,
}

# Termes envoyés à l'API en recherche plein-texte (pré-filtrage côté serveur).
# On ne met QUE des termes discriminants : les mots ambigus seuls (talus,
# ancrage, tirant, renforcement) feraient exploser le volume. Ils restent
# évalués côté client une fois l'annonce remontée par un terme discriminant.
SEARCH_TERMS = [
    "micropieux", "pieux",
    "paroi berlinoise", "micro-berlinoise", "paroi clouée",
    "soutènement", "confortement",
    "tirant d'ancrage",
    "protection de talus", "stabilisation de talus", "stabilisation de versant",
    "clouage", "géotechnique", "béton projeté", "gunite",
    "travaux acrobatiques", "travaux sur cordes",
    "falaise", "éboulement",
]

# ==================== SEUILS ====================
# Relevé : on écarte les annonces à score faible (peu d'intérêt). Avec ce seuil,
# il faut au moins un terme fort (soutènement, confortement, pieux, clouage…)
# ou une combinaison significative ; un mot ambigu seul (renforcement, talus,
# tirant) ne suffit pas. Monter à 10 si encore trop de bruit.
SCORE_THRESHOLD_KEEP = 6       # 1er tri (conservation + log)
SCORE_THRESHOLD_FOR_EMAIL = 8  # Inclusion dans l'e-mail

# ==================== FILTRE GÉOGRAPHIQUE ====================
GEO_FILTER_ENABLED = True
# Annonce sans département exploitable : la garder (True, ne rate pas les
# marchés nationaux/multi-départements) ou la rejeter (False).
GEO_KEEP_UNKNOWN = True

# Périmètre : PACA + Occitanie + Nouvelle-Aquitaine.
SOUTH_DEPARTMENTS = {
    # PACA
    "04", "05", "06", "13", "83", "84",
    # Occitanie
    "09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82",
    # Nouvelle-Aquitaine
    "16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87",
}

# ==================== DATES ====================
DEFAULT_LOOKBACK_DAYS = 30

# ==================== EMAIL ====================
EMAIL_RECIPIENT = "luc.deldem@epc-france.com"
EMAIL_SENDER = "epc-auto-appel@github.actions"

# ==================== API BOAMP (Opendatasoft Explore v2.1) ====================
BOAMP_RECORDS_URL = (
    "https://boamp-datadila.opendatasoft.com"
    "/api/explore/v2.1/catalog/datasets/boamp/records"
)
BOAMP_PAGE_SIZE = 100
BOAMP_MAX_PAGES = 50
BOAMP_TIMEOUT = 20
BOAMP_AVIS_URL_TPL = 'https://www.boamp.fr/pages/avis/?q=idweb:"{idweb}"'