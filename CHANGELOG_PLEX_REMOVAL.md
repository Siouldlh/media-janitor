# Changelog : Suppression de la dépendance PlexAPI

## Résumé

Suppression de la dépendance à PlexAPI. **Tautulli est maintenant la source de vérité unique** pour l'historique de visionnage (watch history). Les inventaires de médias proviennent uniquement de **Radarr (films)** et **Sonarr (séries)**.

## Modifications

### 1. Configuration

**Fichier** : `app/config.py`

- Ajout de `plex.enabled: bool = False` (désactivé par défaut)
- Ajout de `tautulli.enabled: bool = True` (activé par défaut)
- `plex.url` et `plex.token` sont maintenant optionnels

**Fichier** : `config.example.yaml`

- Mise à jour avec `plex.enabled: false` par défaut
- Documentation mise à jour pour indiquer que Tautulli est obligatoire

### 2. Dépendances

**Fichier** : `requirements.txt`

- ❌ **Supprimé** : `plexapi==4.16.0`
- ✅ **Conservé** : Toutes les autres dépendances

**Fichier** : `docker/Dockerfile`

- Retrait de la vérification `import plexapi` dans les tests de dépendances

### 3. Services

**Fichier** : `app/services/tautulli.py` (REFONTE COMPLÈTE)

**Nouvelles méthodes** :
- `get_movie_watch_map()` → `Dict[int, Dict]` (TMDb ID → watch stats)
- `get_episode_watch_map()` → `Dict[Tuple[int, int, int], Dict]` ((TVDb ID, season, episode) → watch stats)
- `get_series_watch_map()` → `Dict[int, Dict]` (TVDb ID → watch stats agrégés)

**Matching** :
- Films : TMDb ID (prioritaire)
- Séries : TVDb ID (prioritaire), fallback TMDb ID
- Épisodes : Clé composite (TVDb ID, season, episode)

**Fichier** : `app/services/plex.py`

- ⚠️ **Conservé mais non utilisé** : Le fichier existe toujours mais n'est jamais instancié si `plex.enabled=false`
- Peut être supprimé dans une version future si besoin

### 4. Planner

**Fichier** : `app/core/planner.py`

**Changements majeurs** :
- ❌ **Supprimé** : Import et utilisation de `PlexService`
- ✅ **Ajouté** : Import et utilisation de `TautulliService`
- ✅ **Nouveau flux** :
  1. Récupération Tautulli watch maps (films, épisodes, séries)
  2. Récupération Radarr movies
  3. Récupération Sonarr series
  4. Enrichissement MediaItems avec Tautulli watch stats
  5. Unification (plus de Plex items)

**Enrichissement MediaItems** :
```python
# Films
if tautulli_service and item.tmdb_id:
    watch_stats = movie_watch_map.get(item.tmdb_id)
    if watch_stats:
        item.last_viewed_at = watch_stats["last_watched_at"]
        item.view_count = watch_stats["view_count"]
        item.never_watched = False
        item.metadata["watch_source"] = "Tautulli"
    else:
        item.never_watched = True
        item.metadata["watch_source"] = "Tautulli (never watched)"
```

### 5. API Routes

**Fichier** : `app/api/routes.py`

- ❌ **Supprimé** : Import de `PlexService`
- ✅ **Ajouté** : Import de `TautulliService`
- **Endpoint `/api/diagnostics`** :
  - ❌ Supprimé : Test Plex
  - ✅ Ajouté : Test Tautulli
- **Endpoint `/api/config`** :
  - ❌ Supprimé : Section `plex`
  - ✅ Ajouté : Section `tautulli` avec `enabled`

**Fichier** : `app/api/models.py`

- **DiagnosticsResponse** : `plex` → `tautulli`

### 6. Executor

**Fichier** : `app/core/executor.py`

- ❌ **Supprimé** : Import et utilisation de `PlexService`
- ❌ **Supprimé** : Logique de refresh Plex library (non nécessaire)

### 7. UI

**Fichier** : `frontend/src/components/PlanItemRow.jsx`

- ✅ **Ajouté** : Affichage de la source watch history dans les détails
  - "Source watch history: Tautulli" ou "Tautulli (never watched)"
  - Affichage du dernier utilisateur si disponible

### 8. Documentation

**Fichier** : `docs/TAUTULLI_MATCHING.md` (NOUVEAU)

- Documentation complète du matching Tautulli ↔ Radarr/Sonarr
- Stratégies de matching par type (films, séries, épisodes)
- Gestion des cas limites
- Exemples de code

**Fichier** : `AUDIT.md`

- Note ajoutée indiquant que PlexAPI a été supprimé

## Migration

### Pour les utilisateurs existants

1. **Mettre à jour `config.yaml`** :
```yaml
plex:
  enabled: false  # Désactiver Plex

tautulli:
  enabled: true   # Activer Tautulli (obligatoire)
  url: "http://192.168.1.59:8181"
  api_key: "TAUTULLI_API_KEY"
```

2. **Vérifier que Tautulli est accessible** :
   - Tester `/api/diagnostics` → `tautulli.connected` doit être `true`

3. **Lancer un scan** :
   - Les items doivent maintenant afficher "Source: Tautulli" dans les détails

## Tests manuels

### ✅ Checklist

- [ ] `/api/diagnostics` passe sans Plex configuré
- [ ] `/api/diagnostics` affiche `tautulli.connected: true` si Tautulli est configuré
- [ ] `/api/scan` ne fait plus d'appels à Plex
- [ ] Les items vus dans Tautulli apparaissent comme "vus" dans le plan
- [ ] Les items jamais vus affichent "Source: Tautulli (never watched)"
- [ ] Les règles "not watched X days" utilisent les dates Tautulli
- [ ] L'UI affiche la source Tautulli dans les détails des items

## Bénéfices

1. **Simplification** : Une seule source de vérité pour watch history
2. **Performance** : Moins d'appels API (pas de Plex)
3. **Fiabilité** : Tautulli track toutes les sessions, même non marquées "vues" dans Plex
4. **Maintenance** : Moins de dépendances à maintenir

## Notes techniques

- Le fichier `app/services/plex.py` est conservé mais non utilisé
- `plex_rating_key` dans MediaItem est toujours présent mais sera `None`
- Le matching Plex dans `matcher.py` fonctionne toujours mais ne sera jamais appelé (liste vide)

## Prochaines étapes (optionnel)

- Supprimer complètement `app/services/plex.py` si confirmé que Plex n'est plus nécessaire
- Nettoyer `plex_rating_key` du modèle MediaItem si non utilisé ailleurs

