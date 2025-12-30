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
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            client = self._get_client()
            torrents = client.torrents_info()
            result = []

            for torrent in torrents:
                # Récupérer les fichiers du torrent pour un matching plus précis
                torrent_files = []
                try:
                    files = client.torrents_files(torrent_hash=torrent.hash)
                    torrent_files = [f.get("name", "") for f in files] if files else []
                except Exception as e:
                    logger.debug(f"Could not get files for torrent {torrent.hash}: {e}")
                
                result.append({
                    "hash": torrent.hash,
                    "name": torrent.name,
                    "save_path": torrent.save_path,
                    "category": torrent.category or "",
                    "tags": torrent.tags.split(",") if torrent.tags else [],
                    "state": torrent.state,
                    "content_path": torrent.content_path if hasattr(torrent, "content_path") else None,
                    "size": torrent.size,
                    "files": torrent_files,  # Liste des fichiers dans le torrent
                })

            return result
        except Exception as e:
            raise Exception(f"Error fetching torrents from qBittorrent: {str(e)}")

    def find_torrents_for_path(self, media_path: str, all_torrents: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Trouve tous les torrents (cross-seed) qui pointent vers un chemin média.
        
        Utilise plusieurs stratégies de matching pour maximiser les correspondances.
        """
        import os
        import logging
        logger = logging.getLogger(__name__)
        
        if all_torrents is None:
            all_torrents = self.get_torrents()

        if not media_path:
            return []

        # Normaliser le chemin média
        media_path_normalized = os.path.normpath(media_path).replace("\\", "/").rstrip("/")
        media_path_lower = media_path_normalized.lower()
        media_name = os.path.basename(media_path_normalized).lower()
        media_dir = os.path.dirname(media_path_normalized).lower()
        
        matching_hashes = []
        debug_logged = False  # Logger seulement les premiers pour éviter le spam

        for torrent in all_torrents:
            matched = False
            match_reason = None
            
            # Normaliser les chemins du torrent
            save_path = torrent.get("save_path", "")
            save_path_normalized = os.path.normpath(save_path).replace("\\", "/").rstrip("/").lower() if save_path else ""
            
            content_path = torrent.get("content_path")
            content_path_normalized = os.path.normpath(content_path).replace("\\", "/").rstrip("/").lower() if content_path else None

            torrent_name = torrent.get("name", "").lower()
            torrent_files = torrent.get("files", [])
            
            if self.match_mode == "path":
                # Stratégie 1: Matching exact du chemin
                if content_path_normalized and media_path_lower == content_path_normalized:
                    matched = True
                    match_reason = "exact_content_path"
                elif save_path_normalized and media_path_lower == save_path_normalized:
                    matched = True
                    match_reason = "exact_save_path"
                
                # Stratégie 2: Le chemin média est dans le dossier du torrent
                if not matched:
                    if content_path_normalized:
                        if media_path_lower.startswith(content_path_normalized + "/") or \
                           content_path_normalized.startswith(media_path_lower + "/"):
                            matched = True
                            match_reason = "content_path_parent"
                    elif save_path_normalized:
                        if media_path_lower.startswith(save_path_normalized + "/") or \
                           save_path_normalized.startswith(media_path_lower + "/"):
                            matched = True
                            match_reason = "save_path_parent"
                
                # Stratégie 3: Matching par nom de dossier parent
                if not matched and media_dir:
                    if content_path_normalized and media_dir in content_path_normalized:
                        matched = True
                        match_reason = "content_path_dir_match"
                    elif save_path_normalized and media_dir in save_path_normalized:
                        matched = True
                        match_reason = "save_path_dir_match"
                
                # Stratégie 4: Matching par nom de fichier dans les fichiers du torrent
                if not matched and torrent_files:
                    for torrent_file in torrent_files:
                        torrent_file_normalized = os.path.normpath(torrent_file).replace("\\", "/").lower()
                        # Vérifier si le nom du média est dans le chemin du fichier torrent
                        if media_name and media_name in torrent_file_normalized:
                            matched = True
                            match_reason = "file_name_match"
                            break
                        # Vérifier si le chemin complet du média est dans le fichier torrent
                        if media_path_lower in torrent_file_normalized:
                            matched = True
                            match_reason = "file_path_match"
                            break
                
                # Stratégie 5: Matching par nom du torrent (fallback)
                if not matched and torrent_name and media_name:
                    # Extraire le nom du film/série depuis le chemin
                    # Ex: "/media/movies/Inception (2010)/Inception.mkv" -> "inception"
                    media_name_clean = media_name.replace(".mkv", "").replace(".mp4", "").replace(".avi", "").strip()
                    if media_name_clean and len(media_name_clean) > 3:
                        if media_name_clean in torrent_name:
                            matched = True
                            match_reason = "torrent_name_match"
                
                # Stratégie 6: Matching partiel du chemin (dernier recours)
                if not matched:
                    # Extraire les parties importantes du chemin
                    path_parts = [p for p in media_path_lower.split("/") if p and len(p) > 2]
                    if path_parts:
                        last_parts = path_parts[-2:] if len(path_parts) >= 2 else path_parts
                        for part in last_parts:
                            if content_path_normalized and part in content_path_normalized:
                                matched = True
                                match_reason = "partial_content_path"
                                break
                            elif save_path_normalized and part in save_path_normalized:
                                matched = True
                                match_reason = "partial_save_path"
                                break
                            elif torrent_name and part in torrent_name:
                                matched = True
                                match_reason = "partial_torrent_name"
                                break
                
                if matched:
                    matching_hashes.append(torrent["hash"])
                    if not debug_logged and len(matching_hashes) <= 3:
                        logger.debug(f"Matched torrent {torrent['hash'][:8]}... for {media_path} (reason: {match_reason})")
                        if len(matching_hashes) == 3:
                            debug_logged = True

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

