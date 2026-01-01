"""Module de matching avancé pour associer torrents qBittorrent aux médias."""
import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


class TorrentMatcher:
    """Matcher avancé pour associer torrents qBittorrent aux médias."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def normalize_path(self, path: str) -> str:
        """Normalise un chemin pour comparaison."""
        if not path:
            return ""
        # Normaliser les séparateurs
        normalized = os.path.normpath(path).replace("\\", "/").rstrip("/")
        return normalized.lower()
    
    def extract_title_clean(self, title: str) -> str:
        """Extrait un titre nettoyé pour matching."""
        if not title:
            return ""
        # Enlever caractères spéciaux, années, extensions
        clean = re.sub(r'[^\w\s]', '', title.lower())
        clean = re.sub(r'\.(mkv|mp4|avi|mov|m4v)$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s+\(\d{4}\)', '', clean)
        return clean.strip()
    
    def extract_year(self, text: str) -> Optional[int]:
        """Extrait l'année d'un texte."""
        match = re.search(r'\((\d{4})\)', text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None
    
    def match_by_exact_path(
        self,
        media_path: str,
        torrent: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Stratégie 1: Matching exact par chemin."""
        media_path_norm = self.normalize_path(media_path)
        
        # Vérifier content_path
        content_path = torrent.get("content_path")
        if content_path:
            content_path_norm = self.normalize_path(content_path)
            if media_path_norm == content_path_norm:
                return True, "exact_content_path"
            # Vérifier relation parent/enfant
            if media_path_norm.startswith(content_path_norm + "/") or \
               content_path_norm.startswith(media_path_norm + "/"):
                return True, "path_parent_child"
        
        # Vérifier save_path
        save_path = torrent.get("save_path", "")
        if save_path:
            save_path_norm = self.normalize_path(save_path)
            torrent_name = torrent.get("name", "")
            if torrent_name:
                # Construire le chemin complet
                full_path = os.path.join(save_path, torrent_name).replace("\\", "/")
                full_path_norm = self.normalize_path(full_path)
                if media_path_norm == full_path_norm:
                    return True, "exact_save_path"
                if media_path_norm.startswith(full_path_norm + "/") or \
                   full_path_norm.startswith(media_path_norm + "/"):
                    return True, "save_path_parent_child"
        
        return False, None
    
    def match_by_torrent_files(
        self,
        media_path: str,
        torrent: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Stratégie 2: Matching par fichiers dans le torrent."""
        media_path_norm = self.normalize_path(media_path)
        media_name = os.path.basename(media_path_norm)
        media_name_clean = self.extract_title_clean(media_name)
        
        torrent_files = torrent.get("files", [])
        if not torrent_files:
            return False, None
        
        for torrent_file in torrent_files:
            if not torrent_file:
                continue
            
            torrent_file_norm = self.normalize_path(torrent_file)
            torrent_file_name = os.path.basename(torrent_file_norm)
            
            # Match exact du nom de fichier
            if media_name == torrent_file_name:
                return True, "exact_filename_match"
            
            # Match du chemin complet
            if media_path_norm in torrent_file_norm or torrent_file_norm in media_path_norm:
                return True, "file_path_match"
            
            # Match partiel du nom nettoyé
            if media_name_clean and len(media_name_clean) > 3:
                torrent_file_clean = self.extract_title_clean(torrent_file_name)
                if media_name_clean in torrent_file_clean or torrent_file_clean in media_name_clean:
                    # Vérifier aussi la similarité (au moins 80% des caractères communs)
                    common_chars = sum(1 for c in media_name_clean if c in torrent_file_clean)
                    if len(media_name_clean) > 0 and common_chars / len(media_name_clean) >= 0.8:
                        return True, "filename_partial_match"
        
        return False, None
    
    def match_by_torrent_name(
        self,
        media_path: str,
        media_title: Optional[str],
        torrent: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Stratégie 3: Matching par nom du torrent."""
        torrent_name = torrent.get("name", "").lower()
        if not torrent_name:
            return False, None
        
        # Utiliser le titre du média si disponible
        title_to_match = media_title if media_title else os.path.basename(media_path)
        title_clean = self.extract_title_clean(title_to_match)
        
        if not title_clean or len(title_clean) < 3:
            return False, None
        
        torrent_name_clean = self.extract_title_clean(torrent_name)
        
        # Comparaison directe
        if title_clean in torrent_name_clean or torrent_name_clean in title_clean:
            # Vérifier aussi les chemins si disponibles
            save_path = torrent.get("save_path", "")
            media_dir = os.path.dirname(self.normalize_path(media_path))
            if save_path and media_dir:
                save_path_norm = self.normalize_path(save_path)
                save_parts = [p for p in save_path_norm.split("/") if p and len(p) > 2]
                media_parts = [p for p in media_dir.split("/") if p and len(p) > 2]
                common_parts = set(save_parts) & set(media_parts)
                if len(common_parts) > 0:
                    return True, "torrent_name_with_common_path"
            return True, "torrent_name_match"
        
        # Similarité de caractères (au moins 60%)
        if len(title_clean) > 5:
            common_chars = sum(1 for c in title_clean if c in torrent_name_clean)
            if common_chars / len(title_clean) >= 0.6:
                return True, "torrent_name_similarity"
        
        return False, None
    
    def match_by_year_and_title(
        self,
        media_path: str,
        media_title: Optional[str],
        torrent: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Stratégie 4: Matching par année + titre."""
        title_to_match = media_title if media_title else os.path.basename(media_path)
        media_year = self.extract_year(title_to_match) or self.extract_year(media_path)
        
        torrent_name = torrent.get("name", "")
        torrent_year = self.extract_year(torrent_name)
        
        if not media_year or not torrent_year:
            return False, None
        
        # Même année (tolérance ±1)
        if abs(media_year - torrent_year) <= 1:
            title_clean = self.extract_title_clean(title_to_match)
            torrent_name_clean = self.extract_title_clean(torrent_name)
            
            if title_clean and len(title_clean) > 5:
                # Vérifier que les premiers caractères du titre correspondent
                if title_clean[:5] in torrent_name_clean or torrent_name_clean[:5] in title_clean:
                    return True, "year_and_title_match"
        
        return False, None
    
    def match_by_path_parts(
        self,
        media_path: str,
        torrent: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Stratégie 5: Matching par parties du chemin (dossiers)."""
        media_path_norm = self.normalize_path(media_path)
        path_parts = [p for p in media_path_norm.split("/") if p and len(p) > 2]
        
        if not path_parts:
            return False, None
        
        # Vérifier les 3 derniers dossiers
        relevant_parts = path_parts[-3:]
        
        content_path = torrent.get("content_path")
        if content_path:
            content_path_norm = self.normalize_path(content_path)
            for part in relevant_parts:
                if part in content_path_norm:
                    return True, "path_part_in_content"
        
        save_path = torrent.get("save_path", "")
        if save_path:
            save_path_norm = self.normalize_path(save_path)
            for part in relevant_parts:
                if part in save_path_norm:
                    return True, "path_part_in_save"
        
        torrent_name = torrent.get("name", "").lower()
        if torrent_name:
            for part in relevant_parts:
                if part in torrent_name:
                    return True, "path_part_in_name"
        
        return False, None
    
    def find_matching_torrents(
        self,
        media_path: str,
        all_torrents: List[Dict[str, Any]],
        media_title: Optional[str] = None
    ) -> List[str]:
        """Trouve tous les torrents correspondant à un média avec stratégies multi-niveaux.
        
        Args:
            media_path: Chemin du média (fichier ou dossier)
            all_torrents: Liste de tous les torrents
            media_title: Titre du média (optionnel, améliore le matching)
        
        Returns:
            Liste des hash des torrents correspondants
        """
        if not media_path or not all_torrents:
            return []
        
        matching_hashes = []
        media_path_norm = self.normalize_path(media_path)
        
        if self.debug:
            logger.info(
                "torrent_matching_start",
                media_path=media_path_norm[:100],
                media_title=media_title,
                total_torrents=len(all_torrents)
            )
        
        for idx, torrent in enumerate(all_torrents):
            matched = False
            match_reason = None
            
            # Stratégie 1: Chemin exact (le plus fiable)
            matched, match_reason = self.match_by_exact_path(media_path, torrent)
            if matched:
                matching_hashes.append(torrent["hash"])
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent["hash"][:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
                continue
            
            # Stratégie 2: Fichiers dans le torrent
            matched, match_reason = self.match_by_torrent_files(media_path, torrent)
            if matched:
                matching_hashes.append(torrent["hash"])
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent["hash"][:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
                continue
            
            # Stratégie 3: Nom du torrent
            matched, match_reason = self.match_by_torrent_name(media_path, media_title, torrent)
            if matched:
                matching_hashes.append(torrent["hash"])
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent["hash"][:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
                continue
            
            # Stratégie 4: Année + titre
            matched, match_reason = self.match_by_year_and_title(media_path, media_title, torrent)
            if matched:
                matching_hashes.append(torrent["hash"])
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent["hash"][:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
                continue
            
            # Stratégie 5: Parties du chemin (dernier recours)
            matched, match_reason = self.match_by_path_parts(media_path, torrent)
            if matched:
                matching_hashes.append(torrent["hash"])
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent["hash"][:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
        
        if matching_hashes:
            logger.info(
                "torrent_matching_complete",
                media_path=media_path_norm[:100],
                matches=len(matching_hashes),
                total_torrents=len(all_torrents)
            )
        elif self.debug:
            logger.debug(
                "torrent_matching_no_match",
                media_path=media_path_norm[:100],
                media_title=media_title
            )
        
        return matching_hashes

