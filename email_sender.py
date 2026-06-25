import os
import logging
import html
from datetime import datetime, date
from typing import Any, Dict, List, Optional

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


# ====================================================================== #
# Helpers de présentation
# ====================================================================== #
def _esc(value: Any) -> str:
    """Échappe une valeur pour l'insérer dans du HTML."""
    return html.escape(str(value if value is not None else ""))


def _parse_date(value: Any) -> Optional[date]:
    """Parse une date ODS (ISO 8601 ou JJ/MM/AAAA) en `date`, sinon None."""
    if not value or str(value).strip() in ("", "N/A"):
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _deadline_label(deadline: Optional[date]) -> str:
    """Texte lisible « date limite + jours restants » avec code couleur."""
    if deadline is None:
        return '<span style="color:#6b7280;">Date limite : non précisée</span>'
    remaining = (deadline - datetime.now().date()).days
    fr = deadline.strftime("%d/%m/%Y")
    if remaining < 0:
        color, urgence = "#9ca3af", "expirée"
    elif remaining <= 3:
        color, urgence = "#dc2626", f"J-{remaining} ⚠️"
    elif remaining <= 7:
        color, urgence = "#ea580c", f"J-{remaining}"
    else:
        color, urgence = "#16a34a", f"J-{remaining}"
    return (
        f'<span style="color:{color};font-weight:600;">'
        f'⏱ Date limite : {fr} ({urgence})</span>'
    )


def _score_badge(score: int) -> str:
    """Pastille colorée selon le score."""
    if score >= 25:
        bg = "#16a34a"
    elif score >= 12:
        bg = "#2563eb"
    else:
        bg = "#6b7280"
    return (
        f'<span style="display:inline-block;background:{bg};color:#fff;'
        f'border-radius:9999px;padding:2px 10px;font-size:13px;'
        f'font-weight:700;">{score} pts</span>'
    )


def _keywords_chips(keywords: List[str]) -> str:
    """Affiche les mots-clés détectés (positifs uniquement) sous forme de puces."""
    pos = [k for k in (keywords or []) if not k.lower().startswith(
        ("maîtrise", "maitrise", "moe", "amo", "mission d", "assistance"))]
    if not pos:
        return ""
    chips = "".join(
        f'<span style="display:inline-block;background:#eef2ff;color:#3730a3;'
        f'border-radius:6px;padding:2px 8px;margin:2px 4px 2px 0;'
        f'font-size:12px;">{_esc(k)}</span>'
        for k in pos[:8]
    )
    return f'<div style="margin-top:8px;">{chips}</div>'


def _tender_card(index: int, t: Dict[str, Any]) -> str:
    """Construit une carte HTML pour une annonce."""
    score = t.get("score_initial", 0)
    deadline = _parse_date(t.get("datedeadline"))
    descriptif = t.get("descriptif") or ""
    if len(descriptif) > 320:
        descriptif = descriptif[:320].rstrip() + "…"

    return f"""
    <tr>
      <td style="padding:0 0 16px 0;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;
                      border-collapse:separate;overflow:hidden;">
          <tr>
            <td style="padding:18px 20px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:13px;color:#6b7280;">#{index}</td>
                  <td align="right">{_score_badge(score)}</td>
                </tr>
              </table>
              <h2 style="margin:8px 0 6px 0;font-size:17px;line-height:1.35;
                         color:#111827;">{_esc(t.get('titre','N/A'))}</h2>
              <p style="margin:0 0 10px 0;font-size:14px;color:#374151;
                        line-height:1.5;">{_esc(descriptif)}</p>
              <table role="presentation" cellpadding="0" cellspacing="0"
                     style="font-size:13px;color:#4b5563;">
                <tr><td style="padding:2px 0;">🏛 <b>Acheteur :</b> {_esc(t.get('acheteur','N/A'))}</td></tr>
                <tr><td style="padding:2px 0;">📍 <b>Région :</b> {_esc(t.get('region','N/A'))}</td></tr>
                <tr><td style="padding:2px 0;">{_deadline_label(deadline)}</td></tr>
              </table>
              {_keywords_chips(t.get('matched_keywords'))}
              <div style="margin-top:14px;">
                <a href="{_esc(t.get('url','#'))}"
                   style="display:inline-block;background:#2563eb;color:#ffffff;
                          text-decoration:none;padding:9px 18px;border-radius:8px;
                          font-size:14px;font-weight:600;">Voir l'annonce →</a>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    """


def build_html_report(tenders: List[Dict[str, Any]],
                      lookback_days: Optional[int] = None) -> str:
    """Construit le rapport HTML complet (email responsive)."""
    today = datetime.now().strftime("%d/%m/%Y")
    sub = f"sur les {lookback_days} derniers jours" if lookback_days else ""
    cards = "".join(_tender_card(i, t) for i, t in enumerate(tenders, 1))

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:#f3f4f6;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0"
             style="max-width:640px;width:100%;">
        <!-- En-tête -->
        <tr><td style="padding:0 16px 20px 16px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:linear-gradient(135deg,#1e3a8a,#2563eb);
                        border-radius:12px;">
            <tr><td style="padding:24px 24px;">
              <div style="font-size:13px;color:#bfdbfe;letter-spacing:1px;
                          text-transform:uppercase;">EPC · Veille appels d'offre</div>
              <div style="font-size:24px;font-weight:700;color:#ffffff;margin-top:4px;">
                📢 {len(tenders)} opportunité{'s' if len(tenders) > 1 else ''} détectée{'s' if len(tenders) > 1 else ''}
              </div>
              <div style="font-size:13px;color:#dbeafe;margin-top:6px;">
                {today} {sub} · soutènement, confortement, micropieux…
              </div>
            </td></tr>
          </table>
        </td></tr>
        <!-- Cartes -->
        <tr><td style="padding:0 16px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            {cards}
          </table>
        </td></tr>
        <!-- Pied -->
        <tr><td style="padding:8px 16px 24px 16px;">
          <p style="font-size:12px;color:#9ca3af;text-align:center;line-height:1.6;">
            Annonces issues du BOAMP, filtrées par mots-clés métier et zone géographique (Sud).<br>
            Seules les offres encore ouvertes (date limite non dépassée) sont incluses.<br>
            EPC-AutoAppelOffre · rapport automatique
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def save_html_report(tenders: List[Dict[str, Any]],
                     path: str = "rapport_boamp.html",
                     lookback_days: Optional[int] = None) -> str:
    """Écrit le rapport HTML sur disque et renvoie le chemin."""
    content = build_html_report(tenders, lookback_days=lookback_days)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.abspath(path)


def send_email(subject: str, html_content: str):
    """Envoie un email HTML via l'API Resend."""
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
