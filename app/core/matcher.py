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
            items_without_path = 0
            # Créer un mapping hash -> torrent pour récupérer les noms
            torrent_by_hash = {t["hash"]: t for t in qb_torrents if t.get("hash")}
            logger.info(f"Created torrent_by_hash mapping with {len(torrent_by_hash)} torrents")
            
            # Log quelques exemples de chemins média et torrents pour debug
            if len(unified) > 0 and len(qb_torrents) > 0:
                sample_item = unified[0]
                sample_torrent = qb_torrents[0]
                primary_path = sample_item.get_primary_path()
                media_path_str = primary_path[:100] if primary_path else "N/A"
                media_title_str = sample_item.title[:50] if sample_item.title else "N/A"
                radarr_path_str = sample_item.radarr_path[:80] if sample_item.radarr_path else "N/A"
                sonarr_path_str = sample_item.sonarr_path[:80] if sample_item.sonarr_path else "N/A"
                torrent_name_str = sample_torrent.get("name", "")[:50] if sample_torrent.get("name") else "N/A"
                torrent_content_path_str = sample_torrent.get("content_path", "")[:100] if sample_torrent.get("content_path") else "N/A"
                torrent_save_path_str = sample_torrent.get("save_path", "")[:80] if sample_torrent.get("save_path") else "N/A"
                torrent_files_count = len(sample_torrent.get("files", []))
                torrent_first_file_str = sample_torrent.get("files", [""])[0][:80] if sample_torrent.get("files") else "N/A"
                logger.info(f"matching_debug_samples: media_path={media_path_str}, media_title={media_title_str}, "
                          f"media_type={sample_item.type}, radarr_path={radarr_path_str}, sonarr_path={sonarr_path_str}, "
                          f"torrent_name={torrent_name_str}, torrent_content_path={torrent_content_path_str}, "
                          f"torrent_save_path={torrent_save_path_str}, torrent_files_count={torrent_files_count}, "
                          f"torrent_first_file={torrent_first_file_str}")
                
                # Tester le matching pour le premier item avec TOUS les torrents
                if primary_path:
                    test_hashes = qb_service.find_torrents_for_path(
                        primary_path,
                        qb_torrents,  # Tester avec TOUS les torrents
                        media_title=sample_item.title
                    )
                    logger.info("matching_test_first_item",
                               media_path=primary_path[:100],
                               media_title=sample_item.title[:50],
                               total_torrents_tested=len(qb_torrents),
                               matches=len(test_hashes),
                               matched_hashes=[h[:8] for h in test_hashes[:5]])
                    
                    # Si aucun match, logger les 5 premiers torrents pour comparaison
                    if not test_hashes and len(qb_torrents) > 0:
                        sample_torrents = [
                            {
                                "name": t.get("name", "")[:60],
                                "content_path": t.get("content_path", "")[:80],
                                "save_path": t.get("save_path", "")[:60],
                            }
                            for t in qb_torrents[:5]
                        ]
                        logger.warning(f"no_matches_for_first_item: media_path={primary_path[:100]}, "
                                     f"sample_torrents={sample_torrents}")
            
            for idx, item in enumerate(unified):
                if idx > 0 and idx % 200 == 0:
                    logger.info(f"  Progress: {idx}/{len(unified)} items processed, {qb_matched_count} with torrents, {items_with_path} with paths")
                primary_path = item.get_primary_path()
                if primary_path:
                    items_with_path += 1
                    # Passer aussi le titre pour améliorer le matching (surtout pour séries)
                    qb_hashes = qb_service.find_torrents_for_path(primary_path, qb_torrents, media_title=item.title)
                    if qb_hashes:
                        qb_matched_count += 1
                        if idx < 10:  # Log first 10 matches for debugging
                            logger.info(f"  ✓ Matched {len(qb_hashes)} torrent(s) for '{item.title}' (path: {primary_path[:60]}...)")
                        item.qb_hashes.extend(qb_hashes)
                        # Stocker les noms des torrents dans metadata
                        torrent_names = []
                        for hash_val in qb_hashes:
                            torrent = torrent_by_hash.get(hash_val)
                            if torrent:
                                torrent_names.append({
                                    "hash": hash_val,
                                    "name": torrent.get("name", ""),
                                })
                        if torrent_names:
                            item.metadata["qb_torrents"] = torrent_names
                else:
                    items_without_path += 1
                    if idx < 5:
                        logger.debug(f"  No path for item '{item.title}' (type: {item.type})")
            logger.info(f"qBittorrent enrichment completed: {qb_matched_count}/{items_with_path} items with paths have torrents ({items_without_path} items without paths)")

        return unified

