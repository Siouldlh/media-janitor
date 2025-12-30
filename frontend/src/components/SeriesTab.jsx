import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { getPlan, updateItems, applyPlan } from '../api'
import PlanItemRow from './PlanItemRow'
import ConfirmationModal from './ConfirmationModal'
import './SeriesTab.css'

function SeriesTab() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const planId = searchParams.get('plan')
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('series') // 'series' or 'episodes'
  const [requireConfirmPhrase, setRequireConfirmPhrase] = useState(null)
  const [showProtected, setShowProtected] = useState(false)

  useEffect(() => {
    if (planId) {
      loadPlan()
    }
  }, [planId])

  const loadPlan = async () => {
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
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleItem = async (itemId, selected) => {
    try {
      await updateItems(planId, [{ id: itemId, selected }])
      loadPlan()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSelectAll = async (selected) => {
    try {
      await updateItems(planId, [], selected)
      loadPlan()
    } catch (err) {
      setError(err.message)
    }
  }

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

  const series = plan.items.filter(item => {
    if (item.media_type !== 'series') return false
    if (!showProtected && item.protected_reason) return false
    return true
  })
  const episodes = plan.items.filter(item => {
    if (item.media_type !== 'episode') return false
    if (!showProtected && item.protected_reason) return false
    return true
  })
  const items = viewMode === 'series' ? series : episodes
  const selectedCount = items.filter(item => item.selected).length
  const totalSize = items.filter(item => item.selected).reduce((sum, item) => sum + item.size_bytes, 0)

  return (
    <div className="container">
      <h1>Séries</h1>
      <div className="tabs">
        <button className="tab" onClick={() => navigate('/')}>
          Dashboard
        </button>
        <button className="tab" onClick={() => navigate('/movies')}>
          Films
        </button>
        <button className="tab active" onClick={() => navigate('/series')}>
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
              className={`btn ${viewMode === 'series' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setViewMode('series')}
            >
              Vue série
            </button>
            <button
              className={`btn ${viewMode === 'episodes' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setViewMode('episodes')}
            >
              Vue épisodes
            </button>
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
        <div className="stats">
          <div className="stat-item">
            <div className="stat-value">{selectedCount}</div>
            <div className="stat-label">{viewMode === 'series' ? 'Séries sélectionnées' : 'Épisodes sélectionnés'}</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{(totalSize / 1024 / 1024 / 1024).toFixed(2)} GB</div>
            <div className="stat-label">Taille totale</div>
          </div>
        </div>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                checked={selectedCount === items.length && items.length > 0}
                onChange={(e) => handleSelectAll(e.target.checked)}
              />
            </th>
            <th>Titre</th>
            <th>Dernier visionnage</th>
            <th>Jours</th>
            <th>Raison</th>
            <th>Taille</th>
            <th>Torrents</th>
            <th>Overseerr</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <PlanItemRow
              key={item.id}
              item={item}
              onToggle={(selected) => handleToggleItem(item.id, selected)}
            />
          ))}
        </tbody>
      </table>

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

export default SeriesTab

