"""
Envoi d'un e-mail récapitulatif propre (texte + HTML) avec les annonces filtrées.
"""

import logging
import os
import smtplib
import socket
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from html import escape
from typing import Any, Dict, List, Optional

from config import EMAIL_RECIPIENT

logger = logging.getLogger(__name__)

BRAND = "#1a5490"
ACCENT = "#2e7d32"


def _fmt_date(value: str) -> str:
    """Affiche une date ISO (avec ou sans heure) au format JJ/MM/AAAA."""
    if not value or value == "N/A":
        return "—"
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value[:len(fmt) + 5], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return str(value)[:10]


class EmailSender:
    """Compose et envoie l'e-mail récapitulatif."""

    def __init__(self, smtp_host: str, smtp_port: int, sender_email: str,
                 sender_password: str = "", timeout: int = 30,
                 use_ssl: Optional[bool] = None):
        """
        use_ssl : True = SMTP_SSL (port 465), False = STARTTLS (587),
                  None = auto (SSL si port 465, sinon STARTTLS).
        sender_password vide => pas d'authentification (relais SMTP interne).
        """
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.sender_email = sender_email
        self.sender_password = sender_password or ""
        self.timeout = timeout
        self.use_ssl = use_ssl if use_ssl is not None else (self.smtp_port == 465)

    def _open(self):
        """Ouvre une connexion SMTP adaptée (SSL / STARTTLS) avec timeout."""
        ctx = ssl.create_default_context()
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port,
                                      timeout=self.timeout, context=ctx)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout)
            server.ehlo()
            if server.has_extn("starttls"):
                server.starttls(context=ctx)
                server.ehlo()
        if self.sender_password:  # relais interne : souvent sans login
            server.login(self.sender_email, self.sender_password)
        return server

    # ------------------------------------------------------------------ #
    def send_tenders_email(self, tenders: List[Dict[str, Any]], subject_suffix: str = "") -> bool:
        if not tenders:
            logger.info("Pas d'annonces à envoyer")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = f"Appels d'offre EPC — {subject_suffix or 'Résultats'}"
        message["From"] = formataddr(("EPC AutoAppelOffre", self.sender_email))
        message["To"] = EMAIL_RECIPIENT
        message["Date"] = formatdate(localtime=True)

        # On attache texte PUIS html : le client affiche la dernière partie
        # qu'il sait lire (HTML si possible, texte sinon).
        message.attach(MIMEText(self._render_text(tenders), "plain", "utf-8"))
        message.attach(MIMEText(self._render_html(tenders), "html", "utf-8"))

        try:
            logger.info("Envoi de l'e-mail à %s via %s:%d (%d annonces)...",
                        EMAIL_RECIPIENT, self.smtp_host, self.smtp_port, len(tenders))
            with self._open() as server:
                server.send_message(message)
            logger.info("E-mail envoyé avec succès")
            return True
        except (socket.timeout, TimeoutError, ConnectionError, OSError) as e:
            logger.error("Connexion SMTP impossible (%s:%d) : %s", self.smtp_host, self.smtp_port, e)
            logger.error("→ Port probablement bloqué par le pare-feu. Testez : "
                         "Test-NetConnection %s -Port %d. Sinon utilisez le relais "
                         "SMTP interne d'EPC (DSI).", self.smtp_host, self.smtp_port)
            return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error("Authentification SMTP refusée : %s", e)
            logger.error("→ Gmail exige un « mot de passe d'application » (pas le mot "
                         "de passe du compte) avec la validation en 2 étapes activée.")
            return False
        except Exception as e:
            logger.error("Erreur envoi e-mail : %s", e)
            return False

    # ------------------------------------------------------------------ #
    # Version texte (fallback + anti-spam)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _render_text(tenders: List[Dict[str, Any]]) -> str:
        lines = [
            "APPELS D'OFFRE EPC — Travaux spéciaux / Géotechnique",
            f"{len(tenders)} annonce(s) — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "=" * 60,
        ]
        for i, t in enumerate(tenders, 1):
            kws = ", ".join(t.get("matched_keywords", [])) or "—"
            lines += [
                "",
                f"{i}. [{t.get('score_initial', 0)} pts] {t.get('objet', 'N/A')}",
                f"   Acheteur     : {t.get('acheteur', 'N/A')}",
                f"   Localisation : {t.get('region', 'N/A')}",
                f"   Parution     : {_fmt_date(t.get('dateparution', ''))}",
                f"   Date limite  : {_fmt_date(t.get('datedeadline', ''))}",
                f"   Mots-clés    : {kws}",
                f"   Lien         : {t.get('url', 'N/A')}",
            ]
        lines += ["", "-" * 60, "E-mail automatisé — EPC AutoAppelOffre (ne pas répondre)"]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Version HTML (mise en page propre, compatible clients mail)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _render_html(tenders: List[Dict[str, Any]]) -> str:
        now = datetime.now().strftime("%d/%m/%Y à %H:%M")
        cards = "\n".join(EmailSender._render_card(i, t) for i, t in enumerate(tenders, 1))
        return f"""\
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#2b2b2b;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">
        <tr><td style="background:{BRAND};border-radius:10px 10px 0 0;padding:24px 28px;color:#fff;">
          <div style="font-size:20px;font-weight:bold;">Appels d'offre — Travaux spéciaux & Géotechnique</div>
          <div style="font-size:13px;opacity:.85;margin-top:6px;">Sélection automatique BOAMP · {now}</div>
        </td></tr>
        <tr><td style="background:#eaf1f8;padding:14px 28px;color:{BRAND};font-size:14px;font-weight:bold;border-bottom:1px solid #dce4ec;">
          {len(tenders)} annonce(s) correspondant à vos critères
        </td></tr>
        <tr><td style="background:#ffffff;padding:8px 18px 18px;">{cards}</td></tr>
        <tr><td style="background:#ffffff;border-radius:0 0 10px 10px;padding:18px 28px;border-top:1px solid #eee;color:#9aa0a6;font-size:12px;">
          E-mail automatisé — EPC AutoAppelOffre · merci de ne pas répondre.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

    @staticmethod
    def _render_card(index: int, t: Dict[str, Any]) -> str:
        title = escape(t.get("objet", "N/A"))
        score = t.get("score_initial", 0)
        url = escape(t.get("url", "#"))
        acheteur = escape(t.get("acheteur", "N/A"))
        region = escape(str(t.get("region", "N/A")))
        type_marche = escape(t.get("type_marche", "") or "")
        parution = _fmt_date(t.get("dateparution", ""))
        deadline = _fmt_date(t.get("datedeadline", ""))

        chips = "".join(
            f'<span style="display:inline-block;background:#eef6ee;color:{ACCENT};'
            'border:1px solid #cfe6cf;border-radius:12px;padding:2px 9px;'
            f'font-size:11px;margin:2px 4px 2px 0;">{escape(k)}</span>'
            for k in t.get("matched_keywords", [])
        ) or '<span style="color:#9aa0a6;font-size:12px;">—</span>'

        type_badge = (
            f'<span style="background:#eef2f7;color:{BRAND};border-radius:4px;'
            f'padding:2px 8px;font-size:11px;margin-left:8px;">{type_marche}</span>'
            if type_marche else ""
        )

        def row(label: str, value: str) -> str:
            return (
                f'<tr><td style="padding:3px 0;color:#6b7280;font-size:13px;width:120px;'
                f'vertical-align:top;">{label}</td>'
                f'<td style="padding:3px 0;color:#2b2b2b;font-size:13px;">{value}</td></tr>'
            )

        return f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="border:1px solid #e3e8ee;border-radius:8px;margin:12px 0;background:#fbfcfd;">
          <tr><td style="padding:16px 18px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
              <div style="font-size:15px;font-weight:bold;color:{BRAND};line-height:1.35;">
                {index}. {title}{type_badge}
              </div>
            </div>
            <div style="margin:8px 0 4px;">
              <span style="background:{ACCENT};color:#fff;border-radius:4px;padding:2px 9px;font-size:12px;">
                Score {score}
              </span>
            </div>
            <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:8px;">
              {row("Acheteur", acheteur)}
              {row("Localisation", region)}
              {row("Parution", parution)}
              {row("Date limite", f'<strong>{deadline}</strong>')}
              {row("Mots-clés", chips)}
            </table>
            <a href="{url}" style="display:inline-block;margin-top:12px;background:{BRAND};
               color:#fff;text-decoration:none;padding:9px 16px;border-radius:5px;font-size:13px;">
              Voir l'annonce sur BOAMP →
            </a>
          </td></tr>
        </table>"""


def save_html_report(tenders: List[Dict[str, Any]], out_dir: str = "reports") -> str:
    """Enregistre le rapport HTML sur disque et renvoie le chemin du fichier."""
    os.makedirs(out_dir, exist_ok=True)
    fname = f"appels_offre_{datetime.now():%Y-%m-%d_%H%M}.html"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(EmailSender._render_html(tenders))
    return os.path.abspath(path)