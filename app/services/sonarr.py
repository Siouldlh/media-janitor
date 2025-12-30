"""Sonarr API client."""
import httpx
from typing import List, Dict, Any, Optional

from app.config import get_config
from app.core.models import MediaItem


class SonarrService:
    """Service pour interagir avec Sonarr."""

    def __init__(self):
        config = get_config()
        if not config.sonarr:
            raise ValueError("Sonarr configuration not found")
        self.base_url = config.sonarr.url.rstrip("/")
        self.api_key = config.sonarr.api_key
        self.protected_tags = config.sonarr.protected_tags
        self._tag_cache: Dict[int, str] = {}  # Cache pour mapper tag ID -> label

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {"X-Api-Key": self.api_key}

    async def _get_tag_labels(self) -> Dict[int, str]:
        """Récupère les labels des tags depuis Sonarr."""
        if self._tag_cache:
            return self._tag_cache
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v3/tag",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                tags = response.json()
                self._tag_cache = {tag.get("id"): tag.get("label", "") for tag in tags}
                return self._tag_cache
            except httpx.HTTPError as e:
                # Si on ne peut pas récupérer les tags, retourner un cache vide
                return {}

    def _get_tag_labels_sync(self) -> Dict[int, str]:
        """Récupère les labels des tags depuis Sonarr (synchronous)."""
        if self._tag_cache:
            return self._tag_cache
        
        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.get(
                    f"{self.base_url}/api/v3/tag",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                tags = response.json()
                self._tag_cache = {tag.get("id"): tag.get("label", "") for tag in tags}
                return self._tag_cache
            except httpx.HTTPError as e:
                # Si on ne peut pas récupérer les tags, retourner un cache vide
                return {}

    async def get_series(self) -> List[Dict[str, Any]]:
        """Récupère toutes les séries depuis Sonarr."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v3/series",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching series from Sonarr: {str(e)}")

    def get_series_sync(self) -> List[Dict[str, Any]]:
        """Récupère toutes les séries depuis Sonarr (synchronous)."""
        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.get(
                    f"{self.base_url}/api/v3/series",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching series from Sonarr: {str(e)}")

    async def get_episodes(self, series_id: int) -> List[Dict[str, Any]]:
        """Récupère les épisodes d'une série."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v3/episode",
                    headers=self._get_headers(),
                    params={"seriesId": series_id},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching episodes from Sonarr: {str(e)}")

    async def delete_series(self, series_id: int, delete_files: bool = True) -> bool:
        """Supprime une série via l'API Sonarr."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                params = {
                    "deleteFiles": delete_files,
                    "addImportExclusion": False,
                }
                response = await client.delete(
                    f"{self.base_url}/api/v3/series/{series_id}",
                    headers=self._get_headers(),
                    params=params,
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                raise Exception(f"Error deleting series from Sonarr: {str(e)}")

    def enrich_media_item(self, media_item: MediaItem, sonarr_series: Dict[str, Any]) -> None:
        """Enrichit un MediaItem avec les données Sonarr."""
        media_item.sonarr_path = sonarr_series.get("path")
        media_item.tvdb_id = sonarr_series.get("tvdbId")
        media_item.tmdb_id = sonarr_series.get("tmdbId")
        media_item.monitored = sonarr_series.get("monitored", True)
        if sonarr_series.get("tags"):
            # Les tags sont des IDs (entiers), on doit récupérer les labels
            tag_ids = sonarr_series.get("tags", [])
            tag_labels_map = self._get_tag_labels_sync()
            # Convertir les IDs en labels, ou garder l'ID si le label n'est pas trouvé
            media_item.tags = [
                tag_labels_map.get(tag_id, str(tag_id)) 
                if isinstance(tag_id, int) 
                else (tag_id.get("label", "") if isinstance(tag_id, dict) else str(tag_id))
                for tag_id in tag_ids
            ]
        # Size on disk depuis Sonarr statistics
        if sonarr_series.get("statistics"):
            stats = sonarr_series.get("statistics", {})
            media_item.size_bytes = stats.get("sizeOnDisk", 0)
        media_item.metadata["sonarr_id"] = sonarr_series.get("id")
        media_item.metadata["sonarr_title"] = sonarr_series.get("title")
        media_item.metadata["sonarr_added"] = sonarr_series.get("added")  # Date d'ajout pour never_watched

