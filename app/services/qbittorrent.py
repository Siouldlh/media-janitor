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
                        # Les fichiers peuvent être des dicts, des objets, ou des NamedTuples
                        for f in files:
                            file_name = None
                            if isinstance(f, dict):
                                # Format dict: {"name": "...", "size": ...}
                                file_name = f.get("name", "") or f.get("path", "")
                            elif hasattr(f, "name"):
                                # Format objet avec attribut name
                                file_name = getattr(f, "name", None)
                            elif hasattr(f, "path"):
                                # Format objet avec attribut path
                                file_name = getattr(f, "path", None)
                            elif isinstance(f, (list, tuple)) and len(f) > 0:
                                # Format tuple/list, le premier élément est souvent le nom
                                file_name = str(f[0]) if f[0] else None
                            else:
                                # Dernier recours: convertir en string
                                file_name = str(f) if f else None
                            
                            if file_name:
                                # Normaliser le chemin (enlever les backslashes Windows)
                                file_name = file_name.replace("\\", "/")
                                torrent_files.append(file_name)
                except Exception as e:
                    logger.debug("torrent_files_error", 
                               hash=torrent.hash[:8], 
                               error=str(e))
                
                # Essayer d'obtenir content_path depuis différentes sources
                content_path = None
                
                # Debug: logger les attributs disponibles
                if idx < 3:
                    torrent_attrs = [attr for attr in dir(torrent) if not attr.startswith("_")]
                    logger.debug("torrent_attributes_sample",
                               index=idx,
                               hash=torrent.hash[:8] if hasattr(torrent, "hash") else "N/A",
                               attrs=torrent_attrs[:20])
                
                # Méthode 1: Attribut direct content_path (peut ne pas exister dans toutes les versions)
                if hasattr(torrent, "content_path") and torrent.content_path:
                    content_path = str(torrent.content_path).replace("\\", "/")
                    if idx < 3:
                        logger.debug("content_path_from_attr", path=content_path[:80])
                # Méthode 2: Depuis save_path + name (méthode standard)
                elif hasattr(torrent, "save_path") and torrent.save_path:
                    import os
                    save_path = str(torrent.save_path)
                    # Le nom du torrent peut être dans différents attributs
                    torrent_name = None
                    if hasattr(torrent, "name") and torrent.name:
                        torrent_name = str(torrent.name)
                    elif hasattr(torrent, "title") and torrent.title:
                        torrent_name = str(torrent.title)
                    
                    if torrent_name:
                        content_path = os.path.join(save_path, torrent_name).replace("\\", "/")
                        if idx < 3:
                            logger.debug("content_path_from_save_path",
                                       save_path=save_path[:60],
                                       name=torrent_name[:50],
                                       content_path=content_path[:80])
                    else:
                        # Si pas de nom, utiliser juste save_path
                        content_path = save_path.replace("\\", "/")
                        if idx < 3:
                            logger.debug("content_path_from_save_path_only", path=content_path[:80])
                # Méthode 3: Depuis le premier fichier si disponible
                elif torrent_files:
                    # Utiliser le répertoire du premier fichier comme content_path
                    first_file = torrent_files[0]
                    import os
                    content_path = os.path.dirname(first_file).replace("\\", "/")
                    if not content_path:
                        # Si pas de répertoire, utiliser le nom du fichier
                        content_path = first_file
                    if idx < 3:
                        logger.debug("content_path_from_files", path=content_path[:80])
                
                result.append({
                    "hash": torrent.hash,
                    "name": str(torrent.name) if hasattr(torrent, "name") else "",
                    "save_path": str(torrent.save_path) if hasattr(torrent, "save_path") else "",
                    "category": str(torrent.category) if hasattr(torrent, "category") and torrent.category else "",
                    "tags": torrent.tags.split(",") if hasattr(torrent, "tags") and torrent.tags else [],
                    "state": str(torrent.state) if hasattr(torrent, "state") else "",
                    "content_path": content_path,
                    "size": int(torrent.size) if hasattr(torrent, "size") else 0,
                    "files": torrent_files,  # Liste des fichiers dans le torrent
                })
                
                if idx < 3:
                    logger.debug("sample_torrent",
                               index=idx+1,
                               name=str(torrent.name)[:50] if hasattr(torrent, "name") else "N/A",
                               save_path=str(torrent.save_path)[:50] if hasattr(torrent, "save_path") else "N/A",
                               content_path=content_path[:50] if content_path else "N/A",
                               files_count=len(torrent_files))

            total_files = sum(len(t.get("files", [])) for t in result)
            logger.info("torrents_retrieved", count=len(result), total_files=total_files)
            return result
        except Exception as e:
            logger.exception("error_fetching_torrents", exc_info=True)
            raise

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

