"""
Module d'envoi d'emails avec les annonces filtrées
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any
from config import EMAIL_RECIPIENT, EMAIL_SENDER

logger = logging.getLogger(__name__)


class EmailSender:
    """Envoie les annonces filtrées par email"""
    
    def __init__(self, smtp_host: str, smtp_port: int, sender_email: str, sender_password: str):
        """
        Initialise l'expéditeur d'emails
        
        Args:
            smtp_host: Serveur SMTP (ex: smtp.gmail.com)
            smtp_port: Port SMTP (ex: 587)
            sender_email: Adresse email d'envoi
            sender_password: Mot de passe ou app password
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
    
    def send_tenders_email(self, tenders: List[Dict[str, Any]], subject_suffix: str = "") -> bool:
        """
        Envoie les annonces par email
        
        Args:
            tenders: Liste des annonces à envoyer
            subject_suffix: Suffixe pour le sujet (ex: "Dernier mois" ou "Nouvelles offres")
        
        Returns:
            True si succès, False sinon
        """
        if not tenders:
            logger.info("❌ Pas d'annonces à envoyer")
            return False
        
        try:
            # Crée le contenu HTML
            html_content = self._generate_html(tenders)
            
            # Crée le message
            message = MIMEMultipart("alternative")
            message["Subject"] = f"🏗️ Appels d'offre EPC - {subject_suffix or 'Résultats'}"
            message["From"] = self.sender_email
            message["To"] = EMAIL_RECIPIENT
            
            # Attache le contenu HTML
            part_html = MIMEText(html_content, "html", "utf-8")
            message.attach(part_html)
            
            # Envoie l'email
            logger.info(f"📧 Envoi de l'email à {EMAIL_RECIPIENT}...")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            logger.info(f"✅ Email envoyé avec succès ({len(tenders)} annonces)")
            return True
        
        except Exception as e:
            logger.error(f"❌ Erreur envoi email: {e}")
            return False
    
    def _generate_html(self, tenders: List[Dict[str, Any]]) -> str:
        """
        Génère le contenu HTML de l'email
        
        Args:
            tenders: Liste des annonces
        
        Returns:
            Contenu HTML
        """
        date_now = datetime.now().strftime("%d/%m/%Y à %H:%M")
        
        # Début du HTML
        html = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .header {{ background-color: #1a5490; color: white; padding: 20px; border-radius: 5px; }}
                    .tender {{ 
                        border: 1px solid #ddd; 
                        margin: 15px 0; 
                        padding: 15px; 
                        border-radius: 5px;
                        background-color: #f9f9f9;
                    }}
                    .tender-title {{ 
                        font-size: 16px; 
                        font-weight: bold; 
                        color: #1a5490;
                        margin-bottom: 8px;
                    }}
                    .tender-score {{
                        display: inline-block;
                        background-color: #4CAF50;
                        color: white;
                        padding: 3px 8px;
                        border-radius: 3px;
                        font-size: 12px;
                        margin-left: 10px;
                    }}
                    .tender-field {{ margin: 8px 0; }}
                    .tender-label {{ font-weight: bold; color: #555; }}
                    .tender-value {{ color: #333; }}
                    .url-button {{
                        display: inline-block;
                        background-color: #1a5490;
                        color: white;
                        padding: 8px 15px;
                        text-decoration: none;
                        border-radius: 3px;
                        margin-top: 10px;
                    }}
                    .footer {{ 
                        margin-top: 30px; 
                        padding-top: 20px; 
                        border-top: 1px solid #ddd; 
                        font-size: 12px; 
                        color: #999;
                    }}
                    .stats {{ 
                        background-color: #e3f2fd; 
                        padding: 15px; 
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏗️ Appels d'offre EPC - France</h1>
                    <p>Résultats du {date_now}</p>
                </div>
                
                <div class="stats">
                    <p><strong>{len(tenders)} annonce(s) trouvée(s)</strong> correspondant à vos critères</p>
                </div>
        """
        
        # Ajoute les annonces
        for i, tender in enumerate(tenders, 1):
            score = tender.get("score_initial", 0)
            
            html += f"""
                <div class="tender">
                    <div class="tender-title">
                        {i}. {tender.get('titre', 'N/A')}
                        <span class="tender-score">Score: {score}</span>
                    </div>
                    
                    <div class="tender-field">
                        <span class="tender-label">📋 Objet :</span>
                        <span class="tender-value">{tender.get('objet', 'N/A')}</span>
                    </div>
                    
                    <div class="tender-field">
                        <span class="tender-label">📝 Descriptif :</span>
                        <span class="tender-value">{tender.get('descriptif', 'N/A')}</span>
                    </div>
                    
                    <div class="tender-field">
                        <span class="tender-label">🏢 Acheteur :</span>
                        <span class="tender-value">{tender.get('acheteur', 'N/A')}</span>
                    </div>
                    
                    <div class="tender-field">
                        <span class="tender-label">📍 Région :</span>
                        <span class="tender-value">{tender.get('region', 'N/A')}</span>
                    </div>
                    
                    <div class="tender-field">
                        <span class="tender-label">💰 Budget :</span>
                        <span class="tender-value">{tender.get('budget', 'N/A')}</span>
                    </div>
                    
                    <div class="tender-field">
                        <span class="tender-label">📅 Date limite :</span>
                        <span class="tender-value">{tender.get('datedeadline', 'N/A')}</span>
                    </div>
                    
                    <a href="{tender.get('url', '#')}" class="url-button">Voir sur BOAMP →</a>
                </div>
            """
        
        # Fin du HTML
        html += """
                <div class="footer">
                    <p>Email automatisé - EPC AutoAppelOffre</p>
                    <p>Ne pas répondre à cet email</p>
                </div>
            </body>
        </html>
        """
        
        return html
