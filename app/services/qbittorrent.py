"""qBittorrent API client."""
from qbittorrentapi import Client
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog

from app.config import get_config
from app.core.models import MediaItem
from app.core.torrent_matcher import TorrentMatcher

logger = structlog.get_logger(__name__)


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
        self._torrent_matcher = TorrentMatcher(debug=True)  # Enable debug for better matching

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
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            client = self._get_client()
            torrents = client.torrents_info()
            result = []
            logger.info(f"Fetching {len(torrents)} torrents from qBittorrent...")

            for idx, torrent in enumerate(torrents):
                # Récupérer les fichiers du torrent pour un matching plus précis
                torrent_files = []
                try:
                    files = client.torrents_files(torrent_hash=torrent.hash)
                    if files:
                        # Les fichiers peuvent être des dicts ou des objets
                        for f in files:
                            if isinstance(f, dict):
                                file_name = f.get("name", "") or str(f)
                            else:
                                file_name = getattr(f, "name", "") or str(f)
                            if file_name:
                                torrent_files.append(file_name)
                except Exception as e:
                    logger.debug(f"Could not get files for torrent {torrent.hash}: {e}")
                
                # Essayer d'obtenir content_path depuis différentes sources
                content_path = None
                if hasattr(torrent, "content_path") and torrent.content_path:
                    content_path = torrent.content_path
                elif hasattr(torrent, "save_path") and torrent.save_path and hasattr(torrent, "name") and torrent.name:
                    # Construire content_path depuis save_path + name
                    import os
                    content_path = os.path.join(torrent.save_path, torrent.name).replace("\\", "/")
                
                result.append({
                    "hash": torrent.hash,
                    "name": torrent.name,
                    "save_path": torrent.save_path,
                    "category": torrent.category or "",
                    "tags": torrent.tags.split(",") if torrent.tags else [],
                    "state": torrent.state,
                    "content_path": content_path,
                    "size": torrent.size,
                    "files": torrent_files,  # Liste des fichiers dans le torrent
                })
                
                if idx < 3:
                    logger.debug(f"Sample torrent {idx+1}: name='{torrent.name[:50]}', save_path='{torrent.save_path[:50] if torrent.save_path else 'N/A'}', files={len(torrent_files)}")

            total_files = sum(len(t.get("files", [])) for t in result)
            logger.info("torrents_retrieved", count=len(result), total_files=total_files)
            return result
        except Exception as e:
            logger.exception("error_fetching_torrents", error=str(e))
            raise Exception(f"Error fetching torrents from qBittorrent: {str(e)}")

    def find_torrents_for_path(self, media_path: str, all_torrents: Optional[List[Dict[str, Any]]] = None, media_title: Optional[str] = None) -> List[str]:
        """Trouve tous les torrents (cross-seed) qui pointent vers un chemin média.
        
        Utilise le nouveau matcher avancé avec stratégies multi-niveaux.
        
        Args:
            media_path: Chemin du média (peut être un fichier ou un dossier pour les séries)
            all_torrents: Liste de tous les torrents (optionnel, sera récupéré si None)
            media_title: Titre du média pour matching par nom (optionnel)
        """
        if all_torrents is None:
            all_torrents = self.get_torrents()

        if not media_path:
            return []

        # Utiliser le nouveau matcher
        matching_hashes = self._torrent_matcher.find_matching_torrents(
            media_path=media_path,
            all_torrents=all_torrents,
            media_title=media_title
        )

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

