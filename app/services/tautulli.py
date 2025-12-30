"""Tautulli API client."""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config import get_config
from app.core.models import MediaItem


class TautulliService:
    """Service pour interagir avec Tautulli."""

    def __init__(self):
        config = get_config()
        if not config.tautulli:
            raise ValueError("Tautulli configuration not found")
        self.base_url = config.tautulli.url.rstrip("/")
        self.api_key = config.tautulli.api_key

    def _get_params(self) -> Dict[str, Any]:
        """Get base API parameters."""
        return {"apikey": self.api_key}

    async def get_history(self, rating_key: Optional[str] = None, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère l'historique de visionnage depuis Tautulli."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                params = self._get_params()
                params["cmd"] = "get_history"
                params["length"] = 10000  # Get a lot of history
                if rating_key:
                    params["rating_key"] = rating_key
                if user:
                    params["user"] = user

                response = await client.get(
                    f"{self.base_url}/api/v2",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", {}).get("data", {}).get("data", [])
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching history from Tautulli: {str(e)}")

    def get_history_sync(self, rating_key: Optional[str] = None, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère l'historique de visionnage depuis Tautulli (synchronous)."""
        with httpx.Client(timeout=60.0) as client:
            try:
                params = self._get_params()
                params["cmd"] = "get_history"
                params["length"] = 10000  # Get a lot of history
                if rating_key:
                    params["rating_key"] = rating_key
                if user:
                    params["user"] = user

                response = client.get(
                    f"{self.base_url}/api/v2",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", {}).get("data", {}).get("data", [])
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching history from Tautulli: {str(e)}")

    def get_watch_stats_for_rating_key(self, rating_key: str) -> Dict[str, Any]:
        """Récupère les statistiques de visionnage pour un rating_key spécifique."""
        history = self.get_history_sync(rating_key=rating_key)
        
        if not history:
            return {
                "view_count": 0,
                "last_viewed_at": None,
                "never_watched": True
            }
        
        # Trier par date (plus récent en premier)
        sorted_history = sorted(history, key=lambda x: x.get("date", 0), reverse=True)
        
        # Dernière date de visionnage
        last_viewed_timestamp = sorted_history[0].get("date", 0)
        last_viewed_at = None
        if last_viewed_timestamp:
            try:
                last_viewed_at = datetime.fromtimestamp(last_viewed_timestamp)
            except (ValueError, OSError):
                pass
        
        # Compter les vues (on considère qu'une session = 1 vue)
        view_count = len(history)
        
        return {
            "view_count": view_count,
            "last_viewed_at": last_viewed_at,
            "never_watched": view_count == 0
        }

    def enrich_media_item_with_watch_history(self, media_item: MediaItem) -> None:
        """Enrichit un MediaItem avec les données de visionnage de Tautulli."""
        if not media_item.plex_rating_key:
            return
        
        try:
            stats = self.get_watch_stats_for_rating_key(media_item.plex_rating_key)
            
            # Mettre à jour avec les données Tautulli (priorité sur Plex)
            if stats["last_viewed_at"]:
                # Garder la date la plus récente entre Plex et Tautulli
                if not media_item.last_viewed_at or stats["last_viewed_at"] > media_item.last_viewed_at:
                    media_item.last_viewed_at = stats["last_viewed_at"]
            
            # Utiliser le view_count de Tautulli s'il est supérieur (plus fiable)
            if stats["view_count"] > media_item.view_count:
                media_item.view_count = stats["view_count"]
            
            # Mettre à jour never_watched
            media_item.never_watched = stats["never_watched"]
            
        except Exception as e:
            # Si Tautulli échoue, on garde les données Plex
            pass

