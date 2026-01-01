"""Planificateur de suppression."""
from typing import List, Dict, Any
from datetime import datetime
import logging

from app.core.models import MediaItem

logger = logging.getLogger(__name__)
from app.core.matcher import MediaMatcher
from app.core.rules import RulesEngine
from app.core.safety import SafetyChecker
from app.services.radarr import RadarrService
from app.services.sonarr import SonarrService
from app.services.overseerr import OverseerrService
from app.services.qbittorrent import QBittorrentService
from app.services.tautulli import TautulliService
from app.db.models import Plan, PlanItem
from app.db.database import get_db_sync
from app.config import get_config


class Planner:
    """Génère un plan de suppression."""

    def __init__(self, scan_id: str = None):
        self.matcher = MediaMatcher()
        self.rules_engine = RulesEngine()
        self.safety_checker = SafetyChecker()
        self.scan_id = scan_id

    def _emit_progress(self, step: str, progress: int, message: str = None, data: dict = None):
        """Émet un événement de progression si scan_id est défini."""
        if not self.scan_id:
            return
        
        from app.main import scan_progress_store
        if self.scan_id in scan_progress_store:
            scan_progress_store[self.scan_id].update({
                "current_step": step,
                "progress": progress,
            })
            if message:
                scan_progress_store[self.scan_id]["logs"].append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "message": message
                })
                # Garder seulement les 100 derniers logs
                scan_progress_store[self.scan_id]["logs"] = scan_progress_store[self.scan_id]["logs"][-100:]
            if data:
                scan_progress_store[self.scan_id].update(data)

    async def generate_plan(self) -> int:
        """Génère un plan de suppression et le sauvegarde en DB."""
        logger.info("Starting plan generation...")
        self._emit_progress("initializing", 0, "Initialisation du scan...")
        db = get_db_sync()

        config = get_config()

        # Collecte des données depuis tous les services
        logger.info("Initializing services...")
        
        # Tautulli watch history (source de vérité)
        self._emit_progress("tautulli_fetching", 10, "Récupération de l'historique Tautulli...")
        movie_watch_map = {}
        episode_watch_map = {}
        series_watch_map = {}
        tautulli_service = None
        if config.tautulli and config.tautulli.enabled:
            try:
                logger.info("Fetching Tautulli watch history...")
                tautulli_service = TautulliService()
                movie_watch_map = tautulli_service.get_movie_watch_map()
                logger.info(f"Tautulli movie watch map: {len(movie_watch_map)} movies")
                
                episode_watch_map = tautulli_service.get_episode_watch_map()
                logger.info("Tautulli episode watch map", count=len(episode_watch_map))
                
                series_watch_map = tautulli_service.get_series_watch_map()
                logger.info("Tautulli series watch map", count=len(series_watch_map))
                
                total_matched = len(movie_watch_map) + len(episode_watch_map) + len(series_watch_map)
                logger.info(f"Tautulli: {len(movie_watch_map)} movies, {len(episode_watch_map)} episodes, {len(series_watch_map)} series (total: {total_matched})")
                self._emit_progress("tautulli_fetched", 15, f"Tautulli: {len(movie_watch_map)} films, {len(episode_watch_map)} épisodes")
            except Exception as e:
                logger.warning(f"Error fetching from Tautulli: {e}", exc_info=True)
                self._emit_progress("tautulli_error", 15, f"Erreur Tautulli: {str(e)}")

        self._emit_progress("radarr_fetching", 20, "Récupération des données Radarr...")
        radarr_movies_data = []
        radarr_service = None
        if config.radarr:
            try:
                logger.info("Fetching Radarr movies...")
                radarr_service = RadarrService()
                radarr_movies_data = await radarr_service.get_movies()
                logger.info(f"Radarr: {len(radarr_movies_data)} movies")
                self._emit_progress("radarr_fetched", 25, f"Radarr: {len(radarr_movies_data)} films")
            except Exception as e:
                logger.warning(f"Error fetching from Radarr: {e}", exc_info=True)
                self._emit_progress("radarr_error", 25, f"Erreur Radarr: {str(e)}")

        self._emit_progress("sonarr_fetching", 30, "Récupération des données Sonarr...")
        sonarr_series_data = []
        sonarr_service = None
        if config.sonarr:
            try:
                logger.info("Fetching Sonarr series...")
                sonarr_service = SonarrService()
                sonarr_series_data = await sonarr_service.get_series()
                logger.info(f"Sonarr: {len(sonarr_series_data)} series")
                self._emit_progress("sonarr_fetched", 35, f"Sonarr: {len(sonarr_series_data)} séries")
            except Exception as e:
                logger.warning(f"Error fetching from Sonarr: {e}", exc_info=True)
                self._emit_progress("sonarr_error", 35, f"Erreur Sonarr: {str(e)}")

        self._emit_progress("overseerr_fetching", 40, "Récupération des données Overseerr...")
        overseerr_requests = []
        overseerr_service = None
        if config.overseerr:
            try:
                logger.info("Fetching Overseerr requests...")
                overseerr_service = OverseerrService()
                overseerr_requests = await overseerr_service.get_requests()
                logger.info(f"Overseerr: {len(overseerr_requests)} requests")
                self._emit_progress("overseerr_fetched", 45, f"Overseerr: {len(overseerr_requests)} requêtes")
            except Exception as e:
                logger.warning(f"Error fetching from Overseerr: {e}")
                self._emit_progress("overseerr_error", 45, f"Erreur Overseerr: {str(e)}")

        self._emit_progress("qbittorrent_fetching", 50, "Récupération des données qBittorrent...")
        qb_torrents = []
        qb_service = None
        if config.qbittorrent:
            try:
                logger.info("Fetching qBittorrent torrents...")
                qb_service = QBittorrentService()
                qb_torrents = qb_service.get_torrents()
                logger.info(f"qBittorrent: {len(qb_torrents)} torrents")
                self._emit_progress("qbittorrent_fetched", 55, f"qBittorrent: {len(qb_torrents)} torrents")
            except Exception as e:
                logger.warning(f"Error fetching from qBittorrent: {e}")
                self._emit_progress("qbittorrent_error", 55, f"Erreur qBittorrent: {str(e)}")

        # Conversion Radarr/Sonarr en MediaItem avec enrichissement Tautulli
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
                
                # Enrichir avec Tautulli watch history
                if tautulli_service and item.tmdb_id:
                    watch_stats = movie_watch_map.get(item.tmdb_id)
                    if watch_stats:
                        item.last_viewed_at = watch_stats.get("last_watched_at")
                        item.view_count = watch_stats.get("view_count", 0)
                        # Si on a des données avec last_watched_at ou view_count > 0, alors jamais vu = False
                        if item.last_viewed_at or item.view_count > 0:
                            item.never_watched = False
                        else:
                            item.never_watched = watch_stats.get("never_watched", True)
                        item.metadata["watch_source"] = "Tautulli"
                        item.metadata["last_watched_user"] = watch_stats.get("last_user")
                        logger.debug("movie_enriched_tautulli",
                                   title=item.title,
                                   tmdb_id=item.tmdb_id,
                                   view_count=item.view_count,
                                   last_watched=item.last_viewed_at.isoformat() if item.last_viewed_at else None)
                    else:
                        # Pas de données Tautulli = jamais vu
                        item.never_watched = True
                        item.view_count = 0
                        item.metadata["watch_source"] = "Tautulli (never watched)"
                        logger.debug("movie_no_tautulli_data",
                                   title=item.title,
                                   tmdb_id=item.tmdb_id)
                
                radarr_items.append(item)
        logger.info(f"Converted {len(radarr_items)} Radarr movies to MediaItems")

        sonarr_items = []
        episode_items = []
        if sonarr_service:
            logger.info("Processing Sonarr series and episodes...")
            for series_data in sonarr_series_data:
                series_item = MediaItem(
                    type="series",
                    title=series_data.get("title", ""),
                    year=series_data.get("year"),
                    tvdb_id=series_data.get("tvdbId"),
                    tmdb_id=series_data.get("tmdbId"),
                )
                sonarr_service.enrich_media_item(series_item, series_data)
                
                # Enrichir avec Tautulli watch history (série entière)
                if tautulli_service and series_item.tvdb_id:
                    watch_stats = series_watch_map.get(series_item.tvdb_id)
                    if watch_stats:
                        series_item.last_viewed_at = watch_stats.get("last_watched_at")
                        series_item.view_count = watch_stats.get("view_count", 0)
                        if series_item.last_viewed_at or series_item.view_count > 0:
                            series_item.never_watched = False
                        else:
                            series_item.never_watched = watch_stats.get("never_watched", True)
                        series_item.metadata["watch_source"] = "Tautulli"
                        series_item.metadata["last_watched_user"] = watch_stats.get("last_user")
                
                sonarr_items.append(series_item)
                
                # Récupérer les épisodes de cette série pour traitement individuel
                series_id = series_data.get("id")
                if series_id:
                    try:
                        episodes_data = sonarr_service.get_episodes_sync(series_id)
                        logger.debug(f"Retrieved {len(episodes_data)} episodes for series '{series_item.title}'")
                        
                        for episode_data in episodes_data:
                            # Créer un MediaItem pour chaque épisode
                            episode_item = MediaItem(
                                type="episode",
                                title=f"{series_item.title} - S{episode_data.get('seasonNumber', 0):02d}E{episode_data.get('episodeNumber', 0):02d}",
                                year=series_item.year,
                                tvdb_id=series_item.tvdb_id,  # TVDb ID de la série
                                tmdb_id=series_item.tmdb_id,
                            )
                            
                            # Enrichir avec les données Sonarr de l'épisode
                            episode_item.sonarr_path = episode_data.get("path")
                            episode_item.monitored = episode_data.get("monitored", True)
                            episode_item.metadata["sonarr_id"] = series_id
                            episode_item.metadata["sonarr_episode_id"] = episode_data.get("id")
                            episode_item.metadata["sonarr_title"] = series_item.title
                            episode_item.metadata["series_title"] = series_item.title
                            episode_item.metadata["season_number"] = episode_data.get("seasonNumber")
                            episode_item.metadata["episode_number"] = episode_data.get("episodeNumber")
                            episode_item.metadata["episode_title"] = episode_data.get("title", "")
                            episode_item.metadata["sonarr_added"] = episode_data.get("added")
                            
                            # Taille de l'épisode
                            if episode_data.get("episodeFile"):
                                episode_file = episode_data.get("episodeFile", {})
                                episode_item.size_bytes = episode_file.get("size", 0)
                            
                            # Enrichir avec Tautulli watch history (épisode individuel)
                            if tautulli_service and episode_item.tvdb_id:
                                season_num = episode_data.get("seasonNumber")
                                episode_num = episode_data.get("episodeNumber")
                                if season_num is not None and episode_num is not None:
                                    watch_stats = episode_watch_map.get((episode_item.tvdb_id, int(season_num), int(episode_num)))
                                    if watch_stats:
                                        episode_item.last_viewed_at = watch_stats.get("last_watched_at")
                                        episode_item.view_count = watch_stats.get("view_count", 0)
                                        if episode_item.last_viewed_at or episode_item.view_count > 0:
                                            episode_item.never_watched = False
                                        else:
                                            episode_item.never_watched = watch_stats.get("never_watched", True)
                                        episode_item.metadata["watch_source"] = "Tautulli"
                                        episode_item.metadata["last_watched_user"] = watch_stats.get("last_user")
                                    else:
                                        # Pas de données Tautulli = jamais vu
                                        episode_item.never_watched = True
                                        episode_item.view_count = 0
                                        episode_item.metadata["watch_source"] = "Tautulli (never watched)"
                            
                            episode_items.append(episode_item)
                    except Exception as e:
                        logger.warning(f"Error fetching episodes for series '{series_item.title}': {e}", exc_info=True)
                        # Continuer avec la série même si les épisodes échouent
        
        logger.info(f"Converted {len(sonarr_items)} Sonarr series and {len(episode_items)} episodes to MediaItems")

        # Unification des médias (plus besoin de Plex)
        self._emit_progress("matching_started", 60, "Matching et unification des médias...")
        logger.info("Matching and unifying media items across services...")
        unified_items = self.matcher.unify_media_items(
            [],  # Plus de Plex items
            radarr_items,
            sonarr_items,
            [],
            qb_torrents,
            qb_service
        )
        
        # Ajouter les épisodes individuels (pas unifiés, traités séparément)
        unified_items.extend(episode_items)
        logger.info(f"Unified {len(unified_items)} media items")
        self._emit_progress("matching_completed", 70, f"Unification terminée: {len(unified_items)} items")
        
        # Enrichir les épisodes avec qBittorrent aussi
        if qb_service and episode_items:
            logger.info(f"Enriching {len(episode_items)} episodes with qBittorrent data...")
            torrent_by_hash = {t["hash"]: t for t in qb_torrents if t.get("hash")}
            episode_matched_count = 0
            for idx, episode in enumerate(episode_items):
                primary_path = episode.get_primary_path()
                if primary_path:
                    qb_hashes = qb_service.find_torrents_for_path(primary_path, qb_torrents, media_title=episode.title)
                    if qb_hashes:
                        episode_matched_count += 1
                        if idx < 5:  # Log first 5 matches
                            logger.info(f"  ✓ Matched {len(qb_hashes)} torrent(s) for episode '{episode.title}'")
                        episode.qb_hashes.extend(qb_hashes)
                        # Stocker les noms des torrents dans metadata
                        torrent_names = []
                        for hash_val in qb_hashes:
                            torrent = torrent_by_hash.get(hash_val)
                            if torrent:
                                torrent_names.append({
                                    "hash": hash_val,
                                    "name": torrent.get("name", ""),
                                })
                        if torrent_names:
                            episode.metadata["qb_torrents"] = torrent_names
                    elif idx < 3:  # Log first 3 non-matches
                        logger.debug(f"  ✗ No torrents matched for episode '{episode.title}' (path: {primary_path[:60]}...)")
            logger.info(f"Episode qBittorrent enrichment completed: {episode_matched_count}/{len(episode_items)} episodes have torrents")

        # Enrichir avec Overseerr requests
        if overseerr_service:
            logger.info("Enriching with Overseerr requests...")
            for item in unified_items:
                overseerr_service.enrich_media_item(item, overseerr_requests)
            logger.info("Overseerr enrichment completed")

        # Évaluation des règles et garde-fous
        self._emit_progress("rules_evaluating", 75, "Évaluation des règles et garde-fous...")
        logger.info("Evaluating rules and safety checks...")
        candidates = []
        max_items = config.app.max_items_per_scan if config.app else None
        
        # Séparer les items par type pour traitement spécial
        series_items = [item for item in unified_items if item.type == "series"]
        episode_items_list = [item for item in unified_items if item.type == "episode"]
        
        # Pour les séries, on ne les inclut que si elles n'ont PAS d'épisodes candidats
        # (car on préfère supprimer les épisodes individuellement)
        series_with_episodes = set()
        for episode in episode_items_list:
            # Trouver la série parente de cet épisode
            episode_tvdb_id = episode.tvdb_id
            if episode_tvdb_id:
                for series in series_items:
                    if series.tvdb_id == episode_tvdb_id:
                        series_with_episodes.add(series.tvdb_id)
                        break
        
        logger.info(f"Found {len(episode_items_list)} episodes, {len(series_items)} series, {len(series_with_episodes)} series with episodes")
        
        for item in unified_items:
            # Limite max_items_per_scan si configuré
            if max_items and len(candidates) >= max_items:
                logger.info(f"Reached max_items_per_scan limit: {max_items}")
                break
            
            # Pour les séries, exclure celles qui ont des épisodes candidats
            if item.type == "series" and item.tvdb_id and item.tvdb_id in series_with_episodes:
                logger.debug("skipping_series_with_episodes", 
                           title=item.title,
                           tvdb_id=item.tvdb_id)
                continue
                
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
        logger.info(f"Found {len(candidates)} candidates for deletion (excluding series with episodes)")
        self._emit_progress("rules_evaluated", 80, f"Évaluation terminée: {len(candidates)} candidats")

        # Créer Plan en DB
        self._emit_progress("plan_creating", 85, "Création du plan en base de données...")
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
        invalid_types = []
        for item, rule in candidates:
            # Validation du type
            if item.type not in ["movie", "series", "episode"]:
                invalid_types.append(f"{item.title} (type: {item.type})")
                logger.warning(f"Invalid media type '{item.type}' for item '{item.title}', skipping")
                continue
            
            plan_item = PlanItem(
                plan_id=plan.id,
                selected=True,  # Par défaut sélectionné
                media_type=item.type,  # Validé ci-dessus
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
        
        if invalid_types:
            logger.error(f"Found {len(invalid_types)} items with invalid types: {', '.join(invalid_types[:5])}")

        db.commit()
        logger.info(f"Plan {plan.id} completed with {len(candidates)} items")
        self._emit_progress("plan_created", 100, f"Plan {plan.id} créé avec succès", {"plan_id": plan.id})
        return plan.id

