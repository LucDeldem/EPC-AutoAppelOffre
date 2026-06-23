"""
Script principal - Orchestration du pipeline de filtrage d'appels d'offre
"""

import logging
import os
import sys
from dotenv import load_dotenv
from boamp_fetcher import BOAMPFetcher
from filtering import TenderFilter
from email_sender import EmailSender, save_html_report
from config import DEFAULT_LOOKBACK_DAYS, SCORE_THRESHOLD_FOR_EMAIL


def setup_logging(level: int = logging.INFO) -> None:
    """Configure le logging en UTF-8 (évite les UnicodeEncodeError sous Windows cp1252)."""
    # Force la console Python en UTF-8 quand c'est possible (Py >= 3.7).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # flux non reconfigurable (ex: redirection particulière)

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    stream_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler("app.log", encoding="utf-8")

    logging.basicConfig(level=level, format=fmt,
                        handlers=[stream_handler, file_handler])


setup_logging()
logger = logging.getLogger(__name__)

# Charge les variables d'environnement
load_dotenv()


def main(lookback_days: int = DEFAULT_LOOKBACK_DAYS, send_email: bool = True):
    """
    Pipeline principal
    
    Args:
        lookback_days: Nombre de jours à remonter
        send_email: Si True, envoie un email avec les résultats
    """
    logger.info("=" * 80)
    logger.info("🚀 Démarrage du pipeline EPC AutoAppelOffre")
    logger.info("=" * 80)
    
    try:
        # ============ ÉTAPE 1 : Récupération BOAMP ============
        logger.info("\n📡 ÉTAPE 1 : Récupération des annonces BOAMP...")
        fetcher = BOAMPFetcher()
        raw_tenders = fetcher.fetch_tenders(lookback_days=lookback_days)
        logger.info(f"✅ {len(raw_tenders)} annonces brutes récupérées")
        
        if not raw_tenders:
            logger.warning("⚠️  Aucune annonce trouvée")
            return
        
        # ============ ÉTAPE 2 : Filtrage et Scoring ============
        logger.info("\n🎯 ÉTAPE 2 : Filtrage et scoring par mots-clés...")
        filter_engine = TenderFilter()
        scored_tenders = filter_engine.filter_and_score(raw_tenders)
        logger.info(f"✅ {len(scored_tenders)} annonces conservées après filtrage")
        
        if not scored_tenders:
            logger.warning("⚠️  Aucune annonce après filtrage")
            return
        
        # ============ ÉTAPE 3 : Création des résumés ============
        logger.info("\n📋 ÉTAPE 3 : Création des résumés...")
        summaries = filter_engine.batch_summarize(scored_tenders)
        
        # Filtre avec le seuil final
        final_tenders = [
            t for t in summaries 
            if t.get("score_initial", 0) >= SCORE_THRESHOLD_FOR_EMAIL
        ]
        logger.info(f"✅ {len(final_tenders)} annonces avec score >= {SCORE_THRESHOLD_FOR_EMAIL}")
        
        if not final_tenders:
            logger.warning("⚠️  Aucune annonce ne dépasse le seuil final")
            return
        
        # ============ ÉTAPE 4 : Affichage des résultats ============
        logger.info("\n📊 RÉSULTATS :")
        logger.info("-" * 80)
        for i, tender in enumerate(final_tenders, 1):
            logger.info(f"\n{i}. [{tender['score_initial']}pts] {tender['titre'][:70]}")
            logger.info(f"   Acheteur: {tender['acheteur']}")
            logger.info(f"   Région: {tender['region']}")
            logger.info(f"   URL: {tender['url']}")

        # ============ ÉTAPE 4bis : Rapport HTML sur disque ============
        # Toujours généré : utile même si l'envoi d'e-mail est bloqué (pare-feu).
        try:
            report_path = save_html_report(final_tenders)
            logger.info("\n💾 Rapport HTML enregistré : %s", report_path)
        except Exception as e:
            logger.warning("Impossible d'écrire le rapport HTML : %s", e)

        # ============ ÉTAPE 5 : Envoi d'email ============
        if send_email:
            logger.info("\n📧 ÉTAPE 5 : Envoi de l'email...")
            
            # Récupère la configuration SMTP depuis l'env
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            sender_email = os.getenv("SENDER_EMAIL")
            sender_password = os.getenv("SENDER_PASSWORD", "")
            smtp_timeout = int(os.getenv("SMTP_TIMEOUT", "30"))
            # SMTP_SSL=1/0 pour forcer ; sinon auto (SSL si port 465)
            use_ssl_env = os.getenv("SMTP_SSL")
            use_ssl = None if use_ssl_env is None else use_ssl_env in ("1", "true", "True")
            # Relais interne (port 25) : authentification souvent inutile
            requires_auth = smtp_port != 25

            if not sender_email or (requires_auth and not sender_password):
                logger.error("❌ Configuration SMTP incomplète (SENDER_EMAIL"
                             "%s manquant)", " / SENDER_PASSWORD" if requires_auth else "")
                logger.info("ℹ️  Renseignez un fichier .env, par exemple :")
                logger.info("    # Gmail (depuis un réseau non bloqué)")
                logger.info("    SMTP_HOST=smtp.gmail.com / SMTP_PORT=587")
                logger.info("    SENDER_EMAIL=... / SENDER_PASSWORD=<mot de passe d'application>")
                logger.info("    # OU relais interne EPC (réseau pro) :")
                logger.info("    SMTP_HOST=<relais.epc-france.com> / SMTP_PORT=25")
                logger.info("    SENDER_EMAIL=epc-auto@epc-france.com  (sans SENDER_PASSWORD)")
                return

            emailer = EmailSender(smtp_host, smtp_port, sender_email,
                                  sender_password, timeout=smtp_timeout, use_ssl=use_ssl)
            
            # Crée le suffixe du sujet
            if lookback_days == DEFAULT_LOOKBACK_DAYS:
                subject_suffix = f"Dernier mois ({len(final_tenders)} offres)"
            else:
                subject_suffix = f"Nouvelles offres ({len(final_tenders)} offres)"
            
            success = emailer.send_tenders_email(final_tenders, subject_suffix=subject_suffix)
            
            if success:
                logger.info("✅ Email envoyé avec succès")
            else:
                logger.error("❌ Erreur lors de l'envoi de l'email")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Pipeline terminé avec succès")
        logger.info("=" * 80)
        
        return final_tenders
    
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EPC AutoAppelOffre - Pipeline de filtrage")
    parser.add_argument(
        "--lookback",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help=f"Nombre de jours à remonter (défaut: {DEFAULT_LOOKBACK_DAYS})"
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Ne pas envoyer d'email (debug mode)"
    )
    
    args = parser.parse_args()
    
    main(
        lookback_days=args.lookback,
        send_email=not args.no_email
    )