# Configuration Setup - Résolution erreur FileNotFoundError

## Erreur : `FileNotFoundError: Config file not found: /config/config.yaml`

Cette erreur signifie que le fichier de configuration n'est pas trouvé dans le container Docker.

## Solution rapide

### Sur votre NAS, avant de lancer le container :

```bash
# 1. Aller dans le dossier du projet
cd /chemin/vers/media-janitor

# 2. Créer le dossier config s'il n'existe pas
mkdir -p config

# 3. Copier l'exemple de configuration
cp config.example.yaml config/config.yaml

# 4. Éditer avec vos paramètres
nano config/config.yaml
# ou
vi config/config.yaml
```

### Vérifier que le volume est bien monté

Dans votre `docker-compose.ghcr.yml`, vous devez avoir :

```yaml
volumes:
  - ./config:/config:ro
```

Cela monte le dossier `./config` (relatif au docker-compose.yml) vers `/config` dans le container.

### Structure de dossiers attendue

```
media-janitor/
├── config/
│   └── config.yaml          ← CE FICHIER DOIT EXISTER
├── data/                    ← Créé automatiquement
├── docker-compose.ghcr.yml
└── config.example.yaml
```

## Vérification

```bash
# Vérifier que le fichier existe
ls -la config/config.yaml

# Vérifier le contenu (doit être un YAML valide)
cat config/config.yaml
```

## Si vous utilisez un chemin absolu

Si votre config est ailleurs (ex: `/DATA/AppData/media-janitor/config`), modifiez le docker-compose :

```yaml
volumes:
  - /DATA/AppData/media-janitor/config:/config:ro
  - /DATA/AppData/media-janitor/data:/data
```

Et ajustez `CONFIG_PATH` si nécessaire :

```yaml
environment:
  - CONFIG_PATH=/config/config.yaml
```

## Après avoir créé config.yaml

```bash
# Redémarrer le container
docker-compose -f docker-compose.ghcr.yml down
docker-compose -f docker-compose.ghcr.yml up -d

# Vérifier les logs (ne doit plus avoir FileNotFoundError)
docker-compose -f docker-compose.ghcr.yml logs -f
```

## Contenu minimal de config.yaml

Au minimum, vous devez avoir :

```yaml
plex:
  url: "http://192.168.1.59:32400"
  token: "VOTRE_TOKEN"

radarr:
  url: "http://192.168.1.59:7878"
  api_key: "VOTRE_CLE"

# ... etc (voir config.example.yaml)
```

Même si certains services ne sont pas configurés, vous pouvez laisser les sections vides ou commentées.

