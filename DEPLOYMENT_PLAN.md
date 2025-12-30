# Plan de Déploiement - Media Janitor V2

## 🎯 Objectifs

1. **Corriger les bugs critiques** (qBittorrent, séparation Films/Séries, UI)
2. **Améliorer l'expérience utilisateur** (progression, filtres, tri)
3. **Rendre l'interface professionnelle et épurée**

---

## 📋 Plan d'Action Détaillé

### Phase 1 : Corrections Critiques (Priorité Haute)

#### 1.1 Fix qBittorrent Matching (0 torrents trouvés)
**Problème** : Aucun torrent n'est trouvé malgré 2518 torrents disponibles

**Causes possibles** :
- Chemins normalisés différemment entre Radarr/Sonarr et qBittorrent
- Matching par nom de fichier non fonctionnel
- Problème de format de chemin (Windows vs Linux)

**Solutions** :
- [ ] Améliorer le matching par chemin avec plusieurs stratégies :
  - Matching exact du chemin
  - Matching par nom de dossier parent
  - Matching par nom de fichier dans le torrent
- [ ] Ajouter un mode de debug pour logger les chemins comparés
- [ ] Utiliser `torrent.files()` de qBittorrent API pour matcher par fichiers individuels
- [ ] Ajouter un fallback : matcher par TMDb/TVDb ID si disponible dans les tags du torrent

**Fichiers à modifier** :
- `app/services/qbittorrent.py` - Améliorer `find_torrents_for_path()`
- `app/core/matcher.py` - Ajouter logs de debug

#### 1.2 Fix Séparation Films/Séries
**Problème** : Films et séries mélangés dans l'onglet Films, onglet Séries ne fonctionne pas

**Solutions** :
- [ ] Vérifier que `media_type` est correctement défini dans `PlanItem`
- [ ] Filtrer correctement dans `MoviesTab.jsx` et `SeriesTab.jsx`
- [ ] S'assurer que le matching ne mélange pas les types
- [ ] Ajouter des logs pour vérifier le type de chaque item

**Fichiers à modifier** :
- `app/core/planner.py` - Vérifier le type lors de la création des PlanItems
- `frontend/src/components/MoviesTab.jsx` - Filtrer uniquement `media_type === "movie"`
- `frontend/src/components/SeriesTab.jsx` - Filtrer uniquement `media_type === "series"`

#### 1.3 Fix Barre de Sélection dans Séries
**Problème** : La barre supérieure de sélection disparaît dans l'onglet Séries

**Solutions** :
- [ ] Vérifier que le plan existe et contient des séries
- [ ] S'assurer que les mêmes composants de sélection sont présents dans `SeriesTab.jsx`
- [ ] Corriger la logique de rendu conditionnel

**Fichiers à modifier** :
- `frontend/src/components/SeriesTab.jsx` - Ajouter la barre de sélection

#### 1.4 Fix Scroll qui Remonte
**Problème** : Quand on décoche un item, la page remonte en haut

**Solutions** :
- [ ] Utiliser `preventDefault()` sur les événements de checkbox
- [ ] Gérer l'état local sans re-render complet
- [ ] Utiliser `useCallback` pour éviter les re-renders inutiles
- [ ] Sauvegarder la position de scroll et la restaurer après update

**Fichiers à modifier** :
- `frontend/src/components/MoviesTab.jsx`
- `frontend/src/components/SeriesTab.jsx`
- `frontend/src/components/PlanItemRow.jsx`

---

### Phase 2 : Améliorations UX (Priorité Moyenne)

#### 2.1 Progression du Scan en Temps Réel
**Feature** : Afficher la progression détaillée du scan avec logs

**Solutions** :
- [ ] Créer un endpoint WebSocket ou Server-Sent Events pour les logs en temps réel
- [ ] Alternative : Endpoint `/api/scan/status` avec polling
- [ ] Afficher une barre de progression avec étapes :
  - Scan Plex (films/séries)
  - Scan Radarr
  - Scan Sonarr
  - Scan Overseerr
  - Scan qBittorrent
  - Matching et unification
  - Évaluation des règles
  - Création du plan
- [ ] Afficher les logs en temps réel dans l'UI

**Fichiers à créer/modifier** :
- `app/api/routes.py` - Ajouter endpoint de statut
- `app/core/planner.py` - Logger les étapes avec timestamps
- `frontend/src/components/ScanProgress.jsx` - Nouveau composant
- `frontend/src/components/Dashboard.jsx` - Intégrer la progression

#### 2.2 Options de Tri
**Feature** : Trier les films/séries par différents critères

**Options de tri** :
- Ordre alphabétique (A-Z, Z-A)
- Nombre de vues (croissant, décroissant)
- Dernière date de visionnage (récent, ancien)
- Date d'ajout (récent, ancien)
- Taille (croissant, décroissant)

**Solutions** :
- [ ] Ajouter un sélecteur de tri dans l'UI
- [ ] Implémenter les fonctions de tri côté client
- [ ] Sauvegarder la préférence de tri dans localStorage

**Fichiers à modifier** :
- `frontend/src/components/MoviesTab.jsx` - Ajouter sélecteur de tri
- `frontend/src/components/SeriesTab.jsx` - Ajouter sélecteur de tri
- `frontend/src/utils/sorting.js` - Nouveau fichier avec fonctions de tri

