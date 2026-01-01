# Audit Technique - Media Janitor V2

**Date** : Décembre 2025  
**Objectif** : Évaluation complète de l'état actuel du projet avant refonte majeure

**Note** : Depuis la refonte, PlexAPI a été supprimé. Tautulli est maintenant la source de vérité unique pour watch history. Voir `docs/TAUTULLI_MATCHING.md` pour les détails du matching.

---

## 📊 État Actuel

### Versions Actuelles

#### Backend Python
- **Python** : 3.11 (Dockerfile) - ✅ Stable, compatible 3.12
- **fastapi** : 0.104.1 - ⚠️ Obsolète (dernière stable ~0.115+)
- **uvicorn[standard]** : 0.24.0 - ⚠️ Obsolète (dernière stable ~0.32+)
- **httpx** : 0.25.2 - ⚠️ Obsolète (dernière stable ~0.28+)
- **sqlalchemy** : 2.0.23 - ⚠️ Obsolète (dernière stable ~2.0.35+)
- **pydantic** : 2.5.0 - ⚠️ Obsolète (dernière stable ~2.10+)
- **pydantic-settings** : 2.1.0 - ⚠️ À vérifier (dernière stable ~2.6+)
- **qbittorrent-api** : >=2024.3.60 - ✅ Récent
- **plexapi** : 4.15.0 - ⚠️ À vérifier (dernière stable ~4.16+)
- **apscheduler** : 3.10.4 - ⚠️ Obsolète (dernière stable ~3.10.7+)
- **pyyaml** : 6.0.1 - ✅ Stable

#### Frontend JavaScript
- **React** : ^18.2.0 - ⚠️ À mettre à jour (dernière 18.x ~18.3+)
- **react-dom** : ^18.2.0 - ⚠️ À mettre à jour
- **react-router-dom** : ^6.20.0 - ⚠️ À mettre à jour (dernière 6.x ~6.28+)
- **vite** : ^5.0.0 - ⚠️ À mettre à jour (dernière 5.x ~5.4+)
- **react-icons** : ^4.12.0 - ✅ Stable
- **Node.js** : 18-alpine (Dockerfile) - ⚠️ À mettre à jour vers Node 20 LTS

### Architecture Actuelle

**Structure du projet** :
```
app/
├── api/          # Routes FastAPI
├── core/         # Logique métier (planner, matcher, rules, safety, executor)
├── db/           # Base de données SQLite
├── services/     # Clients API (Plex, Radarr, Sonarr, Overseerr, qBittorrent, Tautulli)
└── utils/        # Utilitaires (à créer pour http_client)

frontend/
├── src/
│   ├── components/  # Composants React
│   ├── utils/       # Utilitaires (sorting, filtering)
│   └── api.js       # Client API
```

**Base de données** : SQLite avec SQLAlchemy 2.0
- Tables : Plan, PlanItem, Run, RunItem, Protection
- Pas de système de migrations
- Connexion avec `check_same_thread=False` pour FastAPI

---

## 🚨 Problèmes Critiques

### 1. Matching qBittorrent : 0 torrents trouvés

**Sévérité** : 🔴 CRITIQUE - Bloque la fonctionnalité principale

**Problème** :
- Malgré 2518 torrents disponibles dans qBittorrent, aucun n'est matché avec les médias
- Le matching actuel dans `app/services/qbittorrent.py::find_torrents_for_path()` est trop strict ou mal configuré

**Causes identifiées** :
1. Normalisation des chemins différente entre Radarr/Sonarr et qBittorrent
2. Matching par nom de fichier non fonctionnel
3. Problème de format de chemin (Windows vs Linux)
4. Pas de fallback par hash torrent ou TMDb/TVDb ID

**Impact** : Les torrents ne sont jamais supprimés, même si les médias le sont

**Fichiers concernés** :
- `app/services/qbittorrent.py` (lignes 96-296)
- `app/core/matcher.py` (lignes 209-232)

---

### 2. Erreurs 500 non gérées

**Sévérité** : 🔴 CRITIQUE - Expérience utilisateur dégradée

**Problème** :
- Exceptions non gérées remontent jusqu'à l'utilisateur
- Handler global dans `main.py` mais pas de prévention

**Causes identifiées** :
1. Services non disponibles → pas de fallback gracieux
2. Matching échoué → erreurs silencieuses
3. Base de données → erreurs de connexion non gérées
4. Timeouts HTTP → pas de retries

**Fichiers concernés** :
- `app/main.py` (lignes 94-110)
- `app/api/routes.py` (tous les endpoints)
- `app/services/*.py` (appels HTTP)

---

### 3. Séparation Films/Séries défaillante

**Sévérité** : 🔴 CRITIQUE - Confusion utilisateur

