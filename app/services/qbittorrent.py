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
        """Trouve tous les torrents (cross-seed) qui pointent vers un chemin média.
        
        Optimisé pour éviter Path.resolve() qui est très lent sur les chemins réseau.
        """
        if all_torrents is None:
            all_torrents = self.get_torrents()

        if not media_path:
            return []

        # Normaliser le chemin média sans resolve (évite les appels réseau)
        # Utiliser os.path.normpath pour normaliser les séparateurs
        import os
        media_path_normalized = os.path.normpath(media_path).replace("\\", "/").rstrip("/")
        matching_hashes = []

        for torrent in all_torrents:
            # Normaliser les chemins du torrent
            save_path = torrent.get("save_path", "")
            if save_path:
                save_path_normalized = os.path.normpath(save_path).replace("\\", "/").rstrip("/")
            else:
                save_path_normalized = ""
            
            content_path = torrent.get("content_path")
            if content_path:
                content_path_normalized = os.path.normpath(content_path).replace("\\", "/").rstrip("/")
            else:
                content_path_normalized = None

            # Vérifier aussi le nom du torrent (peut contenir le nom du film/série)
            torrent_name = torrent.get("name", "").lower()

            # Check if media_path is within save_path or matches content_path
            if self.match_mode == "path":
                # Match by directory path (string comparison, much faster)
                matched = False
                
                # 1. Vérifier content_path (plus précis)
                if content_path_normalized:
                    if media_path_normalized == content_path_normalized or \
                       media_path_normalized.startswith(content_path_normalized + "/") or \
                       content_path_normalized.startswith(media_path_normalized + "/"):
                        matched = True
                
                # 2. Vérifier save_path
                if not matched and save_path_normalized:
                    if media_path_normalized == save_path_normalized or \
                       media_path_normalized.startswith(save_path_normalized + "/") or \
                       save_path_normalized.startswith(media_path_normalized + "/"):
                        matched = True
                
                # 3. Vérifier si le nom du média est dans le nom du torrent (fallback)
                if not matched and torrent_name:
                    # Extraire le nom du dossier/fichier depuis le chemin média
                    media_name = os.path.basename(media_path_normalized).lower()
                    if media_name and media_name in torrent_name:
                        matched = True
                
                if matched:
                    matching_hashes.append(torrent["hash"])

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

