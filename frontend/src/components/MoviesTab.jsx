import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { getPlan, updateItems, applyPlan } from '../api'
import PlanItemRow from './PlanItemRow'
import ConfirmationModal from './ConfirmationModal'
import { applySort } from '../utils/sorting'
import { applyFilters } from '../utils/filtering'
import './MoviesTab.css'

function MoviesTab() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const planId = searchParams.get('plan')
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState(null)
  const [requireConfirmPhrase, setRequireConfirmPhrase] = useState(null)
  const [showProtected, setShowProtected] = useState(false)
  const scrollPositionRef = useRef(0)
  
  // Tri et filtres
  const [sortOption, setSortOption] = useState(() => {
    return localStorage.getItem('movies_sort_option') || 'alphabetical'
  })
  const [sortDirection, setSortDirection] = useState(() => {
    return localStorage.getItem('movies_sort_direction') || 'asc'
  })
  const [filters, setFilters] = useState({
    neverWatchedOnly: false,
    lastWatchedDays: '',
    addedMonths: '',
    torrentsFilter: 'all', // 'all', 'with', 'without'
    protectedFilter: 'all', // 'all', 'protected', 'unprotected'
    rule: 'all'
  })
  const [showFilters, setShowFilters] = useState(false)

  const loadPlan = useCallback(async (restoreScroll = false) => {
    if (!planId || planId === 'null' || planId === 'undefined') return
    setLoading(true)
    try {
      const data = await getPlan(planId)
      setPlan(data)
      // Charger requireConfirmPhrase depuis config
      try {
        const configRes = await fetch('/api/config')
        const config = await configRes.json()
        setRequireConfirmPhrase(config.app?.require_confirm_phrase || null)
      } catch (e) {
        // Ignore
      }
      
      // Restaurer la position de scroll après le re-render
      if (restoreScroll && scrollPositionRef.current > 0) {
        setTimeout(() => {
          window.scrollTo(0, scrollPositionRef.current)
        }, 0)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [planId])

  useEffect(() => {
    if (planId) {
      loadPlan()
    }
  }, [planId, loadPlan])

  const handleToggleItem = useCallback(async (itemId, selected) => {
    // Sauvegarder la position de scroll avant la mise à jour
    scrollPositionRef.current = window.scrollY || window.pageYOffset
    
    try {
      // Mettre à jour l'état local immédiatement pour éviter le re-render complet
      setPlan(prevPlan => {
        if (!prevPlan) return prevPlan
        return {
          ...prevPlan,
          items: prevPlan.items.map(item => 
            item.id === itemId ? { ...item, selected } : item
          )
        }
      })
      
      // Appel API en arrière-plan (ne bloque pas l'UI)
      updateItems(planId, [{ id: itemId, selected }]).catch(err => {
        setError(err.message)
        // En cas d'erreur, recharger le plan complet
        loadPlan(true)
      })
    } catch (err) {
      setError(err.message)
      loadPlan(true)
    }
  }, [planId, loadPlan])

  const handleSelectAll = useCallback(async (selected) => {
    // Sauvegarder la position de scroll
    scrollPositionRef.current = window.scrollY || window.pageYOffset
    
    try {
      await updateItems(planId, [], selected)
      loadPlan(true)
    } catch (err) {
      setError(err.message)
    }
  }, [planId, loadPlan])

  const handleApply = async (confirmPhrase) => {
    setApplying(true)
    try {
      const response = await fetch(`/api/plan/${planId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm_phrase: confirmPhrase || null }),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Apply failed')
      }
      const result = await response.json()
      navigate(`/history?run=${result.run_id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setApplying(false)
      setShowConfirm(false)
    }
  }

  if (!planId) {
    return (
      <div className="container">
        <p>Aucun plan sélectionné. Lancez un scan depuis le dashboard.</p>
      </div>
    )
  }

  if (loading) {
    return <div className="container">Chargement...</div>
  }

  if (!plan) {
    return <div className="container">Plan non trouvé</div>
  }

  // Filtrer par type et protection
  let movies = plan.items.filter(item => {
    if (item.media_type !== 'movie') return false
    if (!showProtected && item.protected_reason) return false
    return true
  })
  
  // Appliquer les filtres avancés
  const filteredMovies = applyFilters(movies, filters)
  
  // Appliquer le tri
  const sortedMovies = applySort(filteredMovies, sortOption, sortDirection)
  
  const selectedCount = sortedMovies.filter(item => item.selected).length
  const totalSize = sortedMovies.filter(item => item.selected).reduce((sum, item) => sum + item.size_bytes, 0)
  
  // Sauvegarder les préférences de tri
  useEffect(() => {
    localStorage.setItem('movies_sort_option', sortOption)
    localStorage.setItem('movies_sort_direction', sortDirection)
  }, [sortOption, sortDirection])

  return (
    <div className="container">
      <h1>Films</h1>
      <div className="tabs">
        <button className="tab" onClick={() => navigate('/')}>
          Dashboard
        </button>
        <button className="tab active" onClick={() => navigate('/movies')}>
          Films
        </button>
        <button className="tab" onClick={() => navigate('/series')}>
          Séries
        </button>
        <button className="tab" onClick={() => navigate('/history')}>
          Historique
        </button>
        <button className="tab" onClick={() => navigate('/settings')}>
          Paramètres
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="card">
        <div className="plan-header">
          <div>
            <h2>Plan #{plan.id}</h2>
            <p>Créé le {new Date(plan.created_at).toLocaleString('fr-FR')}</p>
          </div>
          <div>
            <button
              className="btn btn-secondary"
              onClick={() => handleSelectAll(true)}
            >
              Tout sélectionner
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleSelectAll(false)}
            >
              Tout désélectionner
            </button>
            <button
              className="btn btn-danger"
              onClick={() => setShowConfirm(true)}
              disabled={selectedCount === 0 || applying}
            >
              {applying ? 'Application...' : `Appliquer (${selectedCount})`}
            </button>
          </div>
        </div>
        <div className="plan-controls">
          <label>
            <input
              type="checkbox"
              checked={showProtected}
              onChange={(e) => setShowProtected(e.target.checked)}
            />
            Afficher les items protégés
          </label>
          <button
            className="btn btn-secondary btn-small"
            onClick={() => setShowFilters(!showFilters)}
          >
            {showFilters ? 'Masquer filtres' : 'Afficher filtres'}
          </button>
        </div>
        
        {showFilters && (
          <div className="filters-panel">
            <h4>Filtres</h4>
            <div className="filters-grid">
              <div className="filter-group">
                <label>
                  <input
                    type="checkbox"
                    checked={filters.neverWatchedOnly}
                    onChange={(e) => setFilters({...filters, neverWatchedOnly: e.target.checked})}
                  />
                  Jamais vus uniquement
                </label>
              </div>
              <div className="filter-group">
                <label>
                  Dernier visionnage depuis (jours):
                  <input
                    type="number"
                    value={filters.lastWatchedDays}
                    onChange={(e) => setFilters({...filters, lastWatchedDays: e.target.value})}
                    placeholder="Ex: 60"
                    min="0"
                  />
                </label>
              </div>
              <div className="filter-group">
                <label>
                  Ajouté depuis au moins (mois):
                  <input
                    type="number"
                    value={filters.addedMonths}
                    onChange={(e) => setFilters({...filters, addedMonths: e.target.value})}
                    placeholder="Ex: 3"
                    min="0"
                  />
                </label>
              </div>
              <div className="filter-group">
                <label>
                  Torrents:
                  <select
                    value={filters.torrentsFilter}
                    onChange={(e) => setFilters({...filters, torrentsFilter: e.target.value})}
                  >
                    <option value="all">Tous</option>
                    <option value="with">Avec torrents</option>
                    <option value="without">Sans torrents</option>
                  </select>
                </label>
              </div>
              <div className="filter-group">
                <label>
                  Protection:
                  <select
                    value={filters.protectedFilter}
                    onChange={(e) => setFilters({...filters, protectedFilter: e.target.value})}
                  >
                    <option value="all">Tous</option>
                    <option value="protected">Protégés</option>
                    <option value="unprotected">Non protégés</option>
                  </select>
                </label>
              </div>
            </div>
          </div>
        )}
        
        <div className="sort-controls">
          <label>
            Trier par:
            <select
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
            >
              <option value="alphabetical">Alphabétique</option>
              <option value="view_count">Nombre de vues</option>
              <option value="last_viewed">Dernier visionnage</option>
              <option value="added_date">Date d'ajout</option>
              <option value="size">Taille</option>
            </select>
          </label>
          <label>
            Ordre:
            <select
              value={sortDirection}
              onChange={(e) => setSortDirection(e.target.value)}
            >
              <option value="asc">Croissant</option>
              <option value="desc">Décroissant</option>
            </select>
          </label>
        </div>
        
        <div className="stats">
          <div className="stat-item">
            <div className="stat-value">{selectedCount}</div>
            <div className="stat-label">Films sélectionnés</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{sortedMovies.length}</div>
            <div className="stat-label">Films affichés {filteredMovies.length !== movies.length ? `(${filteredMovies.length} filtrés)` : ''}</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{(totalSize / 1024 / 1024 / 1024).toFixed(2)} GB</div>
            <div className="stat-label">Taille totale</div>
          </div>
        </div>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={selectedCount === sortedMovies.length && sortedMovies.length > 0}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </th>
              <th title="Titre du film">Titre</th>
              <th title="Date du dernier visionnage">Dernier visionnage</th>
              <th title="Nombre de jours depuis le dernier visionnage">Jours</th>
              <th title="Règle de suppression appliquée">Raison</th>
              <th title="Taille du fichier">Taille</th>
              <th title="Nombre de torrents qBittorrent associés">Torrents</th>
              <th title="Statut Overseerr">Overseerr</th>
              <th title="Actions disponibles">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedMovies.length === 0 ? (
              <tr>
                <td colSpan="9" style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
                  Aucun film trouvé avec les filtres sélectionnés
                </td>
              </tr>
            ) : (
              sortedMovies.map(item => (
                <PlanItemRow
                  key={item.id}
                  item={item}
                  onToggle={(selected) => handleToggleItem(item.id, selected)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {showConfirm && (
        <ConfirmationModal
          itemCount={selectedCount}
          totalSize={totalSize}
          onConfirm={handleApply}
          onCancel={() => setShowConfirm(false)}
          requireConfirmPhrase={requireConfirmPhrase}
        />
      )}
    </div>
  )
}

export default MoviesTab

