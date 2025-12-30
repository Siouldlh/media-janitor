"""Garde-fous et exclusions."""
from typing import List, Tuple, Optional
from pathlib import Path

from app.core.models import MediaItem
from app.services.overseerr import OverseerrService
from app.services.qbittorrent import QBittorrentService
from app.config import get_config


class SafetyChecker:
    """Vérifie les garde-fous avant suppression."""

    def __init__(self):
        self.config = get_config()
        self.overseerr_service = OverseerrService() if self.config.overseerr else None
        self.qb_service = QBittorrentService() if self.config.qbittorrent else None
        # Charger les exclusions depuis la config
        self.excluded_paths: List[str] = self.config.app.excluded_paths if self.config.app else []

    def is_protected(self, media_item: MediaItem) -> Tuple[bool, Optional[str]]:
        """Vérifie si un média est protégé (ne doit pas être supprimé)."""
        # Check path exclusions
        primary_path = media_item.get_primary_path()
        if primary_path:
            for excluded_path in self.excluded_paths:
                try:
                    excluded_path_obj = Path(excluded_path)
                    primary_path_obj = Path(primary_path)
                    # Vérifier si le chemin est dans l'exclusion ou l'inverse
                    if (primary_path_obj.is_relative_to(excluded_path_obj) or
                        excluded_path_obj in primary_path_obj.parents or
                        str(primary_path).startswith(str(excluded_path))):
                        return True, f"Path excluded: {excluded_path}"
                except (OSError, ValueError):
                    # Si is_relative_to n'est pas disponible (Python < 3.9), utiliser startswith
                    if str(primary_path).startswith(str(excluded_path)):
                        return True, f"Path excluded: {excluded_path}"
                    pass

        # Check Radarr/Sonarr protected tags
        if media_item.type == "movie" and self.config.radarr:
            for tag in media_item.tags:
                if tag in self.config.radarr.protected_tags:
                    return True, f"Protected tag: {tag}"
        elif media_item.type in ["series", "episode"] and self.config.sonarr:
            for tag in media_item.tags:
                if tag in self.config.sonarr.protected_tags:
                    return True, f"Protected tag: {tag}"

        # Check qBittorrent protected categories
        if self.qb_service:
            for category in media_item.qb_categories:
                if self.qb_service.is_protected_category(category):
                    return True, f"Protected qB category: {category}"

        # Check Overseerr protection
        if self.overseerr_service:
            protected, reason = self.overseerr_service.is_protected(media_item)
            if protected:
                return True, reason

        # Check DB protections (exclusions persistées)
        from app.db.database import get_db_sync
        from app.db.models import Protection
        db = get_db_sync()
        protections = db.query(Protection).all()
        for protection in protections:
            # Match par ID
            if media_item.type == "movie" and protection.tmdb_id:
                if media_item.tmdb_id == protection.tmdb_id:
                    return True, f"Protected in DB: {protection.reason or 'Manual protection'}"
            elif media_item.type in ["series", "episode"]:
                if protection.tvdb_id and media_item.tvdb_id == protection.tvdb_id:
                    return True, f"Protected in DB: {protection.reason or 'Manual protection'}"
                if protection.tmdb_id and media_item.tmdb_id == protection.tmdb_id:
                    return True, f"Protected in DB: {protection.reason or 'Manual protection'}"
            # Match par path
            if protection.path and primary_path:
                if str(primary_path).startswith(protection.path) or protection.path in str(primary_path):
                    return True, f"Protected in DB: {protection.reason or 'Manual protection'}"

        return False, None

    def add_excluded_path(self, path: str) -> None:
        """Ajoute un chemin à exclure."""
        if path not in self.excluded_paths:
            self.excluded_paths.append(path)

    def remove_excluded_path(self, path: str) -> None:
        """Retire un chemin des exclusions."""
        if path in self.excluded_paths:
            self.excluded_paths.remove(path)

