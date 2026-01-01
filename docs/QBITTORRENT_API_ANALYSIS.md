# Analyse API qBittorrent - Problème de détection des torrents

## Endpoint `/api/v2/torrents/info`

### Réponse attendue (selon documentation officielle)

```json
[
  {
    "hash": "string",
    "name": "string",
    "save_path": "string",
    "content_path": "string",  // Peut être absent selon version
    "category": "string",
    "tags": "string",  // Séparé par virgules
    "state": "string",
    "size": 0,
    ...
  }
]
```

### Points importants

1. **`content_path`** : Peut ne pas exister dans toutes les versions de qBittorrent
2. **`save_path`** : Toujours présent, chemin de sauvegarde
3. **`name`** : Nom du torrent (dossier ou fichier racine)
4. **Chemin complet** : `save_path` + `name` = chemin réel du contenu

## Bibliothèque `qbittorrent-api`

La bibliothèque Python `qbittorrent-api` retourne des objets avec des attributs :
- `torrent.hash` : Hash du torrent
- `torrent.name` : Nom du torrent
- `torrent.save_path` : Chemin de sauvegarde
- `torrent.content_path` : Peut exister ou non selon version
- `torrent.size` : Taille
- `torrent.category` : Catégorie
- `torrent.tags` : Tags (string séparée par virgules)
- `torrent.state` : État

## Problèmes potentiels

1. **`content_path` manquant** : Doit être construit depuis `save_path + name`
2. **Normalisation des chemins** : Windows vs Linux, case sensitivity
3. **Matching** : Les chemins doivent être comparés de manière robuste

## Solution recommandée

1. Toujours construire `content_path` depuis `save_path + name`
2. Normaliser tous les chemins (lowercase, slashes unifiés)
3. Comparer avec plusieurs stratégies (exact, parent/enfant, fichiers)

