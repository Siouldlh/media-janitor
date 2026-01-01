# Matching Tautulli ↔ Radarr/Sonarr

## Vue d'ensemble

Media Janitor utilise **Tautulli comme source de vérité unique** pour l'historique de visionnage (watch history). Les inventaires de médias proviennent de **Radarr (films)** et **Sonarr (séries)**.

## Flux de données

```
Radarr (movies inventory)
    ↓
MediaItem (tmdb_id, path, size, etc.)
    ↓
Tautulli watch map (tmdb_id → watch stats)
    ↓
MediaItem enrichi (last_viewed_at, view_count, never_watched)
    ↓
Rules Engine (évaluation des règles de suppression)
```

## Matching Films (Radarr ↔ Tautulli)

### Identifiant principal : TMDb ID

**Stratégie** :
1. **TMDb ID** (prioritaire) : Matching direct par `tmdb_id`
   - Radarr fournit `tmdbId` pour chaque film
   - Tautulli stocke les GUIDs dans l'historique, incluant `tmdb://12345`
   - Extraction du TMDb ID depuis les GUIDs Tautulli

2. **Fallback** : Si TMDb ID non disponible
   - Le film est traité comme "never watched"
   - Utilisation de `added_days` depuis Radarr pour les règles

### Exemple

```python
# Radarr movie
movie_data = {
    "tmdbId": 12345,
    "title": "The Matrix",
    "path": "/media/movies/The Matrix (1999)"
}

# Tautulli watch map
watch_map = {
    12345: {
        "last_watched_at": datetime(2025, 12, 1),
        "view_count": 3,
        "last_user": "john",
        "never_watched": False
    }
}

# MediaItem enrichi
item.last_viewed_at = datetime(2025, 12, 1)
item.view_count = 3
item.never_watched = False
item.metadata["watch_source"] = "Tautulli"
```

## Matching Séries (Sonarr ↔ Tautulli)

### Identifiant principal : TVDb ID

**Stratégie** :
1. **TVDb ID** (prioritaire) : Matching direct par `tvdb_id`
   - Sonarr fournit `tvdbId` pour chaque série
   - Tautulli stocke les GUIDs dans l'historique, incluant `tvdb://12345`
   - Extraction du TVDb ID depuis les GUIDs Tautulli

2. **Fallback** : Si TVDb ID non disponible
   - TMDb ID (si disponible)
   - Sinon : titre + année (moins fiable)
   - Si aucun match : traité comme "never watched"

### Exemple

```python
# Sonarr series
series_data = {
    "tvdbId": 78901,
    "tmdbId": 45678,
    "title": "Breaking Bad",
    "path": "/media/series/Breaking Bad"
}

# Tautulli watch map (série entière)
series_watch_map = {
    78901: {
        "last_watched_at": datetime(2025, 11, 15),
        "view_count": 62,  # Total épisodes vus
        "last_user": "jane",
        "never_watched": False
    }
}

# MediaItem enrichi
item.last_viewed_at = datetime(2025, 11, 15)
item.view_count = 62
item.never_watched = False
item.metadata["watch_source"] = "Tautulli"
```

## Matching Épisodes (Sonarr ↔ Tautulli)

### Identifiant : (TVDb ID, Season, Episode)

**Stratégie** :
1. **Clé composite** : `(tvdb_id, season_num, episode_num)`
   - Sonarr fournit les épisodes avec `seasonNumber` et `episodeNumber`
   - Tautulli stocke `season_num` et `episode_num` dans l'historique
   - Matching exact par clé composite

2. **Agrégation série** : Les épisodes sont agrégés pour la série
   - `view_count` = somme des épisodes vus
   - `last_watched_at` = date la plus récente parmi tous les épisodes

### Exemple

```python
# Tautulli episode watch map
episode_watch_map = {
    (78901, 1, 1): {
        "last_watched_at": datetime(2025, 10, 1),
        "view_count": 1,
        "never_watched": False
    },
    (78901, 1, 2): {
        "last_watched_at": datetime(2025, 10, 2),
        "view_count": 1,
        "never_watched": False
    }
}

# Agrégation pour la série
series_watch_map[78901] = {
    "last_watched_at": datetime(2025, 10, 2),  # Plus récent
    "view_count": 2,  # Somme
    "never_watched": False
}
```

## Gestion des cas limites

### 1. Pas de données Tautulli

**Comportement** :
- `never_watched = True`
- `view_count = 0`
- `last_viewed_at = None`
- `metadata["watch_source"] = "Tautulli (never watched)"`

**Règles** :
- Utilisation de `added_days` depuis Radarr/Sonarr
- Si `added_days >= if_never_watched_use_added_days` → candidat à suppression

### 2. Tautulli indisponible

**Comportement** :
- Scan partiel (Radarr/Sonarr fonctionnent)
- Tous les items traités comme "never watched"
- Logs d'erreur mais scan continue

### 3. IDs manquants

**Films** :
- Si `tmdb_id` manquant dans Radarr → pas de matching Tautulli
- Traité comme "never watched"

**Séries** :
- Si `tvdb_id` manquant → fallback sur `tmdb_id`
- Si les deux manquants → traité comme "never watched"

## Métadonnées ajoutées

Chaque MediaItem enrichi avec Tautulli contient :

```python
item.metadata = {
    "watch_source": "Tautulli",  # ou "Tautulli (never watched)"
    "last_watched_user": "john",  # Dernier utilisateur ayant vu
    # ... autres métadonnées Radarr/Sonarr
}
```

## Performance

- **Tautulli watch maps** : Récupérés une seule fois au début du scan
- **Matching** : O(1) lookup par ID (dict)
- **Pas de requêtes multiples** : Tous les historiques chargés en une fois

## Logs

Les logs structurés incluent :
- `fetching_movie_watch_map` : Début récupération films
- `movie_watch_map_fetched` : Fin avec count
- `fetching_episode_watch_map` : Début récupération épisodes
- `episode_watch_map_fetched` : Fin avec count
- `fetching_series_watch_map` : Début agrégation séries
- `series_watch_map_fetched` : Fin avec count

