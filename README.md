# Media Janitor

Application pour automatiser le nettoyage des médias (films/séries) non regardés depuis X jours, avec intégration Plex, Radarr, Sonarr, Overseerr et qBittorrent.

## Fonctionnalités

- **Scan automatique** : Collecte des données depuis tous les services
- **Matching cross-services** : Unification des médias par TMDb/TVDb ID ou titre+année
- **Moteur de règles** : Suppression basée sur les jours depuis dernier visionnage
- **Garde-fous** : Protection via tags, exclusions, Overseerr requests
- **UI de sélection** : Interface pour sélectionner/désélectionner les items avant suppression
- **Exécution sécurisée** : Ordre garanti (qBittorrent → Radarr/Sonarr → Plex)
- **Gestion cross-seed** : Détection et suppression de tous les torrents liés
- **Scheduler intégré** : Scans automatiques configurables

## Prérequis

- Docker et docker-compose
- Accès réseau aux services : Plex, Radarr, Sonarr, Overseerr, qBittorrent

## Installation

1. Clonez le repository :
```bash
git clone <repository-url>
cd movie-cycler
```

2. Créez le fichier de configuration :
```bash
cp config.example.yaml config/config.yaml
```

3. Éditez `config/config.yaml` avec vos paramètres :
```yaml
plex:
  url: "http://plex:32400"
  token: "VOTRE_TOKEN_PLEX"

radarr:
  url: "http://radarr:7878"
  api_key: "VOTRE_CLE_RADARR"

# ... etc
```

4. Créez le dossier de données :
```bash
mkdir -p data
```

5. Lancez avec docker-compose :
```bash
docker-compose up -d
```

L'application sera accessible sur http://localhost:8099

## Configuration

### Fichier config.yaml

Le fichier `config/config.yaml` contient toute la configuration :

- **Plex** : URL et token
- **Radarr** : URL, API key, tags protégés
- **Sonarr** : URL, API key, tags protégés
- **Overseerr** : URL, API key, règles de protection
- **qBittorrent** : URL, credentials, catégories protégées
- **Rules** : Règles de suppression (jours, exceptions)
- **Scheduler** : Configuration des scans automatiques
- **App** : 
  - `require_confirm_phrase` : Phrase à taper pour confirmer (ex: "DELETE")
  - `excluded_paths` : Chemins à exclure (ex: "/media/downloads/incomplete")
  - `max_items_per_scan` : Limite le nombre d'items par scan (null = pas de limite)

**IMPORTANT** : Assurez-vous que les chemins dans la config correspondent aux chemins montés dans Docker.

Voir `config.example.yaml` pour un exemple complet.

### Variables d'environnement

Vous pouvez surcharger la config YAML avec des variables d'environnement :
- Format : `SERVICE__KEY=value`
- Exemple : `PLEX__URL=http://plex:32400`

## Utilisation

### Interface Web

1. Accédez à http://localhost:8099
2. Cliquez sur "Lancer un scan" pour générer un plan
3. Consultez les onglets "Films" et "Séries" pour voir les candidats
4. Désélectionnez les items que vous voulez garder
5. Cliquez sur "Appliquer" pour exécuter la suppression

### API

L'API REST est disponible sous `/api` :

- `POST /api/scan` : Lance un scan
- `GET /api/plan/{plan_id}` : Récupère un plan
- `PATCH /api/plan/{plan_id}/items` : Met à jour la sélection
- `POST /api/plan/{plan_id}/apply` : Exécute le plan
- `GET /api/runs/{run_id}` : Statut d'une exécution
- `GET /api/diagnostics` : Vérifie les connexions

## Règles de suppression

### Films

- Supprimer si non regardé depuis > N jours (configurable)
- Si jamais regardé : utiliser date d'ajout si disponible

### Séries

- Supprimer épisodes non regardés depuis > N jours
- OU supprimer série entière si inactive depuis > N jours

### Protections

Un média est protégé si :
- Tag "protected" dans Radarr/Sonarr
- Catégorie protégée dans qBittorrent
- Request Overseerr active/récente (< N jours)
- Chemin dans les exclusions

## Ordre d'exécution

Lors de l'application d'un plan, l'ordre est garanti :

1. **qBittorrent** : Suppression de tous les torrents liés (cross-seed)
2. **Radarr/Sonarr** : Suppression via API (fichiers + DB)
3. **Plex** : Rafraîchissement optionnel

Si une étape échoue, les suivantes ne sont pas exécutées (rollback logique).

## Scheduler

Le scheduler peut être activé pour des scans automatiques :

```yaml
scheduler:
  enabled: true
  cadence: "1 day"  # ou "1 hour"
  timezone: "Europe/Paris"
```

Par défaut, les scans sont planifiés à 2h du matin.

## Développement

### Setup local

```bash
# Installer les dépendances Python
pip install -r requirements.txt

# Installer les dépendances frontend
cd frontend
npm install

# Lancer le frontend en dev
npm run dev

# Lancer le backend
uvicorn app.main:app --reload
```

### Build frontend

```bash
cd frontend
npm run build
```

## Structure du projet

```
media_janitor/
├── app/              # Code Python (FastAPI)
│   ├── api/          # Routes API
│   ├── services/     # Clients API (Plex, Radarr, etc.)
│   ├── core/         # Logique métier (matching, rules, planner, executor)
│   └── db/           # Models SQLAlchemy
├── frontend/          # Application React
├── docker/            # Dockerfile
├── config.example.yaml
└── docker-compose.yml
```

## Sécurité

- **Dry-run par défaut** : Les plans sont en mode DRAFT, l'application est explicite
- **Confirmation requise** : Modal de confirmation avant apply
- **Phrase de confirmation** : Optionnel, peut exiger une phrase (ex: "DELETE") pour confirmer
- **qBittorrent sécurisé** : Suppression des torrents SANS suppression des fichiers (deleteFiles=false)
- **Exclusions** : Chemins et tags protégés empêchent la suppression
- **Logs détaillés** : Audit trail complet dans la DB
- **Rollback logique** : Pas de suppression si qBittorrent échoue
- **Cross-seed** : Détection et suppression de tous les torrents liés avant suppression fichiers

## Limitations

- SQLite pour la base de données (suffisant pour usage personnel)
- Pas d'authentification sur l'UI (à ajouter si besoin)
- Matching par titre+année peut être imprécis (privilégier les IDs)

## Support

Pour les problèmes ou questions, ouvrez une issue sur le repository.

## Licence

MIT

