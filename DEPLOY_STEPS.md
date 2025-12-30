# Étapes pour mettre à jour l'image Docker sur le NAS

## ⚠️ IMPORTANT : Le package ne se met PAS à jour automatiquement

Quand vous modifiez `requirements.txt`, il faut :
1. ✅ Push vers GitHub (déclenche le rebuild automatique)
2. ⏳ Attendre que GitHub Actions rebuild l'image (3-5 minutes)
3. 📥 Pull la nouvelle image sur votre NAS
4. 🔄 Redémarrer le container

## Processus complet

### Étape 1 : Vérifier que les changements sont commités

```bash
# Sur votre machine locale
cd /Users/louis/movie-cycler
git status
# Doit afficher "nothing to commit, working tree clean"
```

### Étape 2 : Push vers GitHub

```bash
git push origin master
```

**Cela déclenche automatiquement le workflow GitHub Actions qui va :**
- Rebuild l'image Docker avec le nouveau `requirements.txt`
- Installer `qbittorrent-api` au lieu de `python-qbittorrent`
- Push la nouvelle image vers `ghcr.io/siouldlh/media-janitor:latest`

### Étape 3 : Vérifier que le build est terminé

1. Allez sur : https://github.com/Siouldlh/media-janitor/actions
2. Cliquez sur le dernier workflow "Build and Push to GHCR"
3. Vérifiez qu'il est **vert** (succès) et terminé
4. **ATTENDEZ 2-3 minutes** après la fin du workflow pour que l'image soit disponible

### Étape 4 : Sur votre NAS - Pull la nouvelle image

```bash
# Connectez-vous à votre NAS (SSH ou terminal)
cd /chemin/vers/media-janitor

# Pull la nouvelle image (IMPORTANT : force le pull même si latest existe)
docker-compose -f docker-compose.ghcr.yml pull --ignore-pull-failures

# OU avec Docker directement
docker pull ghcr.io/siouldlh/media-janitor:latest
```

### Étape 5 : Redémarrer le container avec la nouvelle image

```bash
# Arrêter et supprimer l'ancien container
docker-compose -f docker-compose.ghcr.yml down

# Relancer avec la nouvelle image
docker-compose -f docker-compose.ghcr.yml up -d

# Vérifier les logs (devrait démarrer sans erreur qbittorrentapi)
docker-compose -f docker-compose.ghcr.yml logs -f
```

### Alternative : Commandes Docker directes

```bash
# Arrêter le container
docker stop media-janitor

# Supprimer le container (garde les volumes)
docker rm media-janitor

# Pull la nouvelle image
docker pull ghcr.io/siouldlh/media-janitor:latest

# Relancer
docker-compose -f docker-compose.ghcr.yml up -d

# Vérifier les logs
docker logs -f media-janitor
```

## Vérification que ça fonctionne

```bash
# Voir les logs - ne doit PAS avoir "ModuleNotFoundError: No module named 'qbittorrentapi'"
docker logs media-janitor

# Vous devriez voir :
# - "qbittorrentapi version: X.X.X" (dans les logs de build)
# - "Application startup complete"
# - Pas d'erreur d'import
```

## Si vous avez toujours l'erreur

### Vérification 1 : L'image a-t-elle été rebuildée ?

```bash
# Sur votre NAS, vérifier la date de l'image
docker images ghcr.io/siouldlh/media-janitor:latest

# La date doit être récente (après votre push)
```

### Vérification 2 : Le container utilise-t-il la bonne image ?

```bash
# Vérifier quelle image le container utilise
docker inspect media-janitor | grep Image

# Doit afficher "ghcr.io/siouldlh/media-janitor:latest"
```

### Vérification 3 : Forcer le rebuild complet

Si l'image n'a pas été rebuildée correctement :

```bash
# Sur votre NAS
docker rmi ghcr.io/siouldlh/media-janitor:latest

# Pull à nouveau
docker pull ghcr.io/siouldlh/media-janitor:latest

# Redémarrer
docker-compose -f docker-compose.ghcr.yml up -d --force-recreate
```

### Vérification 4 : Le workflow GitHub Actions a-t-il réussi ?

1. Allez sur : https://github.com/Siouldlh/media-janitor/actions
2. Vérifiez que le dernier workflow est **vert** (succès)
3. Si rouge, cliquez dessus et regardez l'erreur
4. Le check dans le Dockerfile doit avoir réussi : "qbittorrentapi version: ..."

## Résumé rapide

```bash
# 1. Push (si pas déjà fait)
git push origin master

# 2. Attendre 3-5 minutes que GitHub Actions termine

# 3. Sur le NAS
docker-compose -f docker-compose.ghcr.yml pull
docker-compose -f docker-compose.ghcr.yml down
docker-compose -f docker-compose.ghcr.yml up -d
docker-compose -f docker-compose.ghcr.yml logs -f
```

