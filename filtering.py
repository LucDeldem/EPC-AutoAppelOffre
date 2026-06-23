"""
Filtrage et scoring des annonces BOAMP par mots-clés métier.

Détection robuste :
  - insensible à la casse et aux accents (soutenement == soutènement) ;
  - insensible au pluriel simple (micropieu / micropieux) ;
  - insensible aux espaces multiples et aux apostrophes typographiques ;
  - périmètre de texte maîtrisé (objet + description) pour limiter les
    faux positifs sur les noms d'acheteurs ou les adresses.
"""

import re
import logging
import unicodedata
from typing import Any, Dict, List, Tuple

from config import KEYWORDS_SCORING, SCORE_THRESHOLD_KEEP

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Minuscule + suppression des accents + apostrophes/espaces normalisés."""
    if not text:
        return ""
    text = text.replace("’", "'").replace("`", "'")
    # Décomposition Unicode puis suppression des marques diacritiques
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _build_pattern(keyword: str) -> re.Pattern:
    """Compile un motif robuste (accents, pluriel, espaces) pour un mot-clé.

    Le pluriel simple est toléré sur CHAQUE mot de la locution : un radical
    finissant par 's' voit son 's' rendu optionnel, sinon un 's?' est ajouté.
    Ainsi « micropieux » matche aussi « micropieu », et « tirant d'ancrage »
    matche « tirants d'ancrage ».
    """
    pieces = []
    for tok in re.split(r"[\s\-]+", normalize_text(keyword)):
        if not tok:
            continue
        stem = tok[:-1] if (tok[-1:] in ("s", "x") and len(tok) >= 5) else tok
        pieces.append(re.escape(stem) + "[sx]?")  # pluriels français en -s et -x
    # Séparateur tolérant espace OU trait d'union (micro-berlinoise == micro berlinoise)
    return re.compile(r"\b" + r"[\s\-]+".join(pieces) + r"\b")


class TenderFilter:
    """Filtre et score les annonces selon les critères métier."""

    def __init__(self):
        self.keywords = KEYWORDS_SCORING
        self.threshold = SCORE_THRESHOLD_KEEP
        # Patterns compilés une seule fois
        self._patterns = {kw: _build_pattern(kw) for kw in self.keywords}

    # ------------------------------------------------------------------ #
    def filter_and_score(self, tenders: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int]]:
        """Retourne les annonces (avec score >= seuil), triées par score décroissant."""
        scored: List[Tuple[Dict[str, Any], int]] = []
        logger.info("Scoring de %d annonces...", len(tenders))

        for tender in tenders:
            score, matched = self._score(tender)
            if score >= self.threshold:
                tender["_matched"] = matched          # mémorisé pour l'e-mail
                scored.append((tender, score))
                logger.debug("  Score %d (%s): %s",
                             score, ", ".join(matched), (tender.get("objet") or "")[:60])

        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info("%d annonces conservées (score >= %d)", len(scored), self.threshold)
        return scored

    # ------------------------------------------------------------------ #
    def _score(self, tender: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Calcule le score et la liste des mots-clés détectés."""
        # Périmètre maîtrisé : on privilégie l'objet/description, et on complète
        # avec le haystack (contenu enrichi) fourni par le fetcher s'il existe.
        parts = [
            tender.get("titre", ""),
            tender.get("objet", ""),
            tender.get("descriptif", ""),
            tender.get("_haystack", ""),
        ]
        text = normalize_text(" ".join(p for p in parts if p))

        score = 0
        matched: List[str] = []
        for keyword, points in self.keywords.items():
            if self._patterns[keyword].search(text):
                score += points
                matched.append(keyword)
        return score, matched

    # ------------------------------------------------------------------ #
    def get_tender_summary(self, tender: Dict[str, Any], score: int) -> Dict[str, Any]:
        """Résumé structuré d'une annonce (schéma stable pour l'e-mail)."""
        descriptif = tender.get("descriptif", "") or ""
        if len(descriptif) > 600:
            descriptif = descriptif[:600].rstrip() + "…"

        return {
            "id": tender.get("id"),
            "titre": tender.get("titre", "N/A"),
            "objet": tender.get("objet", "N/A"),
            "descriptif": descriptif or "N/A",
            "acheteur": tender.get("acheteur", "N/A"),
            "region": tender.get("region", "N/A"),
            "dateparution": tender.get("dateparution", "N/A"),
            "datedeadline": tender.get("datedeadline", "N/A"),
            "type_marche": tender.get("type_marche", ""),
            "cpv": tender.get("cpv", []),
            "url": tender.get("url", "N/A"),
            "score_initial": score,
            "matched_keywords": tender.get("_matched", []),
        }

    def batch_summarize(self, scored_tenders: List[Tuple[Dict[str, Any], int]]) -> List[Dict[str, Any]]:
        return [self.get_tender_summary(t, s) for t, s in scored_tenders]