"""
Configuration centralisée pour le système de filtrage des appels d'offre BOAMP
"""

# ==================== CODES CPV ====================
CPV_CODES = [
    "45232200",  # Travaux de fondation
    "45233000",  # Travaux de forage
    "45234100",  # Travaux géotechniques
    "45234110",  # Travaux de stabilisation de sols
    "45235000",  # Travaux d'étançonnement et de soutènement
    "45235100",  # Travaux de paroi et rideau de palplanches
    "45239000",  # Autres travaux spécialisés de génie civil
]

# ==================== MOTS-CLÉS ET SCORING ====================
KEYWORDS_SCORING = {
    # Très pertinent (10 points)
    "micropieux": 10,
    "soutènement": 10,
    "paroi berlinoise": 10,
    "micro-berlinoise": 10,
    
    # Pertinent (9 points)
    "confortement": 9,
    "tirant d'ancrage": 9,
    "stabilisation de talus": 9,
    "tirant": 9,
    "ancrage": 8,  # Réduit à 8 car ambiguïté possible
    
    # Modérément pertinent (8 points)
    "travaux acrobatiques": 8,
    "travaux sur cordes": 8,
    "béton projeté": 8,
    
    # Pertinent mais besoin de contexte (5-6 points)
    "clouage": 6,
    "géotechnique": 6,
    "forage": 5,
    "talus": 5,
    "falaise": 5,
    "stabilisation": 5,
    "paroi": 5,
    "fondation": 4,
    
    # Bruit potentiel (1-3 points)
    "terrassement": 2,
    "excavation": 2,
    "renforcement": 1,  # Trop ambiguë
}

# ==================== SEUILS ====================
SCORE_THRESHOLD_FOR_GPT = 5  # Minimum score pour passer la validation GPT
SCORE_THRESHOLD_FOR_EMAIL = 6  # Minimum score pour être inclus dans l'email

# ==================== DATES ====================
# Nombre de jours à remonter par défaut (30 jours = 1 mois)
DEFAULT_LOOKBACK_DAYS = 30

# ==================== EMAIL ====================
EMAIL_RECIPIENT = "luc.deldem@epc-france.com"
EMAIL_SENDER = "epc-auto-appel@github.actions"

# ==================== API BOAMP (Nouvelle API ODS) ====================
# Nouvelle API BOAMP avec endpoint ODS Explore v2
BOAMP_API_BASE_URL = "https://www.boamp.fr/api/opendata"
BOAMP_API_ENDPOINT = "/annonces"
BOAMP_TIMEOUT = 10  # secondes

# ==================== GPT SETTINGS ====================
GPT_MODEL = "gpt-4o-mini"  # ou "gpt-3.5-turbo" pour moins cher
GPT_TEMPERATURE = 0.3  # Réponses plus déterministes

# Prompt système pour l'IA
GPT_SYSTEM_PROMPT = """Tu es expert en travaux spéciaux, géotechnique, soutènement, 
confortement de falaises, stabilisation de versants et travaux acrobatiques.

Évalue si cette consultation/marché public est pertinente pour EPC France, 
une entreprise spécialisée dans ces domaines.

Réponds TOUJOURS en JSON avec la structure suivante:
{
  "pertinent": true/false,
  "score": (0-10),
  "raison": "explication courte"
}

Sois strict : accepte les faux positifs (mieux avoir trop d'annonces) 
mais évite les faux négatifs (ne pas rater une bonne affaire)."""