**Problème** :
- Films et séries mélangés dans l'onglet Films
- Onglet Séries ne fonctionne pas correctement
- Barre de sélection disparaît dans l'onglet Séries

**Causes identifiées** :
1. `media_type` pas toujours correctement défini dans `PlanItem`
2. Filtrage incorrect dans `MoviesTab.jsx` et `SeriesTab.jsx`
3. Matching peut mélanger les types

**Fichiers concernés** :
- `app/core/planner.py` (lignes 239-244)
- `frontend/src/components/MoviesTab.jsx`
- `frontend/src/components/SeriesTab.jsx`

---

### 4. Scroll qui remonte lors du décochage

**Sévérité** : 🟠 MAJEUR - UX dégradée

**Problème** :
- Quand on décoche un item, la page remonte en haut
- Perte de contexte pour l'utilisateur

**Causes identifiées** :
1. Re-render complet du composant
2. Pas de sauvegarde de la position de scroll
3. Événements de checkbox non gérés correctement

**Fichiers concernés** :
- `frontend/src/components/MoviesTab.jsx`
- `frontend/src/components/SeriesTab.jsx`
- `frontend/src/components/PlanItemRow.jsx`

---

## ⚠️ Problèmes Majeurs

### 5. Pas de retries sur les appels HTTP

**Sévérité** : 🟠 MAJEUR - Stabilité

**Problème** :
- Aucun mécanisme de retry sur les appels HTTP
- Si un service est temporairement indisponible, l'appel échoue immédiatement

**Impact** :
- Scans échouent si un service est lent ou temporairement down
- Pas de résilience réseau

**Fichiers concernés** :
- `app/services/radarr.py` (lignes 65-89)
- `app/services/sonarr.py` (lignes 63-87)
- `app/services/overseerr.py` (lignes 27-67)
- `app/services/plex.py` (pas de timeout du tout)

**Solution recommandée** :
- Créer `app/utils/http_client.py` avec retries et backoff exponentiel
- Utiliser `tenacity` pour les retries intelligents

---

### 6. Timeouts incohérents

**Sévérité** : 🟠 MAJEUR - Performance

**Problème** :
- Timeouts différents selon les services :
  - Radarr/Sonarr : 30s
  - Overseerr : 30s
  - Tautulli : 60s
  - Plex : **AUCUN TIMEOUT** ⚠️
- Pas de timeout configurable centralisé

**Impact** :
- Plex peut bloquer indéfiniment
- Pas de cohérence dans la gestion des timeouts

**Fichiers concernés** :
- `app/services/plex.py` (lignes 33-36) - Pas de timeout
- Tous les autres services

---

### 7. I/O synchrones dans services

**Sévérité** : 🟠 MAJEUR - Performance

**Problème** :
- Méthodes `get_movies_sync()` et `get_series_sync()` dans Radarr/Sonarr
- Utilisées dans `planner.py` qui est async
- Bloque le thread principal

**Fichiers concernés** :
- `app/services/radarr.py` (lignes 78-89)
- `app/services/sonarr.py` (lignes 76-87)
- `app/core/planner.py` (lignes 86, 100)

**Solution recommandée** :
- Utiliser uniquement les méthodes async
- Ou wrapper les méthodes sync dans `asyncio.to_thread()`

---

### 8. Pas de circuit breaker

**Sévérité** : 🟠 MAJEUR - Stabilité

**Problème** :
- Si un service est down, tous les appels échouent
- Pas de mécanisme pour éviter de surcharger un service down

**Impact** :
- Scans échouent complètement si un service est indisponible
- Pas de scan partiel possible

---

### 9. Gestion d'erreurs basique

**Sévérité** : 🟠 MAJEUR - Maintenabilité

**Problème** :
- Exceptions génériques (`Exception`)
- Pas de logging structuré
- Pas de distinction entre erreurs récupérables et non récupérables

**Fichiers concernés** :
- Tous les services
- `app/core/planner.py`
- `app/core/executor.py`

**Solution recommandée** :
- Utiliser `structlog` pour logs structurés
- Créer des exceptions personnalisées
- Distinguer erreurs réseau, erreurs de validation, erreurs critiques

---

### 10. Pas de logs structurés

**Sévérité** : 🟠 MAJEUR - Observabilité

**Problème** :
- Logs basiques avec `logging` standard
- Pas de contexte structuré
- Difficile à analyser en production

**Solution recommandée** :
- Migrer vers `structlog`
- Ajouter des champs contextuels (scan_id, service, etc.)

---

## 🟡 Problèmes Mineurs

### 11. UI peu qualitative

**Sévérité** : 🟡 MINEUR - UX

**Problèmes** :
- Interface fonctionnelle mais pas moderne
- Pas de bibliothèque UI cohérente
- Styles basiques

