"""
Module de validation des annonces par GPT
"""

import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from config import GPT_MODEL, GPT_TEMPERATURE, GPT_SYSTEM_PROMPT, SCORE_THRESHOLD_FOR_EMAIL

logger = logging.getLogger(__name__)


class GPTValidator:
    """Valide les annonces avec GPT pour confirmer la pertinence"""
    
    def __init__(self, api_key: str = None):
        """
        Initialise le validateur GPT
        
        Args:
            api_key: Clé API OpenAI (sinon récupérée depuis env var OPENAI_API_KEY)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = GPT_MODEL
        self.temperature = GPT_TEMPERATURE
        self.system_prompt = GPT_SYSTEM_PROMPT
    
    def validate_tender(self, tender_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide une annonce avec GPT
        
        Args:
            tender_summary: Résumé de l'annonce avec titre, objet, descriptif
        
        Returns:
            Dictionnaire avec {pertinent, score_gpt, raison}
        """
        # Prépare le prompt utilisateur
        user_message = f"""
Titre: {tender_summary.get('titre', 'N/A')}

Objet: {tender_summary.get('objet', 'N/A')}

Descriptif: {tender_summary.get('descriptif', 'N/A')}

Acheteur: {tender_summary.get('acheteur', 'N/A')}
Région: {tender_summary.get('region', 'N/A')}
URL: {tender_summary.get('url', 'N/A')}
"""
        
        try:
            logger.debug(f"🤖 Validation GPT: {tender_summary.get('titre', 'N/A')[:60]}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Parse la réponse JSON
            response_text = response.choices[0].message.content.strip()
            
            # Essaie d'extraire le JSON
            try:
                # Cherche le JSON dans la réponse (au cas où GPT aurait du texte avant/après)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    logger.error(f"JSON non trouvé dans la réponse: {response_text}")
                    result = {
                        "pertinent": False,
                        "score": 0,
                        "raison": "Erreur parsing réponse GPT"
                    }
            except json.JSONDecodeError as e:
                logger.error(f"Erreur JSON: {e} | Réponse: {response_text}")
                result = {
                    "pertinent": False,
                    "score": 0,
                    "raison": "Erreur parsing JSON"
                }
            
            return result
        
        except Exception as e:
            logger.error(f"Erreur appel GPT: {e}")
            return {
                "pertinent": False,
                "score": 0,
                "raison": f"Erreur GPT: {str(e)}"
            }
    
    def batch_validate(self, tender_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Valide un lot d'annonces
        
        Args:
            tender_summaries: Liste des résumés d'annonces
        
        Returns:
            Liste avec les validations GPT ajoutées
        """
        validated = []
        total = len(tender_summaries)
        
        logger.info(f"🤖 Validation GPT de {total} annonces...")
        
        for i, summary in enumerate(tender_summaries, 1):
            logger.info(f"  [{i}/{total}] Validation...")
            
            gpt_result = self.validate_tender(summary)
            
            # Fusionne le résumé avec la validation GPT
            enhanced = {
                **summary,
                "gpt_pertinent": gpt_result.get("pertinent", False),
                "gpt_score": gpt_result.get("score", 0),
                "gpt_raison": gpt_result.get("raison", ""),
                "final_score": (summary.get("score_initial", 0) + gpt_result.get("score", 0)) / 2
            }
            
            if enhanced["gpt_pertinent"]:
                logger.info(f"    ✅ Pertinent (GPT score: {gpt_result.get('score', 0)})")
            else:
                logger.info(f"    ❌ Non pertinent (GPT score: {gpt_result.get('score', 0)})")
            
            validated.append(enhanced)
        
        return validated
    
    def filter_validated(self, validated_tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtre les annonces en gardant uniquement les pertinentes selon GPT
        et avec un score final >= seuil
        
        Args:
            validated_tenders: Liste des annonces validées par GPT
        
        Returns:
            Liste filtrée des annonces pertinentes
        """
        filtered = [
            t for t in validated_tenders 
            if t.get("gpt_pertinent", False) and t.get("final_score", 0) >= SCORE_THRESHOLD_FOR_EMAIL
        ]
        
        # Tri par score final décroissant
        filtered.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        logger.info(f"✅ {len(filtered)} annonces pertinentes après validation GPT")
        return filtered
