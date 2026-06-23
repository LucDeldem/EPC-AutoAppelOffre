"""
Module de récupération des annonces depuis l'API BOAMP
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from config import BOAMP_API_BASE_URL, BOAMP_TIMEOUT, CPV_CODES, DEFAULT_LOOKBACK_DAYS

logger = logging.getLogger(__name__)


class BOAMPFetcher:
    """Récupère les annonces depuis l'API BOAMP"""
    
    def __init__(self):
        self.base_url = BOAMP_API_BASE_URL
        self.timeout = BOAMP_TIMEOUT
    
    def fetch_tenders(self, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> List[Dict[str, Any]]:
        """
        Récupère les annonces BOAMP des N derniers jours
        
        Args:
            lookback_days: Nombre de jours à remonter (défaut: 30)
        
        Returns:
            Liste des annonces brutes depuis l'API
        """
        all_tenders = []
        start_date = (datetime.now() - timedelta(days=lookback_days)).date()
        
        logger.info(f"🔍 Récupération BOAMP depuis {start_date}...")
        
        # On récupère d'abord par CPV
        for cpv_code in CPV_CODES:
            try:
                tenders = self._fetch_by_cpv(cpv_code, start_date)
                logger.info(f"  ✅ CPV {cpv_code}: {len(tenders)} annonces")
                all_tenders.extend(tenders)
            except Exception as e:
                logger.warning(f"  ❌ Erreur CPV {cpv_code}: {e}")
        
        # Déduplification par ID
        seen_ids = set()
        unique_tenders = []
        for tender in all_tenders:
            tender_id = tender.get("id")
            if tender_id not in seen_ids:
                seen_ids.add(tender_id)
                unique_tenders.append(tender)
        
        logger.info(f"📊 Total: {len(unique_tenders)} annonces uniques après CPV")
        return unique_tenders
    
    def _fetch_by_cpv(self, cpv_code: str, start_date: str) -> List[Dict[str, Any]]:
        """
        Récupère les annonces pour un code CPV spécifique
        
        Args:
            cpv_code: Code CPV (ex: "45232200")
            start_date: Date de début au format YYYY-MM-DD
        
        Returns:
            Liste des annonces pour ce CPV
        """
        tenders = []
        start = 0
        rows_per_page = 100
        
        while True:
            params = {
                "q": f"cpv:{cpv_code}",
                "start": start,
                "rows": rows_per_page,
                "sort": "dateparution:desc",
                "wt": "json"
            }
            
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                docs = data.get("response", {}).get("docs", [])
                if not docs:
                    break
                
                # Filtre sur la date
                for doc in docs:
                    date_parution = doc.get("dateparution", "")
                    if date_parution >= str(start_date):
                        tenders.append(doc)
                
                # Pagination
                total_results = data.get("response", {}).get("numFound", 0)
                if start + rows_per_page >= total_results:
                    break
                
                start += rows_per_page
            
            except Exception as e:
                logger.error(f"Erreur requête BOAMP CPV {cpv_code}: {e}")
                break
        
        return tenders
    
    def fetch_by_keyword(self, keyword: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> List[Dict[str, Any]]:
        """
        Récupère les annonces par mot-clé (fallback si besoin)
        
        Args:
            keyword: Mot-clé de recherche
            lookback_days: Nombre de jours à remonter
        
        Returns:
            Liste des annonces
        """
        tenders = []
        start = 0
        rows_per_page = 100
        start_date = (datetime.now() - timedelta(days=lookback_days)).date()
        
        while True:
            params = {
                "q": keyword,
                "start": start,
                "rows": rows_per_page,
                "sort": "dateparution:desc",
                "wt": "json"
            }
            
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                docs = data.get("response", {}).get("docs", [])
                if not docs:
                    break
                
                # Filtre sur la date
                for doc in docs:
                    date_parution = doc.get("dateparution", "")
                    if date_parution >= str(start_date):
                        tenders.append(doc)
                
                # Pagination
                total_results = data.get("response", {}).get("numFound", 0)
                if start + rows_per_page >= total_results:
                    break
                
                start += rows_per_page
            
            except Exception as e:
                logger.error(f"Erreur requête BOAMP mot-clé '{keyword}': {e}")
                break
        
        return tenders
