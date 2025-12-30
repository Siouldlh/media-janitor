"""Overseerr API client."""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.config import get_config
from app.core.models import MediaItem


class OverseerrService:
    """Service pour interagir avec Overseerr."""

    def __init__(self):
        config = get_config()
        if not config.overseerr:
            raise ValueError("Overseerr configuration not found")
        self.base_url = config.overseerr.url.rstrip("/")
        self.api_key = config.overseerr.api_key
        self.protect_if_request_active = config.overseerr.protect_if_request_active
        self.protect_if_request_younger_than_days = config.overseerr.protect_if_request_younger_than_days
        self.requested_by_must_have_watched = config.overseerr.requested_by_must_have_watched

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {"X-Api-Key": self.api_key}

    async def get_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère les demandes depuis Overseerr."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {}
                if status:
                    params["filter"] = status
                params["take"] = 1000  # Get all requests
                params["skip"] = 0

                response = await client.get(
                    f"{self.base_url}/api/v1/request",
                    headers=self._get_headers(),
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching requests from Overseerr: {str(e)}")

    def get_requests_sync(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère les demandes depuis Overseerr (synchronous)."""
        with httpx.Client(timeout=30.0) as client:
            try:
                params = {}
                if status:
                    params["filter"] = status
                params["take"] = 1000
                params["skip"] = 0

                response = client.get(
                    f"{self.base_url}/api/v1/request",
                    headers=self._get_headers(),
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching requests from Overseerr: {str(e)}")

    def enrich_media_item(self, media_item: MediaItem, overseerr_requests: List[Dict[str, Any]]) -> None:
        """Enrichit un MediaItem avec les données Overseerr."""
        # Find matching request
        for request in overseerr_requests:
            media_type = request.get("type")
            media_id = None

            if media_type == "movie":
                media_id = request.get("media", {}).get("tmdbId")
                if media_item.tmdb_id and media_id == media_item.tmdb_id:
                    self._apply_request_to_item(media_item, request)
            elif media_type == "tv":
                tvdb_id = request.get("media", {}).get("tvdbId")
                tmdb_id = request.get("media", {}).get("tmdbId")
                if (media_item.tvdb_id and tvdb_id == media_item.tvdb_id) or \
                   (media_item.tmdb_id and tmdb_id == media_item.tmdb_id):
                    self._apply_request_to_item(media_item, request)

    def _apply_request_to_item(self, media_item: MediaItem, request: Dict[str, Any]) -> None:
        """Applique les données d'une request Overseerr à un MediaItem."""
        media_item.overseerr_request_id = request.get("id")
        # Convert status to string before calling lower() (status might be int or string)
        status = request.get("status", "")
        media_item.overseerr_status = str(status).lower() if status else ""
        media_item.overseerr_requested_by = request.get("requestedBy", {}).get("username") if request.get("requestedBy") else None

        # Parse requested date
        if request.get("createdAt"):
            try:
                media_item.overseerr_requested_at = datetime.fromisoformat(
                    request.get("createdAt").replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

    def is_protected(self, media_item: MediaItem) -> tuple[bool, Optional[str]]:
        """Vérifie si un média est protégé par Overseerr."""
        if not media_item.overseerr_status:
            return False, None

        # Si protect_if_request_active, protéger si status est pending/approved
        if self.protect_if_request_active:
            if media_item.overseerr_status in ["pending", "approved"]:
                return True, f"Overseerr request {media_item.overseerr_status}"

        # Vérifier l'âge de la demande
        if media_item.overseerr_requested_at:
            age_days = (datetime.now(media_item.overseerr_requested_at.tzinfo) - media_item.overseerr_requested_at).days
            if age_days < self.protect_if_request_younger_than_days:
                return True, f"Overseerr request recent ({age_days} days old)"

        return False, None

