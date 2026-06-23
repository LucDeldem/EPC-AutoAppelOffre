import os
import logging
import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Variables environnement
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_TO = os.getenv("EMAIL_TO")

# Vérifications
if not RESEND_API_KEY:
    raise ValueError("❌ RESEND_API_KEY manquant (check .env ou GitHub Secrets)")

if not EMAIL_TO:
    raise ValueError("❌ EMAIL_TO manquant (check .env ou GitHub Secrets)")

# Init API
resend.api_key = RESEND_API_KEY


def send_email(subject: str, html_content: str):
    """
    Envoie un email HTML (sans modifier ton rapport BOAMP).
    """

    try:
        response = resend.Emails.send({
            "from": "EPC BOAMP <onboarding@resend.dev>",
            "to": [EMAIL_TO],
            "subject": subject,
            "html": html_content
        })

        logger.info(f"✅ Email envoyé: {response}")
        return response

    except Exception as e:
        logger.error(f"❌ Erreur envoi email: {e}")
        raise