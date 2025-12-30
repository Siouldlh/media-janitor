"""qBittorrent API client."""
from qbittorrentapi import Client
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import get_config
from app.core.models import MediaItem


class QBittorrentService:
    """Service pour interagir avec qBittorrent."""

    def __init__(self):
        config = get_config()
        if not config.qbittorrent:
            raise ValueError("qBittorrent configuration not found")
        self.base_url = config.qbittorrent.url.rstrip("/")
        self.username = config.qbittorrent.username
        self.password = config.qbittorrent.password
        self.protect_categories = config.qbittorrent.protect_categories
        self.match_mode = config.qbittorrent.match_mode
        self._client: Optional[Client] = None

    def _get_client(self) -> Client:
        """Get or create qBittorrent client."""
        if self._client is None:
            self._client = Client(
                host=self.base_url,
                username=self.username,
                password=self.password,
            )
            try:
                self._client.auth_log_in()
            except Exception as e:
                raise Exception(f"Error connecting to qBittorrent: {str(e)}")
        return self._client

    def get_torrents(self) -> List[Dict[str, Any]]:
        """Récupère tous les torrents depuis qBittorrent."""
        try:
            client = self._get_client()
            torrents = client.torrents_info()
            result = []

            for torrent in torrents:
                result.append({
                    "hash": torrent.hash,
                    "name": torrent.name,
                    "save_path": torrent.save_path,
                    "category": torrent.category or "",
                    "tags": torrent.tags.split(",") if torrent.tags else [],
                    "state": torrent.state,
                    "content_path": torrent.content_path if hasattr(torrent, "content_path") else None,
                    "size": torrent.size,
                })

            return result
        except Exception as e:
            raise Exception(f"Error fetching torrents from qBittorrent: {str(e)}")

    def find_torrents_for_path(self, media_path: str, all_torrents: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Trouve tous les torrents (cross-seed) qui pointent vers un chemin média."""
        if all_torrents is None:
            all_torrents = self.get_torrents()

        media_path_obj = Path(media_path).resolve()
        matching_hashes = []

        for torrent in all_torrents:
            save_path = Path(torrent["save_path"]).resolve()
            content_path = Path(torrent["content_path"]).resolve() if torrent.get("content_path") else None

            # Check if media_path is within save_path or matches content_path
            try:
                if self.match_mode == "path":
                    # Match by directory path
                    if content_path:
                        if media_path_obj == content_path or media_path_obj in content_path.parents or content_path in media_path_obj.parents:
                            matching_hashes.append(torrent["hash"])
                    else:
                        # Fallback: check if media_path is in save_path
                        if media_path_obj == save_path or media_path_obj in save_path.parents or save_path in media_path_obj.parents:
                            matching_hashes.append(torrent["hash"])
            except (OSError, ValueError):
                # Path resolution failed, skip
                pass

        return matching_hashes

    async def delete_torrents(self, hashes: List[str], delete_files: bool = True) -> bool:
        """Supprime des torrents (avec ou sans fichiers)."""
        try:
            client = self._get_client()
            if delete_files:
                client.torrents_delete(delete_files=True, torrent_hashes=hashes)
            else:
                client.torrents_delete(delete_files=False, torrent_hashes=hashes)
            return True
        except Exception as e:
            raise Exception(f"Error deleting torrents from qBittorrent: {str(e)}")

    def is_protected_category(self, category: str) -> bool:
        """Vérifie si une catégorie est protégée."""
        return category in self.protect_categories

