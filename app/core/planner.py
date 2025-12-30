"""Planificateur de suppression."""
from typing import List, Dict, Any
from datetime import datetime
import logging

from app.core.models import MediaItem

logger = logging.getLogger(__name__)
from app.core.matcher import MediaMatcher
from app.core.rules import RulesEngine
from app.core.safety import SafetyChecker
from app.services.plex import PlexService
from app.services.radarr import RadarrService
from app.services.sonarr import SonarrService
from app.services.overseerr import OverseerrService
from app.services.qbittorrent import QBittorrentService
from app.db.models import Plan, PlanItem
from app.db.database import get_db_sync


class Planner:
    """Génère un plan de suppression."""

    def __init__(self):
        self.matcher = MediaMatcher()
        self.rules_engine = RulesEngine()
        self.safety_checker = SafetyChecker()

    async def generate_plan(self) -> int:
        """Génère un plan de suppression et le sauvegarde en DB."""
        db = get_db_sync()

        # Collecte des données depuis tous les services
        plex_service = PlexService()
        radarr_service = RadarrService()
        sonarr_service = SonarrService()
        overseerr_service = OverseerrService()
        qb_service = QBittorrentService()

        # Récupération des données
        plex_movies = plex_service.get_movies()
        plex_series = plex_service.get_series()
        radarr_movies_data = await radarr_service.get_movies()
        sonarr_series_data = await sonarr_service.get_series()
        overseerr_requests = await overseerr_service.get_requests()
        qb_torrents = qb_service.get_torrents()

        # Conversion Radarr/Sonarr en MediaItem
        radarr_items = []
        if radarr_service:
            for movie_data in radarr_movies_data:
                item = MediaItem(
                    type="movie",
                    title=movie_data.get("title", ""),
                    year=movie_data.get("year"),
                    tmdb_id=movie_data.get("tmdbId"),
                )
                radarr_service.enrich_media_item(item, movie_data)
                radarr_items.append(item)

        sonarr_items = []
        if sonarr_service:
            for series_data in sonarr_series_data:
                item = MediaItem(
                    type="series",
                    title=series_data.get("title", ""),
                    year=series_data.get("year"),
                    tvdb_id=series_data.get("tvdbId"),
                    tmdb_id=series_data.get("tmdbId"),
                )
                sonarr_service.enrich_media_item(item, series_data)
                sonarr_items.append(item)

        # Note: Overseerr enrichment is done after unification

        # Unification des médias
        all_plex = plex_movies + plex_series
        unified_items = self.matcher.unify_media_items(
            all_plex,
            radarr_items,
            sonarr_items,
            [],
            qb_torrents,
            qb_service
        )

        # Enrichir avec Overseerr requests
        if overseerr_service:
            for item in unified_items:
                overseerr_service.enrich_media_item(item, overseerr_requests)

        # Évaluation des règles et garde-fous
        candidates = []
        max_items = self.config.app.max_items_per_scan if self.config.app else None
        
        for item in unified_items:
            # Limite max_items_per_scan si configuré
            if max_items and len(candidates) >= max_items:
                break
                
            # Évaluer règle
            is_candidate, rule = self.rules_engine.evaluate(item)
            if not is_candidate:
                continue

            # Vérifier garde-fous
            is_protected, protected_reason = self.safety_checker.is_protected(item)
            if is_protected:
                # Stocker la raison de protection pour affichage
                item.metadata["protected_reason"] = protected_reason
                continue

            candidates.append((item, rule))

        # Créer Plan en DB
        plan = Plan(
            status="DRAFT",
            summary_json={
                "movies_count": sum(1 for item, _ in candidates if item.type == "movie"),
                "series_count": sum(1 for item, _ in candidates if item.type == "series"),
                "episodes_count": sum(1 for item, _ in candidates if item.type == "episode"),
                "total_size_bytes": sum(item.size_bytes for item, _ in candidates),
            }
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        # Créer PlanItems
        for item, rule in candidates:
            plan_item = PlanItem(
                plan_id=plan.id,
                selected=True,  # Par défaut sélectionné
                media_type=item.type,
                title=item.title,
                year=item.year,
                ids_json={
                    "tmdb": item.tmdb_id,
                    "tvdb": item.tvdb_id,
                    "imdb": item.imdb_id,
                },
                path=item.get_primary_path() or "",
                size_bytes=item.size_bytes,
                last_viewed_at=item.last_viewed_at,
                view_count=item.view_count,
                never_watched=item.never_watched,
                rule=rule,
                protected_reason=None,  # Items protégés ne sont pas dans candidates
                qb_hashes_json=item.qb_hashes,
                meta_json={
                    "plex_rating_key": item.plex_rating_key,
                    "overseerr_request_id": item.overseerr_request_id,
                    "overseerr_status": item.overseerr_status,
                    "overseerr_requested_by": item.overseerr_requested_by,
                    "tags": item.tags,
                    "monitored": item.monitored,
                    **item.metadata,
                },
            )
            db.add(plan_item)

        db.commit()
        return plan.id

