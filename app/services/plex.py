"""Plex API client."""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from plexapi.server import PlexServer
from plexapi.library import MovieSection, ShowSection
from plexapi.video import Movie, Show, Episode

from app.config import get_config
from app.core.models import MediaItem


class PlexService:
    """Service pour interagir avec Plex."""

    def __init__(self):
        config = get_config()
        if not config.plex:
            raise ValueError("Plex configuration not found")
        self.base_url = config.plex.url
        self.token = config.plex.token
        self.libraries = config.plex.libraries
        self._server: Optional[PlexServer] = None

    def is_configured(self) -> bool:
        """Vérifie si le service est configuré."""
        config = get_config()
        return config.plex is not None

    def _get_server(self) -> PlexServer:
        """Get or create Plex server connection."""
        if self._server is None:
            self._server = PlexServer(self.base_url, self.token)
        return self._server

    def get_movies(self) -> List[MediaItem]:
        """Récupère tous les films depuis Plex."""
        try:
            server = self._get_server()
            movies_section = server.library.section(self.libraries.get("movies", "Films"))
            items = []

            for movie in movies_section.all():
                media_item = MediaItem(
                    type="movie",
                    title=movie.title,
                    year=movie.year,
                    plex_rating_key=str(movie.ratingKey),
                    plex_path=movie.locations[0] if movie.locations else None,
                    last_viewed_at=movie.lastViewedAt if hasattr(movie, "lastViewedAt") and movie.lastViewedAt else None,
                    view_count=movie.viewCount if hasattr(movie, "viewCount") else 0,
                    never_watched=movie.viewCount == 0 if hasattr(movie, "viewCount") else True,
                )

                # Try to get TMDb ID from metadata
                if hasattr(movie, "guids"):
                    for guid in movie.guids:
                        if "tmdb" in guid.id.lower():
                            try:
                                media_item.tmdb_id = int(guid.id.split("//")[-1])
                            except (ValueError, IndexError):
                                pass
                        elif "imdb" in guid.id.lower():
                            try:
                                media_item.imdb_id = guid.id.split("//")[-1]
                            except IndexError:
                                pass

                items.append(media_item)

            return items
        except Exception as e:
            raise Exception(f"Error fetching movies from Plex: {str(e)}")

    def get_series(self) -> List[MediaItem]:
        """Récupère toutes les séries depuis Plex."""
        try:
            server = self._get_server()
            series_section = server.library.section(self.libraries.get("series", "Series"))
            items = []

            for show in series_section.all():
                # Get last viewed episode date
                last_viewed = None
                view_count = 0
                for episode in show.episodes():
                    if hasattr(episode, "lastViewedAt") and episode.lastViewedAt:
                        if last_viewed is None or episode.lastViewedAt > last_viewed:
                            last_viewed = episode.lastViewedAt
                    if hasattr(episode, "viewCount") and episode.viewCount:
                        view_count += episode.viewCount

                media_item = MediaItem(
                    type="series",
                    title=show.title,
                    year=show.year,
                    plex_rating_key=str(show.ratingKey),
                    plex_path=show.locations[0] if show.locations else None,
                    last_viewed_at=last_viewed,
                    view_count=view_count,
                    never_watched=view_count == 0,
                )

                # Try to get TVDb/TMDb ID from metadata
                if hasattr(show, "guids"):
                    for guid in show.guids:
                        if "tvdb" in guid.id.lower():
                            try:
                                media_item.tvdb_id = int(guid.id.split("//")[-1])
                            except (ValueError, IndexError):
                                pass
                        elif "tmdb" in guid.id.lower():
                            try:
                                media_item.tmdb_id = int(guid.id.split("//")[-1])
                            except (ValueError, IndexError):
                                pass
                        elif "imdb" in guid.id.lower():
                            try:
                                media_item.imdb_id = guid.id.split("//")[-1]
                            except IndexError:
                                pass

                items.append(media_item)

            return items
        except Exception as e:
            raise Exception(f"Error fetching series from Plex: {str(e)}")

    def get_episodes(self, series_rating_key: str) -> List[MediaItem]:
        """Récupère les épisodes d'une série."""
        try:
            server = self._get_server()
            show = server.fetchItem(series_rating_key)
            items = []

            for episode in show.episodes():
                media_item = MediaItem(
                    type="episode",
                    title=f"{show.title} - S{episode.seasonNumber:02d}E{episode.episodeNumber:02d}",
                    plex_rating_key=str(episode.ratingKey),
                    plex_path=episode.locations[0] if episode.locations else None,
                    last_viewed_at=episode.lastViewedAt if hasattr(episode, "lastViewedAt") and episode.lastViewedAt else None,
                    view_count=episode.viewCount if hasattr(episode, "viewCount") else 0,
                    never_watched=episode.viewCount == 0 if hasattr(episode, "viewCount") else True,
                )
                media_item.metadata["series_title"] = show.title
                media_item.metadata["season"] = episode.seasonNumber
                media_item.metadata["episode"] = episode.episodeNumber
                items.append(media_item)

            return items
        except Exception as e:
            raise Exception(f"Error fetching episodes from Plex: {str(e)}")

    def refresh_library(self, library_name: Optional[str] = None) -> bool:
        """Refresh Plex library (optionnel après suppression)."""
        try:
            server = self._get_server()
            if library_name:
                section = server.library.section(library_name)
                section.update()
            else:
                server.library.updateAll()
            return True
        except Exception as e:
            raise Exception(f"Error refreshing Plex library: {str(e)}")

    def empty_trash(self) -> bool:
        """Empty Plex trash (optionnel après suppression)."""
        try:
            server = self._get_server()
            server.library.cleanBundles()
            return True
        except Exception as e:
            raise Exception(f"Error emptying Plex trash: {str(e)}")

