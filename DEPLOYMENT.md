# Instructions de déploiement GHCR

## Vérification du workflow GitHub Actions

### Problèmes identifiés et corrigés

1. **Branche surveillée incorrecte** ❌ → ✅
   - **Problème** : Le workflow surveillait uniquement `main` alors que la branche active est `master`
   - **Correction** : Ajout de `master` dans les branches surveillées

2. **Tag `latest` conditionnel** ❌ → ✅
   - **Problème** : Le tag `latest` n'était créé que si la branche était la branche par défaut sur GitHub
   - **Correction** : Tag `latest` forcé avec `priority=1` pour garantir sa présence à chaque build

3. **Permissions** ✅
   - Déjà correct : `packages: write` présent

4. **Login GHCR** ✅
   - Déjà correct : Utilise `GITHUB_TOKEN` automatique

## Vérification après push

### 1. Vérifier que le workflow s'est exécuté

1. Allez sur https://github.com/Siouldlh/media-janitor
2. Cliquez sur l'onglet **Actions**
3. Vous devriez voir le workflow "Build and Push to GHCR" en cours ou terminé

### 2. Vérifier l'apparition du package

1. Allez sur https://github.com/Siouldlh/media-janitor
2. Cliquez sur l'onglet **Packages** (ou allez directement sur https://github.com/orgs/Siouldlh/packages)
3. Vous devriez voir le package `media-janitor` avec l'image Docker

### 3. Vérifier l'image sur GHCR

L'image devrait être disponible à :
- `ghcr.io/siouldlh/media-janitor:latest`
- `ghcr.io/siouldlh/media-janitor:master` (si push sur master)

### 4. Tester le pull local

```bash
docker pull ghcr.io/siouldlh/media-janitor:latest
```

## Si le package n'apparaît toujours pas

### Vérifications à faire :

1. **Le workflow s'est-il exécuté ?**
   - Vérifier dans l'onglet Actions
   - Vérifier qu'il n'y a pas d'erreurs

2. **Les permissions du repository**
   - Le repository doit être public OU vous devez avoir les permissions packages:write
   - Pour un repo public, le package sera public automatiquement

3. **Première publication**
   - La première fois, il faut parfois attendre quelques minutes
   - Rafraîchir la page Packages

4. **Visibilité du package**
   - Par défaut, les packages sont privés même pour un repo public
   - Il faut aller dans Settings du package et le rendre public si nécessaire

### Rendre le package public (si nécessaire)

1. Allez sur https://github.com/Siouldlh/media-janitor/pkgs/container/media-janitor
2. Cliquez sur **Package settings**
3. Dans **Danger Zone**, cliquez sur **Change visibility** → **Public**

## Utilisation de l'image

Une fois l'image disponible, utilisez `docker-compose.ghcr.yml` :

```bash
docker-compose -f docker-compose.ghcr.yml up -d
```

Ou directement :

```bash
docker run -d \
  -p 8099:8099 \
  -v $(pwd)/config:/config:ro \
  -v $(pwd)/data:/data \
  -e CONFIG_PATH=/config/config.yaml \
  -e DATA_DIR=/data \
  -e TZ=Europe/Paris \
  --name media-janitor \
  ghcr.io/siouldlh/media-janitor:latest
```