#### 2.3 Filtres Avancés
**Feature** : Filtrer les items selon différents critères

**Filtres** :
- Jamais vus uniquement
- Dernier visionnage depuis X jours
- Ajouté depuis au moins X mois
- Avec/Sans torrents
- Protégés/Non protégés
- Par règle de suppression

**Solutions** :
- [ ] Créer un panneau de filtres dans l'UI
- [ ] Implémenter la logique de filtrage côté client
- [ ] Afficher le nombre d'items filtrés

**Fichiers à modifier** :
- `frontend/src/components/MoviesTab.jsx` - Ajouter panneau de filtres
- `frontend/src/components/SeriesTab.jsx` - Ajouter panneau de filtres
- `frontend/src/utils/filtering.js` - Nouveau fichier avec fonctions de filtrage

---

### Phase 3 : Amélioration du Design (Priorité Moyenne)

#### 3.1 Interface Pro et Épurée
**Feature** : Rendre l'interface plus professionnelle

**Améliorations** :
- [ ] Améliorer la typographie et les espacements
- [ ] Utiliser un système de couleurs cohérent
- [ ] Ajouter des icônes pour améliorer la lisibilité
- [ ] Améliorer les cartes et les bordures
- [ ] Rendre l'interface responsive
- [ ] Ajouter des animations subtiles

**Fichiers à modifier** :
- `frontend/src/index.css` - Styles globaux
- `frontend/src/components/*.css` - Styles des composants
- Ajouter une bibliothèque d'icônes (ex: react-icons)

#### 3.2 Amélioration de la Table
**Feature** : Rendre la table plus lisible et fonctionnelle

**Améliorations** :
- [ ] Ajouter un header fixe lors du scroll
- [ ] Améliorer l'alternance des couleurs de lignes
- [ ] Ajouter des tooltips sur les colonnes
- [ ] Rendre les colonnes redimensionnables
- [ ] Ajouter une recherche rapide

**Fichiers à modifier** :
- `frontend/src/components/PlanItemRow.jsx`
- `frontend/src/components/MoviesTab.jsx`
- `frontend/src/components/SeriesTab.jsx`

---

## 🔧 Implémentation Technique

### Structure des Modifications

```
app/
├── api/
│   └── routes.py                    # Ajouter endpoint scan/status
├── core/
│   ├── planner.py                   # Améliorer logs et progression
│   └── matcher.py                   # Améliorer matching qBittorrent
└── services/
    └── qbittorrent.py               # Fix matching torrents

frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx           # Ajouter progression scan
│   │   ├── MoviesTab.jsx            # Fix scroll, tri, filtres
│   │   ├── SeriesTab.jsx            # Fix barre sélection, tri, filtres
│   │   ├── PlanItemRow.jsx         # Fix scroll
│   │   └── ScanProgress.jsx        # Nouveau composant
│   ├── utils/
│   │   ├── sorting.js               # Fonctions de tri
│   │   └── filtering.js             # Fonctions de filtrage
│   └── api.js                       # Ajouter endpoints
```

---

## 📝 Checklist de Déploiement

### Étape 1 : Corrections Critiques
- [ ] Fix qBittorrent matching
- [ ] Fix séparation Films/Séries
- [ ] Fix barre de sélection Séries
- [ ] Fix scroll qui remonte
- [ ] Tests manuels

### Étape 2 : Features UX
- [ ] Progression du scan
- [ ] Options de tri
- [ ] Filtres avancés
- [ ] Tests manuels

### Étape 3 : Design
- [ ] Amélioration du design
- [ ] Amélioration de la table
- [ ] Tests visuels

### Étape 4 : Tests Finaux
- [ ] Tests end-to-end
- [ ] Tests de performance
- [ ] Vérification des logs
- [ ] Documentation

---

## 🚀 Ordre d'Implémentation Recommandé

1. **Fix qBittorrent** (critique, bloque les fonctionnalités)
2. **Fix séparation Films/Séries** (critique, confusion utilisateur)
3. **Fix scroll et barre de sélection** (UX critique)
4. **Progression du scan** (améliore l'expérience)
5. **Tri et filtres** (améliore la productivité)
6. **Design** (polish final)

---

## 📊 Métriques de Succès

- ✅ 100% des torrents correctement matchés
- ✅ Films et séries parfaitement séparés
- ✅ Aucun scroll involontaire
- ✅ Progression visible pendant le scan
- ✅ Tri et filtres fonctionnels
- ✅ Interface professionnelle et épurée

---

## 🐛 Bugs à Corriger en Priorité

1. **qBittorrent matching** - 0 torrents trouvés
2. **Séparation Films/Séries** - Mélange dans l'onglet Films
3. **Barre de sélection** - Disparaît dans Séries
4. **Scroll** - Remonte en haut lors du décochage

---

## 💡 Notes d'Implémentation

- Utiliser des logs détaillés pour debugger qBittorrent
- Tester avec de vrais chemins de fichiers
- Vérifier les formats de chemin (Windows/Linux)
- Implémenter les features par ordre de priorité
- Tester chaque feature avant de passer à la suivante

