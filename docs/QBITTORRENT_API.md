# Documentation API qBittorrent

## Endpoints utilisés dans Media Janitor

### 1. Authentification
- **Endpoint**: `/api/v2/auth/login`
- **Méthode**: POST
- **Bibliothèque**: `qbittorrent-api` gère automatiquement l'authentification via `client.auth_log_in()`

### 2. Récupérer tous les torrents
- **Endpoint**: `/api/v2/torrents/info`
- **Méthode**: GET
- **Bibliothèque**: `client.torrents_info()`
- **Retourne**: Liste d'objets Torrent avec:
  - `hash`: Hash du torrent (identifiant unique)
  - `name`: Nom du torrent
  - `save_path`: Chemin de sauvegarde
  - `content_path`: Chemin du contenu (peut être None selon la version)
  - `category`: Catégorie du torrent
  - `tags`: Tags du torrent (string séparée par virgules)
  - `state`: État du torrent (downloading, seeding, etc.)
  - `size`: Taille du torrent en bytes

### 3. Récupérer les fichiers d'un torrent
- **Endpoint**: `/api/v2/torrents/files`
- **Méthode**: GET
- **Paramètres**: `hash` (hash du torrent)
- **Bibliothèque**: `client.torrents_files(torrent_hash=hash)`
- **Retourne**: Liste de fichiers avec:
  - Format peut varier: dict, objet, ou NamedTuple
  - Champs possibles: `name`, `path`, `size`, `progress`
  - **Important**: Le format peut être différent selon la version de qBittorrent

### 4. Supprimer des torrents
- **Endpoint**: `/api/v2/torrents/delete`
- **Méthode**: DELETE
- **Paramètres**: 
  - `hashes`: Liste de hashs (séparés par `|` ou `%7C`)
  - `deleteFiles`: bool (true pour supprimer aussi les fichiers)
- **Bibliothèque**: `client.torrents_delete(delete_files=True, torrent_hashes=hashes)`

## Structure des données dans Media Janitor

### Format Torrent (après transformation)
```python
{
    "hash": str,              # Hash unique du torrent
    "name": str,              # Nom du torrent
    "save_path": str,         # Chemin de sauvegarde
    "content_path": str,      # Chemin du contenu (construit si absent)
    "category": str,          # Catégorie
    "tags": List[str],        # Liste de tags
    "state": str,             # État
    "size": int,              # Taille en bytes
    "files": List[str]        # Liste des chemins de fichiers
}
```

### Construction de `content_path`

Le code utilise 3 méthodes pour construire `content_path`:

1. **Attribut direct** (si disponible):
   ```python
   content_path = torrent.content_path
   ```

2. **save_path + name**:
   ```python
   content_path = os.path.join(save_path, name)
   ```

3. **Depuis le premier fichier**:
   ```python
   content_path = os.path.dirname(first_file)
   ```

## Matching des torrents

Le matching utilise plusieurs stratégies (voir `app/core/torrent_matcher.py`):

1. **Matching exact par chemin**: Compare `content_path` ou `save_path + name` avec le chemin média
2. **Matching par fichiers**: Compare les fichiers du torrent avec le chemin média
3. **Matching par nom**: Compare le nom du torrent avec le titre du média
4. **Matching par année + titre**: Extrait l'année et compare avec le titre
5. **Matching par parties du chemin**: Compare les dossiers du chemin

## Notes importantes

- **Normalisation des chemins**: Tous les chemins sont normalisés (backslashes → slashes, lowercase) pour le matching
- **Cross-seed**: Plusieurs torrents peuvent pointer vers le même média (cross-seed)
- **Format des fichiers**: Le format retourné par `torrents_files` peut varier, le code gère dict, objet, et tuple
- **Version de l'API**: Le code utilise l'API v2 de qBittorrent (compatible avec qBittorrent 4.1+)

## Références

- Documentation officielle: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
- Bibliothèque Python: https://github.com/rmartin16/qbittorrent-api

