"""Core business models."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class MediaItem:
    """Item média unifié (film/série/épisode)."""
    type: str  # movie, series, episode
    title: str
    year: Optional[int] = None

    # IDs
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    plex_rating_key: Optional[str] = None

    # Paths
    radarr_path: Optional[str] = None
    sonarr_path: Optional[str] = None
    plex_path: Optional[str] = None

    # Plex data
    last_viewed_at: Optional[datetime] = None
    view_count: int = 0
    never_watched: bool = False

    # Overseerr data
    overseerr_requested_by: Optional[str] = None
    overseerr_requested_at: Optional[datetime] = None
    overseerr_status: Optional[str] = None  # requested, approved, available
    overseerr_request_id: Optional[int] = None

    # qBittorrent
    qb_hashes: List[str] = field(default_factory=list)  # Liste des hash torrents
    qb_categories: List[str] = field(default_factory=list)

    # Radarr/Sonarr
    tags: List[str] = field(default_factory=list)
    monitored: bool = True

    # Metadata additionnelle
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_primary_path(self) -> Optional[str]:
        """Retourne le chemin principal (radarr ou sonarr)."""
        return self.radarr_path or self.sonarr_path

    def get_primary_id(self) -> Optional[int]:
        """Retourne l'ID principal (tmdb pour films, tvdb pour séries)."""
        if self.type == "movie":
            return self.tmdb_id
        elif self.type in ["series", "episode"]:
            return self.tvdb_id or self.tmdb_id
        return None

