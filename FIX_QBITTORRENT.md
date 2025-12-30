# Fix: ModuleNotFoundError qbittorrentapi

## Problème identifié

**Erreur :** `ModuleNotFoundError: No module named 'qbittorrentapi'`

**Cause :** Le package dans `requirements.txt` était incorrect :
- ❌ `python-qbittorrent==0.4.2` (package incorrect ou obsolète)
- ✅ `qbittorrent-api==2024.3.50` (package correct)

Le package pip `qbittorrent-api` fournit le module Python `qbittorrentapi` (sans tiret).

## Corrections apportées

1. **requirements.txt** : Remplacé `python-qbittorrent` par `qbittorrent-api==2024.3.50`
2. **Dockerfile** : Ajout d'un check de vérification après installation pour détecter ce type d'erreur en amont

## Commandes pour rebuild et redéployer

### 1. Push vers GitHub (déclenche le build automatique)

```bash
git push origin master
```

Le workflow GitHub Actions va automatiquement :
- Build l'image Docker avec les nouvelles dépendances
- Push vers `ghcr.io/siouldlh/media-janitor:latest`

### 2. Vérifier le build sur GitHub

1. Allez sur : https://github.com/Siouldlh/media-janitor/actions
2. Vérifiez que le workflow "Build and Push to GHCR" se termine avec succès
3. Attendez 2-3 minutes pour que l'image soit disponible

### 3. Sur votre NAS - Pull et redémarrage

```bash
# Aller dans le dossier du projet
cd /chemin/vers/media-janitor

# Pull la nouvelle image
docker-compose -f docker-compose.ghcr.yml pull

# Redémarrer le container
docker-compose -f docker-compose.ghcr.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.ghcr.yml logs -f
```

### Alternative : Commandes Docker directes

```bash
# Pull l'image
docker pull ghcr.io/siouldlh/media-janitor:latest

# Arrêter l'ancien container
docker stop media-janitor
docker rm media-janitor

# Relancer avec la nouvelle image
docker-compose -f docker-compose.ghcr.yml up -d

# Vérifier les logs
docker logs -f media-janitor
```

## Vérification que ça fonctionne

Une fois redémarré, vérifiez que l'application démarre sans erreur :

```bash
# Voir les logs
docker logs media-janitor

# Vérifier que le module est bien importé (pas d'erreur qbittorrentapi)
# Vous devriez voir "Application startup complete" sans ModuleNotFoundError
```

## Build local (optionnel, pour tester)

Si vous voulez tester localement avant de push :

```bash
# Build local
docker build -f docker/Dockerfile -t media-janitor:test .

# Tester que le module est installé
docker run --rm media-janitor:test python -c "import qbittorrentapi; print(qbittorrentapi.__version__)"
```

## Résumé

- ✅ **Fichier corrigé** : `requirements.txt` (python-qbittorrent → qbittorrent-api)
- ✅ **Dockerfile amélioré** : Vérification automatique après installation
- ✅ **Commit créé** : Prêt à être pushé
- ✅ **Workflow GHCR** : Se déclenchera automatiquement au push

Après le push, attendez 3-5 minutes puis pull/restart sur votre NAS.

