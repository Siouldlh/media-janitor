# Fix: SQLite unable to open database file

## Erreur : `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file`

Cette erreur signifie que SQLite ne peut pas créer ou écrire dans le fichier de base de données.

## Causes possibles

1. **Permissions insuffisantes** : Le container n'a pas les droits d'écriture sur `/data`
2. **Dossier inexistant** : Le dossier `./data` n'existe pas sur l'hôte
3. **Volume non monté** : Le volume Docker n'est pas correctement monté

## Solution rapide

### Sur votre NAS :

```bash
# 1. Aller dans le dossier du projet
cd /chemin/vers/media-janitor

# 2. Créer le dossier data avec les bonnes permissions
mkdir -p data
chmod 777 data

# 3. Vérifier que le volume est bien monté dans docker-compose.ghcr.yml
# Doit avoir : - ./data:/data

# 4. Redémarrer le container
docker-compose -f docker-compose.ghcr.yml down
docker-compose -f docker-compose.ghcr.yml up -d

# 5. Vérifier les logs
docker-compose -f docker-compose.ghcr.yml logs -f
```

### Vérification des permissions

```bash
# Vérifier que le dossier existe
ls -la data/

# Vérifier les permissions (doit être rwx pour tous ou au moins pour le user Docker)
ls -ld data/

# Si nécessaire, corriger les permissions
chmod 777 data
```

### Si vous utilisez un chemin absolu

Si votre data est ailleurs (ex: `/DATA/AppData/media-janitor/data`), modifiez le docker-compose :

```yaml
volumes:
  - /DATA/AppData/media-janitor/config:/config:ro
  - /DATA/AppData/media-janitor/data:/data
```

Et créez le dossier :

```bash
mkdir -p /DATA/AppData/media-janitor/data
chmod 777 /DATA/AppData/media-janitor/data
```

## Structure attendue

```
media-janitor/
├── config/
│   └── config.yaml
├── data/                    ← CE DOSSIER DOIT EXISTER ET ÊTRE ACCESSIBLE EN ÉCRITURE
│   └── media_janitor.db     ← Créé automatiquement
└── docker-compose.ghcr.yml
```

## Vérification après correction

Les logs doivent afficher :

```
Initializing database at: /data/media_janitor.db
Database initialized successfully
Application startup complete
```

## Alternative : Utiliser un chemin dans /tmp (temporaire)

Si le problème persiste, vous pouvez temporairement utiliser `/tmp` :

```yaml
environment:
  - DATA_DIR=/tmp/data
```

Mais attention : les données seront perdues au redémarrage du container. Utilisez uniquement pour tester.

