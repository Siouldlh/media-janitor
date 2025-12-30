"""Moteur de règles pour déterminer les candidats à la suppression."""
from typing import Optional, Tuple
from datetime import datetime, timedelta

from app.core.models import MediaItem
from app.config import get_config


class RulesEngine:
    """Moteur d'évaluation des règles."""

    def __init__(self):
        self.config = get_config()

    def evaluate_movie(self, media_item: MediaItem) -> Tuple[bool, Optional[str]]:
        """Évalue si un film est candidat à la suppression."""
        if media_item.type != "movie":
            return False, None

        rules = self.config.rules.movies
        delete_if_not_watched_days = rules.get("delete_if_not_watched_days", 60)
        if_never_watched_use_added_days = rules.get("if_never_watched_use_added_days", 60)

        # Si jamais regardé
        if media_item.never_watched or media_item.view_count == 0:
            # Utiliser date d'ajout si disponible (depuis Radarr/Sonarr)
            added_date = media_item.metadata.get("added_at") or media_item.metadata.get("radarr_added") or media_item.metadata.get("sonarr_added")
            if added_date:
                if isinstance(added_date, str):
                    try:
                        added_date = datetime.fromisoformat(added_date.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        return False, None
                days_since_added = (datetime.now(added_date.tzinfo) - added_date).days
                if days_since_added >= if_never_watched_use_added_days:
                    return True, f"never_watched_{if_never_watched_use_added_days}d"
            return False, None

        # Si regardé, vérifier last_viewed_at
        if media_item.last_viewed_at:
            days_since_watched = (datetime.now(media_item.last_viewed_at.tzinfo) - media_item.last_viewed_at).days
            if days_since_watched >= delete_if_not_watched_days:
                return True, f"not_watched_{delete_if_not_watched_days}d"

        return False, None

    def evaluate_series(self, media_item: MediaItem) -> Tuple[bool, Optional[str]]:
        """Évalue si une série est candidate à la suppression (série entière)."""
        if media_item.type != "series":
            return False, None

        rules = self.config.rules.series
        delete_entire_series_if_inactive_days = rules.get("delete_entire_series_if_inactive_days", 120)

        # Vérifier si aucun épisode n'a été vu depuis X jours
        if media_item.last_viewed_at:
            days_since_watched = (datetime.now(media_item.last_viewed_at.tzinfo) - media_item.last_viewed_at).days
            if days_since_watched >= delete_entire_series_if_inactive_days:
                return True, f"series_inactive_{delete_entire_series_if_inactive_days}d"

        return False, None

    def evaluate_episode(self, media_item: MediaItem) -> Tuple[bool, Optional[str]]:
        """Évalue si un épisode est candidat à la suppression."""
        if media_item.type != "episode":
            return False, None

        rules = self.config.rules.series
        delete_episodes_not_watched_days = rules.get("delete_episodes_not_watched_days", 60)

        # Si jamais regardé
        if media_item.never_watched or media_item.view_count == 0:
            # Utiliser date d'ajout si disponible (depuis Radarr/Sonarr)
            added_date = media_item.metadata.get("added_at") or media_item.metadata.get("radarr_added") or media_item.metadata.get("sonarr_added")
            if added_date:
                if isinstance(added_date, str):
                    try:
                        added_date = datetime.fromisoformat(added_date.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        return False, None
                days_since_added = (datetime.now(added_date.tzinfo) - added_date).days
                if days_since_added >= delete_episodes_not_watched_days:
                    return True, f"episode_never_watched_{delete_episodes_not_watched_days}d"
            return False, None

        # Si regardé, vérifier last_viewed_at
        if media_item.last_viewed_at:
            days_since_watched = (datetime.now(media_item.last_viewed_at.tzinfo) - media_item.last_viewed_at).days
            if days_since_watched >= delete_episodes_not_watched_days:
                return True, f"episode_not_watched_{delete_episodes_not_watched_days}d"

        return False, None

    def evaluate(self, media_item: MediaItem) -> Tuple[bool, Optional[str]]:
        """Évalue un média selon son type."""
        if media_item.type == "movie":
            return self.evaluate_movie(media_item)
        elif media_item.type == "series":
            return self.evaluate_series(media_item)
        elif media_item.type == "episode":
            return self.evaluate_episode(media_item)
        return False, None

