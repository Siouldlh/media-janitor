# Fix: Assets en chemins relatifs (problème proxy NAS)

## Problème

Lors de l'accès via le proxy du NAS, les assets sont chargés avec des URLs absolues :
- ❌ `http://10.244.0.1:8099/assets/index-*.js` (bloqué, MIME text/html)
- ✅ `./assets/index-*.js` (chemin relatif, fonctionne)

## Corrections apportées

### 1. Vite config (`frontend/vite.config.js`)
- Ajout de `base: './'` pour forcer les chemins relatifs

### 2. FastAPI (`app/main.py`)
- Montage de `/assets` AVANT le fallback SPA
- Vérification que les assets ne passent pas par le fallback

## Commandes pour rebuild et push

### 1. Push vers GitHub (déclenche le rebuild automatique)

```bash
git push origin master
```

Le workflow GitHub Actions va automatiquement :
- Build le frontend avec `base: './'`
- Build l'image Docker
- Push vers `ghcr.io/siouldlh/media-janitor:latest`

### 2. Vérifier le build sur GitHub

1. Allez sur : https://github.com/Siouldlh/media-janitor/actions
2. Vérifiez que le workflow "Build and Push to GHCR" réussit
3. Attendez 3-5 minutes

### 3. Sur votre NAS - Pull et redémarrer

```bash
# Pull la nouvelle image
docker-compose -f docker-compose.ghcr.yml pull

# Redémarrer
docker-compose -f docker-compose.ghcr.yml down
docker-compose -f docker-compose.ghcr.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.ghcr.yml logs -f
```

## Vérification

Après le redéploiement :

1. Accédez à l'app via votre NAS
2. Ouvrez les DevTools (F12) → Network
3. Vérifiez que les assets sont chargés avec des chemins relatifs :
   - ✅ `./assets/index-abc123.js`
   - ✅ `./assets/index-abc123.css`
   - ❌ Plus de `http://10.244.0.1:8099/assets/...`

4. La page ne doit plus être blanche, les assets doivent se charger correctement

## Build local (optionnel, pour tester)

Si vous voulez tester localement avant de push :

```bash
# Build le frontend
cd frontend
npm install
npm run build

# Vérifier que index.html utilise des chemins relatifs
cat dist/index.html | grep assets
# Doit afficher : <script type="module" src="./assets/...">

# Build l'image Docker
cd ..
docker build -f docker/Dockerfile -t media-janitor:test .

# Tester
docker run -p 8099:8099 -v $(pwd)/config:/config:ro -v $(pwd)/data:/data media-janitor:test
```

## Résumé

- ✅ **Vite config** : `base: './'` ajouté
- ✅ **FastAPI** : `/assets` monté avant le fallback SPA
- ✅ **Dockerfile** : Déjà correct (build frontend + copy dist)

Après push → attendre GitHub Actions → pull sur NAS → restart → ça devrait fonctionner !

