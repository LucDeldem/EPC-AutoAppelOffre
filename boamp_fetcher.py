"""
Récupération des annonces depuis l'API BOAMP (Opendatasoft Explore v2.1).

L'ancienne API "Solr" (q=cpv:..., wt=json, response.docs/numFound) a été
supprimée et renvoie des 404. On utilise désormais l'endpoint records v2.1 :
  GET .../catalog/datasets/boamp/records?where=...&limit=...&offset=...
  Réponse : { "total_count": N, "results": [ {champs...} ] }
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from requests.adapters import HTTPAdapter

try:  # urllib3 est fourni avec requests
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    Retry = None

from config import (
    ALLOWED_NATURES,
    BOAMP_AVIS_URL_TPL,
    BOAMP_MAX_PAGES,
    BOAMP_PAGE_SIZE,
    BOAMP_RECORDS_URL,
    BOAMP_TIMEOUT,
    DEFAULT_LOOKBACK_DAYS,
    EXCLUDE_EXPIRED_DEADLINE,
    GEO_FILTER_ENABLED,
    GEO_KEEP_UNKNOWN,
    KEEP_TENDERS_WITHOUT_DEADLINE,
    ONLY_OPEN_TENDERS,
    SEARCH_TERMS,
    SOUTH_DEPARTMENTS,
)

logger = logging.getLogger(__name__)


class BOAMPFetcher:
    """Récupère et normalise les annonces depuis l'API BOAMP v2.1."""

    def __init__(self):
        self.url = BOAMP_RECORDS_URL
        self.timeout = BOAMP_TIMEOUT
        self.session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "Accept": "application/json",
            "User-Agent": "EPC-AutoAppelOffre/2.0 (+https://github.com/LucDeldem)",
        })
        if Retry is not None:
            retry = Retry(
                total=3,
                backoff_factor=1.0,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET",),
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
        return session

    # ------------------------------------------------------------------ #
    # API publique
    # ------------------------------------------------------------------ #
    def fetch_tenders(self, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> List[Dict[str, Any]]:
        """Récupère les annonces des N derniers jours, normalisées et dédupliquées."""
        start_date = (datetime.now() - timedelta(days=lookback_days)).date().isoformat()
        logger.info("Récupération BOAMP depuis %s ...", start_date)

        # 1) Pré-filtrage côté serveur par mots-clés métier (volume réduit).
        where = self._build_where(start_date, with_keywords=True)
        raw = self._query(where)

        # 2) Fallback : si la requête plein-texte échoue ou ne renvoie rien,
        #    on retombe sur un filtrage par date seule (scoring 100% client).
        if not raw:
            logger.warning("Recherche par mots-clés vide/indisponible -> fallback date seule")
            raw = self._query(self._build_where(start_date, with_keywords=False))

        normalized = [self._normalize(rec) for rec in raw]

        # Déduplication : par identifiant (idweb) si présent, sinon repli sur
        # une clé titre+acheteur. Évite qu'une même annonce remontée par
        # plusieurs mots-clés apparaisse en double dans l'e-mail.
        seen, unique = set(), []
        for tender in normalized:
            tid = tender.get("id")
            key = (
                str(tid).strip().lower() if tid
                else (
                    (tender.get("titre") or "").strip().lower(),
                    (tender.get("acheteur") or "").strip().lower(),
                )
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(tender)

        logger.info("Total : %d annonces uniques récupérées", len(unique))

        # 3) Filtrage des offres dont la date limite de réponse est dépassée
        #    (on ne peut plus candidater -> offre plus disponible).
        if EXCLUDE_EXPIRED_DEADLINE:
            unique = self._filter_open_deadline(unique)

        # 4) Filtrage géographique (Sud de la France)
        if GEO_FILTER_ENABLED:
            unique = self._filter_south(unique)
        return unique

    # ------------------------------------------------------------------ #
    # Filtre date limite de réponse
    # ------------------------------------------------------------------ #
    @staticmethod
    def _filter_open_deadline(tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ne conserve que les annonces dont la date limite n'est pas dépassée."""
        today = datetime.now().date()
        kept, expired, unknown = [], 0, 0
        for t in tenders:
            deadline = BOAMPFetcher._parse_deadline(t.get("datedeadline"))
            if deadline is None:
                unknown += 1
                if KEEP_TENDERS_WITHOUT_DEADLINE:
                    kept.append(t)
                continue
            if deadline >= today:
                kept.append(t)
            else:
                expired += 1
        logger.info(
            "Filtre disponibilité : %d ouvertes, %d expirées, %d sans date limite%s",
            len(kept), expired, unknown,
            " (gardées)" if KEEP_TENDERS_WITHOUT_DEADLINE else " (rejetées)",
        )
        return kept

    @staticmethod
    def _parse_deadline(value: Any):
        """Parse une date limite ODS en `date`, ou None si absente/illisible."""
        if not value or value == "N/A":
            return None
        text = str(value).strip()
        # ODS renvoie souvent un ISO 8601 ("2026-07-15" ou "2026-07-15T12:00:00+02:00").
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        # Repli : on tente quelques formats fréquents.
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------ #
    # Filtre géographique
    # ------------------------------------------------------------------ #
    @staticmethod
    def _filter_south(tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ne conserve que les annonces situées dans les départements du Sud."""
        kept, dropped, unknown = [], 0, 0
        for t in tenders:
            depts = t.get("departements") or set()
            if not depts:
                unknown += 1
                if GEO_KEEP_UNKNOWN:
                    kept.append(t)
                else:
                    dropped += 1
                continue
            if depts & SOUTH_DEPARTMENTS:
                kept.append(t)
            else:
                dropped += 1
        logger.info(
            "Filtre géo (Sud) : %d gardées, %d hors zone, %d sans département%s",
            len(kept), dropped, unknown,
            " (gardées)" if GEO_KEEP_UNKNOWN else " (rejetées)",
        )
        return kept

    # ------------------------------------------------------------------ #
    # Construction des requêtes ODSQL
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_where(start_date: str, with_keywords: bool) -> str:
        """Construit la clause `where` ODSQL."""
        clause = f'dateparution >= "{start_date}"'

        # Ne garder que les avis d'appel à la concurrence encore ouverts :
        # on exclut les "ATTRIBUTION" (marché déjà accepté), "ANNULATION", etc.
        if ONLY_OPEN_TENDERS and ALLOWED_NATURES:
            natures = " or ".join(f'nature = "{n}"' for n in sorted(ALLOWED_NATURES))
            clause = f"{clause} and ({natures})"

        if with_keywords and SEARCH_TERMS:
            # Une chaîne entre guillemets dans `where` = recherche plein-texte.
            terms = " or ".join(f'"{t}"' for t in SEARCH_TERMS)
            clause = f"{clause} and ({terms})"
        return clause

    def _query(self, where: str) -> List[Dict[str, Any]]:
        """Exécute une requête paginée et renvoie la liste brute des `results`."""
        results: List[Dict[str, Any]] = []
        for page in range(BOAMP_MAX_PAGES):
            offset = page * BOAMP_PAGE_SIZE
            params = {
                "where": where,
                "order_by": "dateparution desc",
                "limit": BOAMP_PAGE_SIZE,
                "offset": offset,
                "lang": "fr",
                "timezone": "Europe/Paris",
            }
            try:
                resp = self.session.get(self.url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
            except requests.HTTPError as e:
                # 400 = clause invalide -> on signale et on laisse le fallback agir.
                logger.error("Erreur HTTP BOAMP (offset=%d): %s", offset, e)
                break
            except Exception as e:
                logger.error("Erreur requête BOAMP (offset=%d): %s", offset, e)
                break

            # v2.1 : {total_count, results}. On gère aussi un éventuel format v2.0.
            batch = data.get("results")
            if batch is None:
                batch = [r.get("record", {}).get("fields", r)
                         for r in data.get("records", [])]
            if not batch:
                break

            results.extend(batch)
            total = data.get("total_count", len(results))
            logger.info("  page %d : %d annonces (cumul %d/%s)",
                        page + 1, len(batch), len(results), total)

            if len(results) >= total or len(batch) < BOAMP_PAGE_SIZE:
                break
        return results

    # ------------------------------------------------------------------ #
    # Normalisation vers le schéma canonique du pipeline
    # ------------------------------------------------------------------ #
    @staticmethod
    def _as_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(BOAMPFetcher._as_text(v) for v in value if v)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _extract_departments(rec: Dict[str, Any]) -> set:
        """Extrait l'ensemble des codes département d'un enregistrement.

        Gère les listes, la Corse (2A/2B/20) et un repli sur le code postal
        (2 premiers chiffres) si `code_departement` est absent.
        """
        depts = set()

        def add(value):
            for v in (value if isinstance(value, (list, tuple)) else [value]):
                s = str(v).strip().upper()
                if not s:
                    continue
                if s in ("2A", "2B"):
                    depts.add(s)
                elif s[:3].isdigit() and s[:3] in ("971", "972", "973", "974", "976"):
                    depts.add(s[:3])  # DOM
                elif s[:2].isdigit():
                    depts.add(s[:2])

        add(rec.get("code_departement"))
        if not depts:
            # Replis : champs pouvant contenir un code postal
            for key in ("cp", "code_postal", "lieu_execution_code"):
                add(rec.get(key))
        return depts

    def _normalize(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """Convertit un enregistrement ODS en dict canonique stable."""
        idweb = self._as_text(rec.get("idweb"))
        objet = self._as_text(rec.get("objet"))
        url = self._as_text(rec.get("url_avis")) or (
            BOAMP_AVIS_URL_TPL.format(idweb=idweb) if idweb else "N/A"
        )

        # Départements (pour le filtre géo) + affichage région lisible.
        depts = self._extract_departments(rec)
        region = (
            self._as_text(rec.get("nom_departement"))
            or (", ".join(sorted(depts)) if depts else "")
            or self._as_text(rec.get("perimetre"))
            or "N/A"
        )

        # Description AFFICHÉE : propre et lisible (objet + libellés humains),
        # sans dump JSON.
        descriptif = objet
        for key in ("descripteur_libelle", "famille_libelle"):
            extra = self._as_text(rec.get(key))
            if extra and extra.lower() not in descriptif.lower():
                descriptif = f"{descriptif} — {extra}" if descriptif else extra

        # Haystack INTERNE (non affiché) : contenu enrichi pour le scoring,
        # y compris les données techniques imbriquées.
        haystack = " ".join(self._as_text(rec.get(k)) for k in (
            "objet", "descripteur_libelle", "famille_libelle",
            "nature", "type_marche", "donnees",
        ))

        return {
            "id": idweb or None,
            "titre": objet[:140] if objet else "N/A",
            "objet": objet or "N/A",
            "descriptif": descriptif or "N/A",
            "acheteur": self._as_text(rec.get("nomacheteur")) or "N/A",
            "region": region,
            "departements": depts,
            "dateparution": self._as_text(rec.get("dateparution")) or "N/A",
            "datedeadline": self._as_text(rec.get("datelimitereponse")) or "N/A",
            "budget": self._as_text(rec.get("montant")) or "N/A",
            "cpv": rec.get("code_cpv") or rec.get("cpv") or [],
            "url": url,
            "type_marche": self._as_text(rec.get("type_marche")),
            "_haystack": haystack,
            "raw": rec,
        }