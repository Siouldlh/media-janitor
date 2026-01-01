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
        """Normalise un chemin pour comparaison.
        
        Gère les différences entre Windows et Linux, et normalise les chemins
        pour permettre le matching même si les formats diffèrent.
        """
        if not path:
            return ""
        # Convertir en string si ce n'est pas déjà le cas
        path = str(path)
        # Normaliser les séparateurs (Windows -> Unix)
        normalized = os.path.normpath(path).replace("\\", "/")
        # Enlever les trailing slashes
        normalized = normalized.rstrip("/")
        # Convertir en minuscules pour comparaison case-insensitive
        normalized = normalized.lower()
        # Enlever les espaces en début/fin
        normalized = normalized.strip()
        return normalized
    
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
        if not media_path:
            return False, None
            
        media_path_norm = self.normalize_path(media_path)
        
        # Vérifier content_path (chemin construit depuis save_path + name)
        content_path = torrent.get("content_path")
        if content_path:
            content_path_norm = self.normalize_path(content_path)
            # Match exact
            if media_path_norm == content_path_norm:
                if self.debug:
                    logger.debug("exact_match_content_path",
                               media=media_path_norm[:80],
                               torrent=content_path_norm[:80])
                return True, "exact_content_path"
            # Vérifier relation parent/enfant (un chemin contient l'autre)
            if media_path_norm.startswith(content_path_norm + "/") or \
               content_path_norm.startswith(media_path_norm + "/"):
                if self.debug:
                    logger.debug("parent_child_match_content_path",
                               media=media_path_norm[:80],
                               torrent=content_path_norm[:80])
                return True, "path_parent_child"
        
        # Vérifier save_path + name (TOUJOURS vérifier même si content_path existe)
        save_path = torrent.get("save_path", "")
        torrent_name = torrent.get("name", "")
        if save_path and torrent_name:
            # Construire le chemin complet
            full_path = os.path.join(save_path, torrent_name).replace("\\", "/")
            full_path_norm = self.normalize_path(full_path)
            
            # Si content_path existe mais est différent, logger pour debug
            if content_path and self.debug:
                content_path_norm_check = self.normalize_path(content_path)
                if full_path_norm != content_path_norm_check:
                    logger.debug("content_path_mismatch",
                               constructed=full_path_norm[:80],
                               from_attr=content_path_norm_check[:80])
            
            # Match exact
            if media_path_norm == full_path_norm:
                if self.debug:
                    logger.debug("exact_match_save_path",
                               media=media_path_norm[:80],
                               torrent=full_path_norm[:80])
                return True, "exact_save_path"
            # Relation parent/enfant
            if media_path_norm.startswith(full_path_norm + "/") or \
               full_path_norm.startswith(media_path_norm + "/"):
                if self.debug:
                    logger.debug("parent_child_match_save_path",
                               media=media_path_norm[:80],
                               torrent=full_path_norm[:80])
                return True, "save_path_parent_child"
        
        # Vérifier aussi save_path seul (pour les cas où le torrent est directement dans save_path)
        if save_path:
            save_path_norm = self.normalize_path(save_path)
            if media_path_norm == save_path_norm or \
               media_path_norm.startswith(save_path_norm + "/") or \
               save_path_norm.startswith(media_path_norm + "/"):
                if self.debug:
                    logger.debug("match_save_path_only",
                               media=media_path_norm[:80],
                               torrent=save_path_norm[:80])
                return True, "save_path_only"
        
        # Si aucun match, logger pour debug (seulement pour les premiers)
        if self.debug:
            logger.debug("no_path_match",
                       media=media_path_norm[:80],
                       torrent_content_path=content_path[:80] if content_path else "N/A",
                       torrent_save_path=save_path[:60] if save_path else "N/A",
                       torrent_name=torrent_name[:50] if torrent_name else "N/A")
        
        return False, None
    
    def match_by_torrent_files(
        self,
        media_path: str,
        torrent: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Stratégie 2: Matching par fichiers dans le torrent."""
        if not media_path:
            return False, None
            
        media_path_norm = self.normalize_path(media_path)
        media_name = os.path.basename(media_path_norm)
        media_name_clean = self.extract_title_clean(media_name)
        
        torrent_files = torrent.get("files", [])
        if not torrent_files:
            return False, None
        
        # Obtenir save_path et content_path pour construire les chemins complets des fichiers
        save_path = torrent.get("save_path", "")
        content_path = torrent.get("content_path", "")
        torrent_name = torrent.get("name", "")
        
        # Base path pour les fichiers relatifs
        base_path = None
        if content_path:
            base_path = content_path
        elif save_path and torrent_name:
            base_path = os.path.join(save_path, torrent_name).replace("\\", "/")
        elif save_path:
            base_path = save_path.replace("\\", "/")
        
        for torrent_file in torrent_files:
            if not torrent_file:
                continue
            
            # Construire le chemin complet du fichier
            torrent_file_str = str(torrent_file)
            torrent_file_full = torrent_file_str
            
            # Si le fichier est relatif, le combiner avec base_path
            if not os.path.isabs(torrent_file_str) and base_path:
                torrent_file_full = os.path.join(base_path, torrent_file_str).replace("\\", "/")
                torrent_file_full = torrent_file_full.replace("//", "/")
            
            torrent_file_norm = self.normalize_path(torrent_file_full)
            torrent_file_name = os.path.basename(torrent_file_norm)
            
            # Match exact du nom de fichier
            if media_name == torrent_file_name:
                if self.debug:
                    logger.debug(f"exact_filename_match: media_name={media_name}, torrent_file={torrent_file_name}")
                return True, "exact_filename_match"
            
            # Match du chemin complet (exact)
            if media_path_norm == torrent_file_norm:
                if self.debug:
                    logger.debug(f"exact_file_path_match: media={media_path_norm[:80]}, torrent_file={torrent_file_norm[:80]}")
                return True, "file_path_match"
            
            # Match partiel (un chemin est contenu dans l'autre)
            if media_path_norm in torrent_file_norm or torrent_file_norm in media_path_norm:
                if self.debug:
                    logger.debug(f"partial_file_path_match: media={media_path_norm[:80]}, torrent_file={torrent_file_norm[:80]}")
                return True, "file_path_match"
            
            # Match partiel du nom nettoyé
            if media_name_clean and len(media_name_clean) > 3:
                torrent_file_clean = self.extract_title_clean(torrent_file_name)
                if media_name_clean in torrent_file_clean or torrent_file_clean in media_name_clean:
                    # Vérifier aussi la similarité (au moins 80% des caractères communs)
                    common_chars = sum(1 for c in media_name_clean if c in torrent_file_clean)
                    if len(media_name_clean) > 0 and common_chars / len(media_name_clean) >= 0.8:
                        if self.debug:
                            logger.debug(f"filename_partial_match: media_clean={media_name_clean[:50]}, torrent_clean={torrent_file_clean[:50]}")
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
            if self.debug:
                logger.debug("torrent_matching_skipped", 
                           reason="no_path_or_torrents",
                           has_path=bool(media_path),
                           has_torrents=bool(all_torrents))
            return []
        
        matching_hashes = []
        media_path_norm = self.normalize_path(media_path)
        
        if self.debug:
            logger.info(
                "torrent_matching_start",
                media_path=media_path_norm[:100],
                media_title=media_title,
                total_torrents=len(all_torrents),
                media_path_original=media_path[:100] if media_path else None
            )
            
            # Log quelques exemples de torrents pour debug
            sample_torrents = all_torrents[:3]
            for idx, t in enumerate(sample_torrents):
                logger.debug("sample_torrent_for_matching",
                           index=idx,
                           hash=t.get("hash", "")[:8] if t.get("hash") else "N/A",
                           name=t.get("name", "")[:50] if t.get("name") else "N/A",
                           content_path=t.get("content_path", "")[:80] if t.get("content_path") else "N/A",
                           save_path=t.get("save_path", "")[:80] if t.get("save_path") else "N/A",
                           files_count=len(t.get("files", [])))
        
        for idx, torrent in enumerate(all_torrents):
            matched = False
            match_reason = None
            
            # Vérifier que le torrent a un hash valide
            torrent_hash = torrent.get("hash")
            if not torrent_hash:
                if self.debug and idx < 5:
                    logger.debug(f"Torrent {idx} has no hash, keys: {list(torrent.keys())}")
                continue
            
            # Stratégie 1: Chemin exact (le plus fiable)
            matched, match_reason = self.match_by_exact_path(media_path, torrent)
            if matched:
                matching_hashes.append(torrent_hash)
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent_hash[:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50],
                        content_path=torrent.get("content_path", "")[:100],
                        save_path=torrent.get("save_path", "")[:100],
                        media_path_norm=media_path_norm[:100]
                    )
                continue
            
            # Stratégie 2: Fichiers dans le torrent
            matched, match_reason = self.match_by_torrent_files(media_path, torrent)
            if matched:
                matching_hashes.append(torrent_hash)
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent_hash[:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
                continue
            
            # Stratégie 3: Nom du torrent
            matched, match_reason = self.match_by_torrent_name(media_path, media_title, torrent)
            if matched:
                matching_hashes.append(torrent_hash)
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent_hash[:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
                continue
            
            # Stratégie 4: Année + titre
            matched, match_reason = self.match_by_year_and_title(media_path, media_title, torrent)
            if matched:
                matching_hashes.append(torrent_hash)
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent_hash[:8],
                        reason=match_reason,
                        torrent_name=torrent.get("name", "")[:50]
                    )
                continue
            
            # Stratégie 5: Parties du chemin (dernier recours)
            matched, match_reason = self.match_by_path_parts(media_path, torrent)
            if matched:
                matching_hashes.append(torrent_hash)
                if self.debug and len(matching_hashes) <= 10:
                    logger.info(
                        "torrent_matched",
                        hash=torrent_hash[:8],
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

