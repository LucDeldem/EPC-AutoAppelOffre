"""
Script principal - Orchestration du pipeline de filtrage d'appels d'offre
"""

import logging
import os
import sys
from dotenv import load_dotenv

from boamp_fetcher import BOAMPFetcher
from filtering import TenderFilter
from email_sender import send_email
from config import DEFAULT_LOOKBACK_DAYS, SCORE_THRESHOLD_FOR_EMAIL


def setup_logging(level: int = logging.INFO) -> None:
    """Logging UTF-8 compatible Windows"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log", encoding="utf-8")
        ]
    )


setup_logging()
logger = logging.getLogger(__name__)

# Charge .env local
load_dotenv()


def main(lookback_days: int = DEFAULT_LOOKBACK_DAYS, send_email_flag: bool = True):
    """
    Pipeline principal BOAMP
    """

    logger.info("=" * 80)
    logger.info("🚀 Démarrage EPC AutoAppelOffre")
    logger.info("=" * 80)

    try:
        # ===================== ÉTAPE 1 =====================
        logger.info("\n📡 Récupération BOAMP...")
        fetcher = BOAMPFetcher()
        raw_tenders = fetcher.fetch_tenders(lookback_days=lookback_days)

        logger.info(f"✅ {len(raw_tenders)} annonces récupérées")

        if not raw_tenders:
            logger.warning("⚠️ Aucune annonce")
            return

        # ===================== ÉTAPE 2 =====================
        logger.info("\n🎯 Filtrage + scoring...")
        filter_engine = TenderFilter()
        scored_tenders = filter_engine.filter_and_score(raw_tenders)

        logger.info(f"✅ {len(scored_tenders)} après filtrage")

        if not scored_tenders:
            logger.warning("⚠️ Aucun résultat après filtre")
            return

        # ===================== ÉTAPE 3 =====================
        logger.info("\n📋 Résumés...")
        summaries = filter_engine.batch_summarize(scored_tenders)

        final_tenders = [
            t for t in summaries
            if t.get("score_initial", 0) >= SCORE_THRESHOLD_FOR_EMAIL
        ]

        logger.info(f"✅ {len(final_tenders)} au-dessus du seuil")

        if not final_tenders:
            logger.warning("⚠️ Rien à envoyer")
            return

        # ===================== ÉTAPE 4 =====================
        logger.info("\n📊 Résultats :")
        logger.info("-" * 80)

        for i, tender in enumerate(final_tenders, 1):
            logger.info(f"\n{i}. [{tender['score_initial']}pts] {tender['titre'][:70]}")
            logger.info(f"   Acheteur: {tender['acheteur']}")
            logger.info(f"   Région: {tender['region']}")
            logger.info(f"   URL: {tender['url']}")

        # ===================== ÉTAPE 4bis =====================
        # Rapport HTML optionnel
        try:
            from email_sender import save_html_report
            report_path = save_html_report(final_tenders)
            logger.info(f"\n💾 Rapport HTML : {report_path}")
        except Exception as e:
            logger.warning(f"⚠️ Rapport HTML non généré : {e}")

        # ===================== ÉTAPE 5 =====================
        if send_email_flag:
            logger.info("\n📧 Envoi email (Resend API)...")

            subject = f"📢 BOAMP - {len(final_tenders)} opportunités détectées"

            html_content = "\n".join([
                f"""
                <h2>{t['titre']}</h2>
                <p><b>Score:</b> {t['score_initial']}</p>
                <p><b>Acheteur:</b> {t['acheteur']}</p>
                <p><b>Région:</b> {t['region']}</p>
                <p><a href="{t['url']}">Voir l'annonce</a></p>
                <hr>
                """
                for t in final_tenders
            ])

            send_email(subject, html_content)

            logger.info("✅ Email envoyé")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Pipeline terminé avec succès")
        logger.info("=" * 80)

        return final_tenders

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EPC AutoAppelOffre")

    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--no-email", action="store_true")

    args = parser.parse_args()

    main(
        lookback_days=args.lookback,
        send_email_flag=not args.no_email
    )