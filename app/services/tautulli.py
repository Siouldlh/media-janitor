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

    def _extract_tvdb_id_from_guid(self, guid_str: str) -> Optional[int]:
        """Extrait le TVDb ID depuis un GUID string.
        
        Formats supportés:
        - "com.plexapp.agents.thetvdb://121361?lang=en" (série)
        - "com.plexapp.agents.thetvdb://121361/6/1?lang=en" (épisode)
        - "thetvdb://121361"
        """
        if not isinstance(guid_str, str) or "tvdb" not in guid_str.lower():
            return None
        
        try:
            # Format: "com.plexapp.agents.thetvdb://121361?lang=en" ou "com.plexapp.agents.thetvdb://121361/6/1?lang=en"
            # On veut extraire 121361 (le TVDb ID de la série)
            # Après "://", prendre la partie avant le premier "/" ou "?"
            if "://" in guid_str:
                after_protocol = guid_str.split("://")[-1]
                # Enlever les paramètres de query (?lang=en)
                after_protocol = after_protocol.split("?")[0]
                # Prendre la première partie avant "/" (saison/épisode)
                tvdb_id_str = after_protocol.split("/")[0]
                return int(tvdb_id_str)
            else:
                # Format alternatif: "thetvdb:121361"
                parts = guid_str.split(":")
                if len(parts) >= 2:
                    tvdb_id_str = parts[-1].split("/")[0].split("?")[0]
                    return int(tvdb_id_str)
        except (ValueError, IndexError, AttributeError) as e:
            logger.debug("tvdb_id_extraction_failed", guid=guid_str, error=str(e))
        
        return None

    def _extract_tvdb_id_from_entry(self, entry: Dict[str, Any], for_series: bool = False) -> Optional[int]:
        """Extrait le TVDb ID depuis une entrée d'historique Tautulli.
        
        Args:
            entry: Entrée d'historique Tautulli
            for_series: Si True, extrait depuis grandparent_guid (série), sinon depuis guid (épisode)
        """
        # Pour les séries, utiliser grandparent_guid qui contient le TVDb ID de la série
        if for_series:
            grandparent_guid = entry.get("grandparent_guid", "")
            if grandparent_guid:
                tvdb_id = self._extract_tvdb_id_from_guid(grandparent_guid)
                if tvdb_id:
                    return tvdb_id
        
        # Méthode 1: Extraire depuis "guids" (array)
        guids = entry.get("guids", [])
        if guids:
            for guid in guids:
                if isinstance(guid, str):
                    tvdb_id = self._extract_tvdb_id_from_guid(guid)
                    if tvdb_id:
                        return tvdb_id
                elif isinstance(guid, dict):
                    guid_id = guid.get("id", "")
                    if isinstance(guid_id, str):
                        tvdb_id = self._extract_tvdb_id_from_guid(guid_id)
                        if tvdb_id:
                            return tvdb_id
        
        # Méthode 2: Depuis "guid" (string unique) - pour épisodes, contient le GUID de l'épisode
        guid_str = entry.get("guid", "")
        if guid_str:
            tvdb_id = self._extract_tvdb_id_from_guid(guid_str)
            if tvdb_id:
                return tvdb_id
        
        # Méthode 3: Depuis "grandparent_guid" si disponible (pour séries)
        if not for_series:
            grandparent_guid = entry.get("grandparent_guid", "")
            if grandparent_guid:
                tvdb_id = self._extract_tvdb_id_from_guid(grandparent_guid)
                if tvdb_id:
                    return tvdb_id
        
        # Méthode 4: Fallback via get_metadata
        rating_key = entry.get("rating_key")
        if rating_key:
            try:
                metadata = self._get_metadata_sync(str(rating_key))
                if metadata:
                    # Pour les séries, chercher dans grandparent_guid
                    if for_series:
                        grandparent_guid = metadata.get("grandparent_guid", "")
                        if grandparent_guid:
                            tvdb_id = self._extract_tvdb_id_from_guid(grandparent_guid)
                            if tvdb_id:
                                return tvdb_id
                    
                    metadata_guids = metadata.get("guids", [])
                    for guid in metadata_guids:
                        if isinstance(guid, str):
                            tvdb_id = self._extract_tvdb_id_from_guid(guid)
                            if tvdb_id:
                                return tvdb_id
            except Exception as e:
                logger.debug("get_metadata_fallback_failed_tvdb", rating_key=rating_key, error=str(e))
        
        return None

    def _extract_tmdb_id_from_guid(self, guid_str: str) -> Optional[int]:
        """Extrait le TMDb ID depuis un GUID string.
        
        Formats supportés:
        - "com.plexapp.agents.themoviedb://12345?lang=en"
        - "tmdb://12345"
        - "tmdb:12345"
        """
        if not isinstance(guid_str, str) or "tmdb" not in guid_str.lower():
            return None
        
        try:
            # Format: "com.plexapp.agents.themoviedb://12345?lang=en" ou "tmdb://12345"
            if "://" in guid_str:
                after_protocol = guid_str.split("://")[-1]
                # Enlever les paramètres de query
                after_protocol = after_protocol.split("?")[0]
                # Prendre la première partie (pas de saison/épisode pour les films)
                tmdb_id_str = after_protocol.split("/")[0]
                return int(tmdb_id_str)
            else:
                # Format alternatif: "tmdb:12345"
                parts = guid_str.split(":")
                if len(parts) >= 2:
                    tmdb_id_str = parts[-1].split("/")[0].split("?")[0]
                    return int(tmdb_id_str)
        except (ValueError, IndexError, AttributeError) as e:
            logger.debug("tmdb_id_extraction_failed", guid=guid_str, error=str(e))
        
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
                if isinstance(guid, str):
                    tmdb_id = self._extract_tmdb_id_from_guid(guid)
                    if tmdb_id:
                        return tmdb_id
                elif isinstance(guid, dict):
                    guid_id = guid.get("id", "")
                    if isinstance(guid_id, str):
                        tmdb_id = self._extract_tmdb_id_from_guid(guid_id)
                        if tmdb_id:
                            return tmdb_id
        
        # Méthode 2: Extraire depuis "guid" (string unique, parfois présent)
        guid_str = entry.get("guid", "")
        if guid_str:
            tmdb_id = self._extract_tmdb_id_from_guid(guid_str)
            if tmdb_id:
                return tmdb_id
        
        # Méthode 3: Fallback via get_metadata avec rating_key
        rating_key = entry.get("rating_key")
        if rating_key:
            try:
                metadata = self._get_metadata_sync(str(rating_key))
                if metadata:
                    metadata_guids = metadata.get("guids", [])
                    for guid in metadata_guids:
                        if isinstance(guid, str):
                            tmdb_id = self._extract_tmdb_id_from_guid(guid)
                            if tmdb_id:
                                return tmdb_id
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
            
            # Date de visionnage - gérer timestamps Unix et ISO strings
            date_value = entry.get("date")
            last_watched_at = None
            if date_value:
                try:
                    # Si c'est un timestamp Unix (int ou float)
                    if isinstance(date_value, (int, float)):
                        last_watched_at = datetime.fromtimestamp(date_value)
                    # Si c'est une chaîne ISO
                    elif isinstance(date_value, str):
                        # Essayer d'abord le format ISO
                        try:
                            last_watched_at = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                        except ValueError:
                            # Fallback: essayer de parser comme timestamp string
                            try:
                                last_watched_at = datetime.fromtimestamp(float(date_value))
                            except (ValueError, OSError):
                                pass
                except (ValueError, OSError, TypeError) as e:
                    logger.debug("date_parsing_failed", date_value=date_value, error=str(e))
            
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
            
            # Pour les épisodes, extraire le TVDb ID depuis guid (contient le GUID de l'épisode)
            # Le TVDb ID de la série est dans grandparent_guid, mais pour les épisodes individuels
            # on peut aussi l'extraire depuis guid car le format est "thetvdb://SERIES_ID/SEASON/EPISODE"
            tvdb_id = self._extract_tvdb_id_from_entry(entry, for_series=False)
            
            if not tvdb_id:
                # Fallback: essayer depuis grandparent_guid
                tvdb_id = self._extract_tvdb_id_from_entry(entry, for_series=True)
            
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
        
        Cette méthode construit la map directement depuis l'historique en utilisant grandparent_guid
        pour obtenir le TVDb ID de la série, ce qui est plus fiable que de reconstruire depuis les épisodes.
        
        Returns:
            Dict avec clé = tvdb_id (int), valeur = {
                "last_watched_at": datetime,
                "view_count": int (total épisodes vus),
                "last_user": Optional[str],
                "never_watched": bool
            }
        """
        logger.info("fetching_series_watch_map")
        history = self.get_history_sync()
        
        series_map: Dict[int, Dict[str, Any]] = {}
        skipped_no_tvdb = 0
        
        for entry in history:
            media_type = entry.get("media_type", "").lower()
            # Pour les séries, on s'intéresse aux épisodes (media_type="episode")
            if media_type != "episode":
                continue
            
            # Extraire TVDb ID de la série depuis grandparent_guid
            tvdb_id = self._extract_tvdb_id_from_entry(entry, for_series=True)
            
            if not tvdb_id:
                skipped_no_tvdb += 1
                if skipped_no_tvdb <= 5:
                    logger.debug("series_entry_no_tvdb",
                               title=entry.get("grandparent_title", "unknown"),
                               rating_key=entry.get("rating_key"),
                               guid=entry.get("guid"),
                               grandparent_guid=entry.get("grandparent_guid"))
                continue
            
            # Date de visionnage
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
                    logger.debug("date_parsing_failed_series", date_value=date_value, error=str(e))
            
            # User
            last_user = entry.get("user", None)
            
            # Si on a déjà une entrée pour cette série, accumuler les stats
            if tvdb_id in series_map:
                # Accumuler le view_count (chaque épisode vu = +1)
                series_map[tvdb_id]["view_count"] += 1
                
                # Garder la date la plus récente
                if last_watched_at:
                    existing_date = series_map[tvdb_id]["last_watched_at"]
                    if not existing_date or last_watched_at > existing_date:
                        series_map[tvdb_id]["last_watched_at"] = last_watched_at
                        series_map[tvdb_id]["last_user"] = last_user
            else:
                # Première entrée pour cette série
                series_map[tvdb_id] = {
                    "last_watched_at": last_watched_at,
                    "view_count": 1,
                    "last_user": last_user,
                    "never_watched": False
                }
        
        logger.info("series_watch_map_fetched",
                   count=len(series_map),
                   skipped_no_tvdb=skipped_no_tvdb,
                   total_history=len(history))
        return series_map

    def enrich_media_item_with_watch_history(self, media_item: MediaItem) -> None:
        """Enrichit un MediaItem avec les données de visionnage de Tautulli.
        
        Cette méthode est utilisée pour enrichir un MediaItem existant.
        Pour un scan complet, utiliser get_movie_watch_map() et get_episode_watch_map().
        """
        # Cette méthode est conservée pour compatibilité mais n'est plus utilisée
        # dans le nouveau flux basé sur Radarr/Sonarr + Tautulli maps
        pass
