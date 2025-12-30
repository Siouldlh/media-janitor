"""Matching cross-services pour unifier les médias."""
from typing import List, Dict, Optional
from pathlib import Path
import difflib
import logging

from app.core.models import MediaItem

logger = logging.getLogger(__name__)


class MediaMatcher:
    """Matcher pour unifier les médias entre services."""

    @staticmethod
    def match_by_id(media_item: MediaItem, candidates: List[MediaItem]) -> Optional[MediaItem]:
        """Match par ID (TMDb/TVDb/IMDb)."""
        primary_id = media_item.get_primary_id()
        if not primary_id:
            return None

        for candidate in candidates:
            if media_item.type == "movie":
                if candidate.tmdb_id and candidate.tmdb_id == media_item.tmdb_id:
                    return candidate
                if candidate.imdb_id and media_item.imdb_id and candidate.imdb_id == media_item.imdb_id:
                    return candidate
            elif media_item.type in ["series", "episode"]:
                if candidate.tvdb_id and media_item.tvdb_id and candidate.tvdb_id == media_item.tvdb_id:
                    return candidate
                if candidate.tmdb_id and media_item.tmdb_id and candidate.tmdb_id == media_item.tmdb_id:
                    return candidate
                if candidate.imdb_id and media_item.imdb_id and candidate.imdb_id == media_item.imdb_id:
                    return candidate

        return None

    @staticmethod
    def match_by_title_year(media_item: MediaItem, candidates: List[MediaItem], threshold: float = 0.8) -> Optional[MediaItem]:
        """Match par titre + année (fallback)."""
        if not media_item.title:
            return None

        best_match = None
        best_ratio = 0.0

        for candidate in candidates:
            if not candidate.title:
                continue

            # Title similarity
            title_ratio = difflib.SequenceMatcher(
                None,
                media_item.title.lower(),
                candidate.title.lower()
            ).ratio()

            # Year match bonus
            year_match = False
            if media_item.year and candidate.year:
                year_match = abs(media_item.year - candidate.year) <= 1
            elif media_item.year is None and candidate.year is None:
                year_match = True

            # Combined score
            score = title_ratio
            if year_match:
                score += 0.2
            else:
                score -= 0.3

            if score > best_ratio and score >= threshold:
                best_ratio = score
                best_match = candidate

        return best_match

    @staticmethod
    def match_by_path(media_item: MediaItem, candidates: List[MediaItem]) -> Optional[MediaItem]:
        """Match par chemin de fichier (sans resolve pour éviter les appels réseau lents)."""
        primary_path = media_item.get_primary_path()
        if not primary_path:
            return None

        # Normaliser les chemins sans resolve (évite les appels réseau)
        media_path_normalized = str(Path(primary_path)).rstrip("/")

        for candidate in candidates:
            candidate_path = candidate.get_primary_path()
            if not candidate_path:
                continue

            candidate_path_normalized = str(Path(candidate_path)).rstrip("/")
            
            # Check if paths match exactly
            if media_path_normalized == candidate_path_normalized:
                return candidate
            
            # Check if one is a substring of the other (parent/child relationship)
            if media_path_normalized.startswith(candidate_path_normalized + "/") or \
               candidate_path_normalized.startswith(media_path_normalized + "/"):
                return candidate

        return None

    @staticmethod
    def merge_items(source: MediaItem, target: MediaItem) -> MediaItem:
        """Fusionne deux MediaItem (source dans target)."""
        # Merge IDs (priorité à target)
        if not target.tmdb_id and source.tmdb_id:
            target.tmdb_id = source.tmdb_id
        if not target.tvdb_id and source.tvdb_id:
            target.tvdb_id = source.tvdb_id
        if not target.imdb_id and source.imdb_id:
            target.imdb_id = source.imdb_id
        if not target.plex_rating_key and source.plex_rating_key:
            target.plex_rating_key = source.plex_rating_key

        # Merge paths
        if not target.radarr_path and source.radarr_path:
            target.radarr_path = source.radarr_path
        if not target.sonarr_path and source.sonarr_path:
            target.sonarr_path = source.sonarr_path
        if not target.plex_path and source.plex_path:
            target.plex_path = source.plex_path

        # Merge Plex data (priorité à source pour watched data)
        if source.last_viewed_at:
            if not target.last_viewed_at or source.last_viewed_at > target.last_viewed_at:
                target.last_viewed_at = source.last_viewed_at
        target.view_count = max(target.view_count, source.view_count)
        if source.view_count > 0:
            target.never_watched = False

        # Merge qBittorrent hashes
        target.qb_hashes.extend([h for h in source.qb_hashes if h not in target.qb_hashes])
        target.qb_categories.extend([c for c in source.qb_categories if c not in target.qb_categories])

        # Merge tags
        target.tags.extend([t for t in source.tags if t not in target.tags])

        # Merge metadata
        target.metadata.update(source.metadata)

        return target

    @staticmethod
    def unify_media_items(
        plex_items: List[MediaItem],
        radarr_items: List[MediaItem],
        sonarr_items: List[MediaItem],
        overseerr_items: List[MediaItem],
        qb_torrents: List[Dict],
        qb_service
    ) -> List[MediaItem]:
        """Unifie tous les médias de tous les services."""
        unified: List[MediaItem] = []
        processed_plex = set()
        processed_radarr = set()
        processed_sonarr = set()

        # Start with Radarr/Sonarr items (source of truth for paths)
        logger.info(f"Starting unification: {len(radarr_items)} Radarr, {len(sonarr_items)} Sonarr, {len(plex_items)} Plex items")
        for item in radarr_items + sonarr_items:
            unified.append(item)
            if item.type == "movie":
                processed_radarr.add(id(item))
            else:
                processed_sonarr.add(id(item))

        # Match Plex items
        logger.info(f"Matching {len(plex_items)} Plex items...")
        matched_count = 0
        for idx, plex_item in enumerate(plex_items):
            if idx > 0 and idx % 100 == 0:
                logger.info(f"  Progress: {idx}/{len(plex_items)} Plex items processed, {matched_count} matched")
            
            matched = False

            # Try ID match first (fastest)
            match = MediaMatcher.match_by_id(plex_item, unified)
            if match:
                MediaMatcher.merge_items(plex_item, match)
                matched = True
                matched_count += 1
            else:
                # Try title+year match
                match = MediaMatcher.match_by_title_year(plex_item, unified)
                if match:
                    MediaMatcher.merge_items(plex_item, match)
                    matched = True
                    matched_count += 1
                else:
                    # Try path match
                    match = MediaMatcher.match_by_path(plex_item, unified)
                    if match:
                        MediaMatcher.merge_items(plex_item, match)
                        matched = True
                        matched_count += 1

            if not matched:
                # Add as new item (Plex-only)
                unified.append(plex_item)
        
        logger.info(f"Plex matching completed: {matched_count}/{len(plex_items)} matched, {len(unified)} total unified items")

        # Note: Overseerr enrichment is done separately in planner

        # Enrich with qBittorrent
        if qb_service:
            logger.info(f"Enriching {len(unified)} items with qBittorrent data ({len(qb_torrents)} torrents available)...")
            qb_matched_count = 0
            items_with_path = 0
            for idx, item in enumerate(unified):
                if idx > 0 and idx % 200 == 0:
                    logger.info(f"  Progress: {idx}/{len(unified)} items processed, {qb_matched_count} with torrents, {items_with_path} with paths")
                primary_path = item.get_primary_path()
                if primary_path:
                    items_with_path += 1
                    qb_hashes = qb_service.find_torrents_for_path(primary_path, qb_torrents)
                    if qb_hashes:
                        qb_matched_count += 1
                        if idx < 5:  # Log first 5 matches for debugging
                            logger.debug(f"  Matched {len(qb_hashes)} torrent(s) for {item.title} (path: {primary_path})")
                    item.qb_hashes.extend(qb_hashes)
            logger.info(f"qBittorrent enrichment completed: {qb_matched_count}/{items_with_path} items with paths have torrents")

        return unified

