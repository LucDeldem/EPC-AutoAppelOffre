"""
Module de filtrage et scoring des annonces BOAMP
"""

import re
import logging
from typing import List, Dict, Any, Tuple
from config import KEYWORDS_SCORING, SCORE_THRESHOLD_FOR_GPT

logger = logging.getLogger(__name__)


class TenderFilter:
    """Filtre et score les annonces selon les critères métier"""
    
    def __init__(self):
        self.keywords = KEYWORDS_SCORING
        self.threshold = SCORE_THRESHOLD_FOR_GPT
    
    def filter_and_score(self, tenders: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int]]:
        """
        Filtre et score les annonces
        
        Args:
            tenders: Liste des annonces brutes de l'API BOAMP
        
        Returns:
            Liste de tuples (annonce, score) triée par score décroissant
            Ne retourne que les annonces avec score >= seuil
        """
        scored_tenders = []
        
        logger.info(f"📋 Scoring de {len(tenders)} annonces...")
        
        for tender in tenders:
            score = self._calculate_score(tender)
            
            if score >= self.threshold:
                scored_tenders.append((tender, score))
                logger.debug(f"  ✅ Score {score}: {tender.get('objet', 'N/A')[:60]}")
            else:
                logger.debug(f"  ❌ Score {score} (< {self.threshold}): {tender.get('objet', 'N/A')[:60]}")
        
        # Tri par score décroissant
        scored_tenders.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"📊 {len(scored_tenders)} annonces conservées (score >= {self.threshold})")
        return scored_tenders
    
    def _calculate_score(self, tender: Dict[str, Any]) -> int:
        """
        Calcule le score d'une annonce selon les mots-clés métier
        
        Args:
            tender: Dictionnaire représentant une annonce
        
        Returns:
            Score total (entier)
        """
        score = 0
        
        # Texte à analyser : titre + objet + description
        title = (tender.get("titre", "") or "").lower()
        objet = (tender.get("objet", "") or "").lower()
        descriptif = (tender.get("descriptif", "") or "").lower()
        full_text = f"{title} {objet} {descriptif}"
        
        # Parcours des mots-clés
        for keyword, points in self.keywords.items():
            keyword_lower = keyword.lower()
            
            # Compte les occurrences du mot-clé (séparé par des limites de mots)
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            matches = len(re.findall(pattern, full_text))
            
            if matches > 0:
                # Ajoute les points une seule fois par mot-clé (même s'il apparaît plusieurs fois)
                score += points
                logger.debug(f"    Keyword '{keyword}' trouvé {matches}x (+{points} pts)")
        
        return score
    
    def get_tender_summary(self, tender: Dict[str, Any], score: int) -> Dict[str, Any]:
        """
        Crée un résumé structuré d'une annonce avec son score
        
        Args:
            tender: Dictionnaire représentant une annonce
            score: Score calculé
        
        Returns:
            Dictionnaire structuré avec les infos pertinentes
        """
        return {
            "id": tender.get("id"),
            "titre": tender.get("titre", "N/A"),
            "objet": tender.get("objet", "N/A"),
            "descriptif": (tender.get("descriptif", "")[:500] + "...") 
                         if len(tender.get("descriptif", "")) > 500 
                         else tender.get("descriptif", "N/A"),
            "acheteur": tender.get("acheteur", "N/A"),
            "region": tender.get("region", "N/A"),
            "dateparution": tender.get("dateparution", "N/A"),
            "datedeadline": tender.get("datedeadline", "N/A"),
            "budget": tender.get("montantuht", "N/A"),
            "cpv": tender.get("cpv", []),
            "url": tender.get("urlannonce", "N/A"),
            "score_initial": score,
            "raw": tender  # Garde l'original pour débug
        }
    
    def batch_summarize(self, scored_tenders: List[Tuple[Dict[str, Any], int]]) -> List[Dict[str, Any]]:
        """
        Crée des résumés pour toutes les annonces scorées
        
        Args:
            scored_tenders: Liste de tuples (annonce, score)
        
        Returns:
            Liste de résumés structurés
        """
        summaries = []
        for tender, score in scored_tenders:
            summary = self.get_tender_summary(tender, score)
            summaries.append(summary)
        return summaries
