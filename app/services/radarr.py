"""Radarr API client."""
import httpx
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import get_config
from app.core.models import MediaItem


class RadarrService:
    """Service pour interagir avec Radarr."""

    def __init__(self):
        config = get_config()
        if not config.radarr:
            raise ValueError("Radarr configuration not found")
        self.base_url = config.radarr.url.rstrip("/")
        self.api_key = config.radarr.api_key
        self.protected_tags = config.radarr.protected_tags
        self.delete_method = config.radarr.delete_method
        self._tag_cache: Dict[int, str] = {}  # Cache pour mapper tag ID -> label

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {"X-Api-Key": self.api_key}

    async def _get_tag_labels(self) -> Dict[int, str]:
        """Récupère les labels des tags depuis Radarr."""
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
        """Récupère les labels des tags depuis Radarr (synchronous)."""
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

    async def get_movies(self) -> List[Dict[str, Any]]:
        """Récupère tous les films depuis Radarr."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v3/movie",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching movies from Radarr: {str(e)}")

    def get_movies_sync(self) -> List[Dict[str, Any]]:
        """Récupère tous les films depuis Radarr (synchronous)."""
        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.get(
                    f"{self.base_url}/api/v3/movie",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching movies from Radarr: {str(e)}")

    async def delete_movie(self, movie_id: int, delete_files: bool = True) -> bool:
        """Supprime un film via l'API Radarr."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                params = {
                    "deleteFiles": delete_files,
                    "addImportExclusion": False,
                }
                response = await client.delete(
                    f"{self.base_url}/api/v3/movie/{movie_id}",
                    headers=self._get_headers(),
                    params=params,
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                raise Exception(f"Error deleting movie from Radarr: {str(e)}")

    def enrich_media_item(self, media_item: MediaItem, radarr_movie: Dict[str, Any]) -> None:
        """Enrichit un MediaItem avec les données Radarr."""
        media_item.radarr_path = radarr_movie.get("path")
        media_item.tmdb_id = radarr_movie.get("tmdbId")
        media_item.monitored = radarr_movie.get("monitored", True)
        if radarr_movie.get("tags"):
            # Les tags sont des IDs (entiers), on doit récupérer les labels
            tag_ids = radarr_movie.get("tags", [])
            tag_labels_map = self._get_tag_labels_sync()
            # Convertir les IDs en labels, ou garder l'ID si le label n'est pas trouvé
            media_item.tags = [
                tag_labels_map.get(tag_id, str(tag_id)) 
                if isinstance(tag_id, int) 
                else (tag_id.get("label", "") if isinstance(tag_id, dict) else str(tag_id))
                for tag_id in tag_ids
            ]
        # Size on disk depuis Radarr (prioritaire)
        if radarr_movie.get("sizeOnDisk"):
            media_item.size_bytes = radarr_movie.get("sizeOnDisk", 0)
        # Fallback: calculer depuis statistics si disponible
        elif radarr_movie.get("statistics") and radarr_movie["statistics"].get("sizeOnDisk"):
            media_item.size_bytes = radarr_movie["statistics"]["sizeOnDisk"]
        media_item.metadata["radarr_id"] = radarr_movie.get("id")
        media_item.metadata["radarr_title"] = radarr_movie.get("title")
        media_item.metadata["radarr_added"] = radarr_movie.get("added")  # Date d'ajout pour never_watched

