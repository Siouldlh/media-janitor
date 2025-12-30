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
        logger.info("Starting plan generation...")
        db = get_db_sync()

        config = get_config()

        # Collecte des données depuis tous les services
        logger.info("Initializing services...")
        plex_movies = []
        plex_series = []
        if config.plex:
            try:
                logger.info("Fetching Plex movies and series...")
                plex_service = PlexService()
                plex_movies = plex_service.get_movies()
                plex_series = plex_service.get_series()
                logger.info(f"Plex: {len(plex_movies)} movies, {len(plex_series)} series")
            except Exception as e:
                logger.warning(f"Error fetching from Plex: {e}")

        radarr_movies_data = []
        radarr_service = None
        if config.radarr:
            try:
                logger.info("Fetching Radarr movies...")
                radarr_service = RadarrService()
                radarr_movies_data = await radarr_service.get_movies()
                logger.info(f"Radarr: {len(radarr_movies_data)} movies")
            except Exception as e:
                logger.warning(f"Error fetching from Radarr: {e}")

        sonarr_series_data = []
        sonarr_service = None
        if config.sonarr:
            try:
                logger.info("Fetching Sonarr series...")
                sonarr_service = SonarrService()
                sonarr_series_data = await sonarr_service.get_series()
                logger.info(f"Sonarr: {len(sonarr_series_data)} series")
            except Exception as e:
                logger.warning(f"Error fetching from Sonarr: {e}")

        overseerr_requests = []
        overseerr_service = None
        if config.overseerr:
            try:
                logger.info("Fetching Overseerr requests...")
                overseerr_service = OverseerrService()
                overseerr_requests = await overseerr_service.get_requests()
                logger.info(f"Overseerr: {len(overseerr_requests)} requests")
            except Exception as e:
                logger.warning(f"Error fetching from Overseerr: {e}")

        qb_torrents = []
        qb_service = None
        if config.qbittorrent:
            try:
                logger.info("Fetching qBittorrent torrents...")
                qb_service = QBittorrentService()
                qb_torrents = qb_service.get_torrents()
                logger.info(f"qBittorrent: {len(qb_torrents)} torrents")
            except Exception as e:
                logger.warning(f"Error fetching from qBittorrent: {e}")

        # Conversion Radarr/Sonarr en MediaItem
        logger.info("Converting Radarr/Sonarr data to MediaItems...")
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
        logger.info(f"Converted {len(radarr_items)} Radarr movies to MediaItems")

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
        logger.info(f"Converted {len(sonarr_items)} Sonarr series to MediaItems")

        # Unification des médias
        logger.info("Matching and unifying media items across services...")
        all_plex = plex_movies + plex_series
        unified_items = self.matcher.unify_media_items(
            all_plex,
            radarr_items,
            sonarr_items,
            [],
            qb_torrents,
            qb_service
        )
        logger.info(f"Unified {len(unified_items)} media items")

        # Enrichir avec Overseerr requests
        if overseerr_service:
            logger.info("Enriching with Overseerr requests...")
            for item in unified_items:
                overseerr_service.enrich_media_item(item, overseerr_requests)
            logger.info("Overseerr enrichment completed")

        # Évaluation des règles et garde-fous
        logger.info("Evaluating rules and safety checks...")
        candidates = []
        max_items = config.app.max_items_per_scan if config.app else None
        
        for item in unified_items:
            # Limite max_items_per_scan si configuré
            if max_items and len(candidates) >= max_items:
                logger.info(f"Reached max_items_per_scan limit: {max_items}")
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
        logger.info(f"Found {len(candidates)} candidates for deletion")

        # Créer Plan en DB
        logger.info("Creating plan in database...")
        movies_count = sum(1 for item, _ in candidates if item.type == "movie")
        series_count = sum(1 for item, _ in candidates if item.type == "series")
        episodes_count = sum(1 for item, _ in candidates if item.type == "episode")
        total_size = sum(item.size_bytes for item, _ in candidates)
        
        plan = Plan(
            status="DRAFT",
            summary_json={
                "movies_count": movies_count,
                "series_count": series_count,
                "episodes_count": episodes_count,
                "total_size_bytes": total_size,
            }
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        logger.info(f"Plan {plan.id} created: {movies_count} movies, {series_count} series, {episodes_count} episodes, {total_size / 1024 / 1024 / 1024:.2f} GB")

        # Créer PlanItems
        logger.info("Creating plan items...")
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
        logger.info(f"Plan {plan.id} completed with {len(candidates)} items")
        return plan.id

