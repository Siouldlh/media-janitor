"""Tautulli API client - Source de vérité pour watch history."""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import structlog

from app.config import get_config
from app.core.models import MediaItem
from app.utils.http_client import get_http_client

logger = structlog.get_logger(__name__)


class TautulliService:
    """Service pour interagir avec Tautulli - Source de vérité pour watch history."""

    def __init__(self):
        config = get_config()
        if not config.tautulli or not config.tautulli.enabled:
            raise ValueError("Tautulli configuration not found or disabled")
        self.base_url = config.tautulli.url.rstrip("/")
        self.api_key = config.tautulli.api_key

    def _get_params(self) -> Dict[str, Any]:
        """Get base API parameters."""
        return {"apikey": self.api_key}

    async def get_history(self, rating_key: Optional[str] = None, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère l'historique de visionnage depuis Tautulli."""
        http_client = get_http_client()
        params = self._get_params()
        params["cmd"] = "get_history"
        params["length"] = 10000  # Get a lot of history
        if rating_key:
            params["rating_key"] = rating_key
        if user:
            params["user"] = user

        response = await http_client.get_async(
            f"{self.base_url}/api/v2",
            service_name="tautulli",
            params=params,
            timeout=60.0
        )
        data = response.json()
        return data.get("response", {}).get("data", {}).get("data", [])

    def get_history_sync(self, rating_key: Optional[str] = None, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère l'historique de visionnage depuis Tautulli (synchronous)."""
        http_client = get_http_client()
        params = self._get_params()
        params["cmd"] = "get_history"
        params["length"] = 10000  # Get a lot of history
        if rating_key:
            params["rating_key"] = rating_key
        if user:
            params["user"] = user

        response = http_client.get_sync(
            f"{self.base_url}/api/v2",
            service_name="tautulli",
            params=params,
            timeout=60.0
        )
        data = response.json()
        
        # Tautulli API structure peut varier selon la version
        # Format 1: response.data.data (array)
        # Format 2: response.data (array directement)
        # Format 3: response.data.data (dict avec clé "data")
        response_obj = data.get("response", {})
        result = response_obj.get("data", {})
        
        # Si result est directement une liste, la retourner
        if isinstance(result, list):
            logger.info("get_history_format", format="direct_list", count=len(result))
            return result
        
        # Si result est un dict, chercher la clé "data"
        if isinstance(result, dict):
            history_data = result.get("data", [])
            if isinstance(history_data, list):
                logger.info("get_history_format", format="nested_dict", count=len(history_data))
                return history_data
            # Si "data" n'existe pas, peut-être que result contient directement les entrées
            # Vérifier si result a des clés qui ressemblent à des entrées d'historique
            if result:
                logger.warning("get_history_unexpected_format", keys=list(result.keys())[:5])
        
        logger.warning("get_history_no_data", response_structure=str(type(result)))
        return []

    def _extract_tvdb_id_from_entry(self, entry: Dict[str, Any]) -> Optional[int]:
        """Extrait le TVDb ID depuis une entrée d'historique Tautulli."""
        # Méthode 1: Extraire depuis "guids" (array)
        guids = entry.get("guids", [])
        if guids:
            for guid in guids:
                if isinstance(guid, str) and "tvdb" in guid.lower():
                    try:
                        tvdb_id = int(guid.split(":")[-1].split("/")[-1])
                        return tvdb_id
                    except (ValueError, IndexError):
                        continue
                elif isinstance(guid, dict):
                    guid_id = guid.get("id", "")
                    if isinstance(guid_id, str) and "tvdb" in guid_id.lower():
                        try:
                            tvdb_id = int(guid_id.split(":")[-1].split("/")[-1])
                            return tvdb_id
                        except (ValueError, IndexError):
                            continue
        
        # Méthode 2: Depuis "guid" (string unique)
        guid_str = entry.get("guid", "")
        if isinstance(guid_str, str) and "tvdb" in guid_str.lower():
            try:
                tvdb_id = int(guid_str.split(":")[-1].split("/")[-1])
                return tvdb_id
            except (ValueError, IndexError):
                pass
        
        # Méthode 3: Fallback via get_metadata
        rating_key = entry.get("rating_key")
        if rating_key:
            try:
                metadata = self._get_metadata_sync(str(rating_key))
                if metadata:
                    metadata_guids = metadata.get("guids", [])
                    for guid in metadata_guids:
                        if isinstance(guid, str) and "tvdb" in guid.lower():
                            try:
                                tvdb_id = int(guid.split(":")[-1].split("/")[-1])
                                return tvdb_id
                            except (ValueError, IndexError):
                                continue
            except Exception as e:
                logger.debug("get_metadata_fallback_failed_tvdb", rating_key=rating_key, error=str(e))
        
        return None

    def _extract_tmdb_id_from_entry(self, entry: Dict[str, Any]) -> Optional[int]:
        """Extrait le TMDb ID depuis une entrée d'historique Tautulli.
        
        Essaie plusieurs méthodes :
        1. Depuis le champ "guids" (array de strings ou dicts)
        2. Depuis le champ "guid" (string unique)
        3. Depuis "rating_key" via get_metadata (fallback)
        """
        # Méthode 1: Extraire depuis "guids" (array)
        guids = entry.get("guids", [])
        if guids:
            for guid in guids:
                # Format string: "tmdb://12345" ou "tmdb:12345"
                if isinstance(guid, str) and "tmdb" in guid.lower():
                    try:
                        # Format: "tmdb://12345" ou "tmdb:12345"
                        tmdb_id = int(guid.split(":")[-1].split("/")[-1])
                        return tmdb_id
                    except (ValueError, IndexError):
                        continue
                # Format dict: {"id": "tmdb://12345", "source": "tmdb"}
                elif isinstance(guid, dict):
                    guid_id = guid.get("id", "")
                    if isinstance(guid_id, str) and "tmdb" in guid_id.lower():
                        try:
                            tmdb_id = int(guid_id.split(":")[-1].split("/")[-1])
                            return tmdb_id
                        except (ValueError, IndexError):
                            continue
        
        # Méthode 2: Extraire depuis "guid" (string unique, parfois présent)
        guid_str = entry.get("guid", "")
        if isinstance(guid_str, str) and "tmdb" in guid_str.lower():
            try:
                tmdb_id = int(guid_str.split(":")[-1].split("/")[-1])
                return tmdb_id
            except (ValueError, IndexError):
                pass
        
        # Méthode 3: Fallback via get_metadata avec rating_key
        rating_key = entry.get("rating_key")
        if rating_key:
            try:
                metadata = self._get_metadata_sync(str(rating_key))
                if metadata:
                    # Les GUIDs dans metadata peuvent être dans un format différent
                    metadata_guids = metadata.get("guids", [])
                    for guid in metadata_guids:
                        if isinstance(guid, str) and "tmdb" in guid.lower():
                            try:
                                tmdb_id = int(guid.split(":")[-1].split("/")[-1])
                                return tmdb_id
                            except (ValueError, IndexError):
                                continue
            except Exception as e:
                logger.debug("get_metadata_fallback_failed", rating_key=rating_key, error=str(e))
        
        return None

    def _get_metadata_sync(self, rating_key: str) -> Optional[Dict[str, Any]]:
        """Récupère les métadonnées d'un média via rating_key (synchronous)."""
        try:
            http_client = get_http_client()
            params = self._get_params()
            params["cmd"] = "get_metadata"
            params["rating_key"] = rating_key

            response = http_client.get_sync(
                f"{self.base_url}/api/v2",
                service_name="tautulli",
                params=params,
                timeout=30.0
            )
            data = response.json()
            response_obj = data.get("response", {})
            return response_obj.get("data", {})
        except Exception as e:
            logger.debug("get_metadata_error", rating_key=rating_key, error=str(e))
            return None

    def get_movie_watch_map(self) -> Dict[int, Dict[str, Any]]:
        """Récupère un mapping TMDb ID → watch stats pour tous les films.
        
        Returns:
            Dict avec clé = tmdb_id (int), valeur = {
                "last_watched_at": datetime,
                "view_count": int,
                "last_user": Optional[str],
                "never_watched": bool
            }
        """
        logger.info("fetching_movie_watch_map")
        history = self.get_history_sync()
        logger.info("history_retrieved", count=len(history))
        
        watch_map: Dict[int, Dict[str, Any]] = {}
        skipped_no_tmdb = 0
        
        for entry in history:
            media_type = entry.get("media_type", "").lower()
            # Tautulli peut retourner "movie" ou "film" selon la version
            if media_type not in ["movie", "film"]:
                continue
            
            # Extraire TMDb ID avec la nouvelle méthode robuste
            tmdb_id = self._extract_tmdb_id_from_entry(entry)
            
            if not tmdb_id:
                skipped_no_tmdb += 1
                # Log seulement les premiers pour éviter le spam
                if skipped_no_tmdb <= 5:
                    logger.debug("movie_entry_no_tmdb", 
                               title=entry.get("title", "unknown"),
                               rating_key=entry.get("rating_key"),
                               guids=entry.get("guids", []))
                continue
            
            # Date de visionnage
            date_timestamp = entry.get("date", 0)
            last_watched_at = None
            if date_timestamp:
                try:
                    last_watched_at = datetime.fromtimestamp(date_timestamp)
                except (ValueError, OSError):
                    pass
            
            # User
            last_user = entry.get("user", None)
            
            # Si on a déjà une entrée pour ce TMDb ID, garder la plus récente
            if tmdb_id in watch_map:
                existing_date = watch_map[tmdb_id].get("last_watched_at")
                if existing_date and last_watched_at:
                    if last_watched_at > existing_date:
                        watch_map[tmdb_id] = {
                            "last_watched_at": last_watched_at,
                            "view_count": watch_map[tmdb_id].get("view_count", 0) + 1,
                            "last_user": last_user,
                            "never_watched": False
                        }
                    else:
                        watch_map[tmdb_id]["view_count"] = watch_map[tmdb_id].get("view_count", 0) + 1
                elif last_watched_at:
                    watch_map[tmdb_id] = {
                        "last_watched_at": last_watched_at,
                        "view_count": watch_map[tmdb_id].get("view_count", 0) + 1,
                        "last_user": last_user,
                        "never_watched": False
                    }
            else:
                watch_map[tmdb_id] = {
                    "last_watched_at": last_watched_at,
                    "view_count": 1,
                    "last_user": last_user,
                    "never_watched": False
                }
        
        logger.info("movie_watch_map_fetched", 
                   count=len(watch_map), 
                   skipped_no_tmdb=skipped_no_tmdb,
                   total_history=len(history))
        return watch_map

    def get_episode_watch_map(self) -> Dict[Tuple[int, int, int], Dict[str, Any]]:
        """Récupère un mapping (TVDb ID, season, episode) → watch stats pour tous les épisodes.
        
        Returns:
            Dict avec clé = (tvdb_id, season, episode), valeur = {
                "last_watched_at": datetime,
                "view_count": int,
                "last_user": Optional[str],
                "never_watched": bool
            }
        """
        logger.info("fetching_episode_watch_map")
        history = self.get_history_sync()
        
        watch_map: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
        
        for entry in history:
            media_type = entry.get("media_type", "").lower()
            if media_type not in ["episode", "show"]:
                continue
            
            # Extraire TVDb ID avec la même logique robuste
            tvdb_id = self._extract_tvdb_id_from_entry(entry)
            
            if not tvdb_id:
                continue
            
            # Season et episode
            season_num = entry.get("season_num")
            episode_num = entry.get("episode_num")
            
            if season_num is None or episode_num is None:
                continue
            
            try:
                season_num = int(season_num)
                episode_num = int(episode_num)
            except (ValueError, TypeError):
                continue
            
            key = (tvdb_id, season_num, episode_num)
            
            # Date de visionnage - gérer timestamps Unix et ISO strings
            date_value = entry.get("date")
            last_watched_at = None
            if date_value:
                try:
                    if isinstance(date_value, (int, float)):
                        last_watched_at = datetime.fromtimestamp(date_value)
                    elif isinstance(date_value, str):
                        try:
                            last_watched_at = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                        except ValueError:
                            try:
                                last_watched_at = datetime.fromtimestamp(float(date_value))
                            except (ValueError, OSError):
                                pass
                except (ValueError, OSError, TypeError) as e:
                    logger.debug("date_parsing_failed_episode", date_value=date_value, error=str(e))
            
            # User
            last_user = entry.get("user", None)
            
            # Si on a déjà une entrée, garder la plus récente
            if key in watch_map:
                existing_date = watch_map[key].get("last_watched_at")
                if existing_date and last_watched_at:
                    if last_watched_at > existing_date:
                        watch_map[key] = {
                            "last_watched_at": last_watched_at,
                            "view_count": watch_map[key].get("view_count", 0) + 1,
                            "last_user": last_user,
                            "never_watched": False
                        }
                    else:
                        watch_map[key]["view_count"] = watch_map[key].get("view_count", 0) + 1
                elif last_watched_at:
                    watch_map[key] = {
                        "last_watched_at": last_watched_at,
                        "view_count": watch_map[key].get("view_count", 0) + 1,
                        "last_user": last_user,
                        "never_watched": False
                    }
            else:
                watch_map[key] = {
                    "last_watched_at": last_watched_at,
                    "view_count": 1,
                    "last_user": last_user,
                    "never_watched": False
                }
        
        logger.info("episode_watch_map_fetched", count=len(watch_map))
        return watch_map

    def get_series_watch_map(self) -> Dict[int, Dict[str, Any]]:
        """Récupère un mapping TVDb ID → watch stats pour les séries (dernier épisode vu).
        
        Returns:
            Dict avec clé = tvdb_id (int), valeur = {
                "last_watched_at": datetime,
                "view_count": int (total épisodes vus),
                "last_user": Optional[str],
                "never_watched": bool
            }
        """
        logger.info("fetching_series_watch_map")
        episode_map = self.get_episode_watch_map()
        
        series_map: Dict[int, Dict[str, Any]] = {}
        
        for (tvdb_id, season, episode), stats in episode_map.items():
            if tvdb_id not in series_map:
                series_map[tvdb_id] = {
                    "last_watched_at": stats["last_watched_at"],
                    "view_count": 0,
                    "last_user": stats.get("last_user"),
                    "never_watched": False
                }
            
            # Accumuler le view_count
            series_map[tvdb_id]["view_count"] += stats["view_count"]
            
            # Garder la date la plus récente
            if stats["last_watched_at"]:
                existing_date = series_map[tvdb_id]["last_watched_at"]
                if not existing_date or stats["last_watched_at"] > existing_date:
                    series_map[tvdb_id]["last_watched_at"] = stats["last_watched_at"]
                    series_map[tvdb_id]["last_user"] = stats.get("last_user")
        
        logger.info("series_watch_map_fetched", count=len(series_map))
        return series_map

    def enrich_media_item_with_watch_history(self, media_item: MediaItem) -> None:
        """Enrichit un MediaItem avec les données de visionnage de Tautulli.
        
        Cette méthode est utilisée pour enrichir un MediaItem existant.
        Pour un scan complet, utiliser get_movie_watch_map() et get_episode_watch_map().
        """
        # Cette méthode est conservée pour compatibilité mais n'est plus utilisée
        # dans le nouveau flux basé sur Radarr/Sonarr + Tautulli maps
        pass