**Solution recommandée** :
- Intégrer Mantine ou shadcn/ui
- Améliorer la typographie et les espacements

---

### 12. Pas de tests

**Sévérité** : 🟡 MINEUR - Qualité

**Problème** :
- Aucun test unitaire ou d'intégration
- Difficile de valider les changements

**Solution recommandée** :
- Ajouter des tests pour le matching torrents (critique)
- Tests unitaires pour les règles
- Tests d'intégration pour les services

---

### 13. Dockerfile : User root

**Sévérité** : 🟡 MINEUR - Sécurité

**Problème** :
- Container tourne en root
- Pas de user non-root

**Solution recommandée** :
- Créer user `mediajanitor`
- Changer ownership des volumes si nécessaire

---

### 14. Pas de migrations DB

**Sévérité** : 🟡 MINEUR - Maintenabilité

**Problème** :
- SQLite avec `create_all()` uniquement
- Pas de système de migrations
- Risque de perte de données lors de changements de schéma

**Solution recommandée** :
- Utiliser Alembic pour les migrations
- Ou documenter les changements de schéma manuels

---

### 15. Pagination Overseerr limitée

**Sévérité** : 🟡 MINEUR - Fonctionnalité

**Problème** :
- `params["take"] = 1000` hardcodé
- Si plus de 1000 requêtes, certaines sont ignorées

**Fichiers concernés** :
- `app/services/overseerr.py` (lignes 34, 55)

**Solution recommandée** :
- Implémenter la pagination complète
- Ou augmenter la limite si l'API le permet

---

## ✅ Points Positifs

### Architecture
- ✅ Séparation claire des responsabilités (services, core, api)
- ✅ Utilisation de SQLAlchemy 2.0 (moderne)
- ✅ FastAPI avec async/await
- ✅ Frontend React avec Vite (moderne)

### Sécurité
- ✅ Dry-run par défaut configuré
- ✅ Phrase de confirmation optionnelle
- ✅ Protection par tags Radarr/Sonarr
- ✅ Protection par requêtes Overseerr

### Fonctionnalités
- ✅ WebSocket pour progression scan (déjà implémenté)
- ✅ Tri et filtres côté frontend (déjà implémentés)
- ✅ Gestion des protections multiples
- ✅ Logs de progression en temps réel

---

## 📋 Recommandations par Priorité

### Priorité 1 - CRITIQUE (Bloquant)
1. **Fix matching qBittorrent** - 0 torrents trouvés
2. **Fix séparation Films/Séries** - Confusion utilisateur
3. **Gestion d'erreurs 500** - Expérience utilisateur
4. **Fix scroll qui remonte** - UX dégradée

### Priorité 2 - MAJEUR (Stabilité)
5. **Ajouter retries HTTP** - Résilience réseau
6. **Uniformiser timeouts** - Performance
7. **Remplacer I/O sync** - Performance
8. **Circuit breaker** - Stabilité
9. **Logs structurés** - Observabilité

### Priorité 3 - MINEUR (Polish)
10. **Refonte UI** - UX
11. **Tests** - Qualité
12. **User non-root Docker** - Sécurité
13. **Migrations DB** - Maintenabilité

---

## 🔄 Ordre d'Implémentation Recommandé

1. **Phase 1** : Audit (✅ COMPLÉTÉ - ce document)
2. **Phase 2.1** : Mise à jour backend (packages, retries, timeouts)
3. **Phase 3** : Refactor matching torrents (CRITIQUE)
4. **Phase 2.2** : Mise à jour frontend (packages, UI lib)
5. **Phase 4** : Refonte UI
6. **Phase 5** : Stabilité et sécurité
7. **Phase 6** : Docker et déploiement

---

## 📊 Métriques Actuelles vs Cibles

| Métrique | Actuel | Cible |
|----------|--------|-------|
| Torrents matchés | 0% | 100% |
| Erreurs 500 | Fréquentes | 0 |
| Retries HTTP | 0 | Automatiques |
| Timeouts uniformes | Non | Oui |
| Logs structurés | Non | Oui |
| Tests | 0 | >80% coverage |
| User Docker | root | non-root |

---

## 🎯 Conclusion

Le projet Media Janitor a une **architecture solide** mais souffre de **problèmes critiques** qui bloquent son utilisation en production :

1. **Matching qBittorrent défaillant** - Bloque la fonctionnalité principale
2. **Gestion d'erreurs insuffisante** - Expérience utilisateur dégradée
3. **Manque de résilience réseau** - Pas de retries, timeouts incohérents

**Recommandation** : Procéder à la refonte selon le plan établi, en commençant par les problèmes critiques (matching, erreurs) avant d'améliorer l'UI et la stabilité.

---

**Prochaines étapes** : Implémenter le plan de refonte phase par phase, en validant chaque étape avant de passer à la suivante.

