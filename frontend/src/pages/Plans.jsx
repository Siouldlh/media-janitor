import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import usePlan from '../hooks/usePlan'
import PlanHeader from '../components/plan/PlanHeader'
import PlanItemList from '../components/plan/PlanItemList'
import ConfirmationModal from '../components/ConfirmationModal'
import { applyPlan, protectItem, getLatestPlan } from '../api'
import { toast } from '../lib/toast.jsx'

function Plans() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const planIdParam = searchParams.get('planId') || searchParams.get('plan')
  const viewModeParam = searchParams.get('viewMode') || 'all'
  const [planId, setPlanId] = useState(planIdParam)
  const [loadingLatest, setLoadingLatest] = useState(false)
  
  const {
    plan,
    loading,
    error,
    selectedCount,
    totalCount,
    updateItemSelection,
    updateAllItems,
  } = usePlan(planId)

  const [applying, setApplying] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [requireConfirmPhrase, setRequireConfirmPhrase] = useState(null)
  const [viewMode, setViewMode] = useState(viewModeParam) // 'all', 'movies', 'series'
  const [sortOption, setSortOption] = useState('alphabetical')
  const [sortDirection, setSortDirection] = useState('asc')
  const [filters, setFilters] = useState({
    neverWatchedOnly: false,
    lastWatchedDays: '',
    addedMonths: '',
    torrentsFilter: 'all',
    protectedFilter: 'all',
    rule: 'all'
  })

  // Load latest plan if no planId provided
  useEffect(() => {
    const loadLatestPlan = async () => {
      if (planId) return // Already have a planId
      
      setLoadingLatest(true)
      try {
        const latestPlan = await getLatestPlan()
        setPlanId(latestPlan.id)
        // Update URL with planId but keep viewMode
        setSearchParams(prev => {
          const newParams = new URLSearchParams(prev)
          newParams.set('planId', latestPlan.id.toString())
          return newParams
        })
      } catch (err) {
        // No plan found, that's okay
        console.log('No latest plan found:', err.message)
      } finally {
        setLoadingLatest(false)
      }
    }
    
    loadLatestPlan()
  }, [planId, setSearchParams])

  // Sync viewMode with URL param
  useEffect(() => {
    const urlViewMode = searchParams.get('viewMode') || 'all'
    if (urlViewMode !== viewMode) {
      setViewMode(urlViewMode)
    }
  }, [searchParams, viewMode])

  // Update URL when viewMode changes
  const handleViewModeChange = (newMode) => {
    setViewMode(newMode)
    setSearchParams(prev => {
      const newParams = new URLSearchParams(prev)
      newParams.set('viewMode', newMode)
      return newParams
    })
  }

  // Load confirm phrase from config
  React.useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await fetch('/api/config')
        const config = await res.json()
        setRequireConfirmPhrase(config.app?.require_confirm_phrase || null)
      } catch (e) {
        // Ignore
      }
    }
    loadConfig()
  }, [])

  const handleApply = () => {
    if (selectedCount === 0) return
    setShowConfirm(true)
  }

  const handleConfirmApply = async (confirmPhrase) => {
    if (!planId) return

    if (requireConfirmPhrase && confirmPhrase !== requireConfirmPhrase) {
      alert('Phrase de confirmation incorrecte')
      return
    }

    setApplying(true)
    try {
      await applyPlan(planId, confirmPhrase || null)
      toast.success('Plan appliqué avec succès')
      navigate('/history')
    } catch (err) {
      toast.error(`Erreur: ${err.message}`)
    } finally {
      setApplying(false)
      setShowConfirm(false)
    }
  }

  const handleProtect = async (item) => {
    if (!confirm(`Protéger "${item.title}" de toute suppression future ?`)) {
      return
    }
    try {
      await protectItem({
        media_type: item.media_type,
        tmdb_id: item.ids?.tmdb,
        tvdb_id: item.ids?.tvdb,
        imdb_id: item.ids?.imdb,
        path: item.path,
        reason: 'Protection manuelle',
      })
      toast.success('Item protégé avec succès')
      // Reload plan to reflect protection
      window.location.reload()
    } catch (err) {
      toast.error(`Erreur: ${err.message}`)
    }
  }

  // Filter items by view mode
  const filteredItems = React.useMemo(() => {
    if (!plan?.items) return []
    let items = plan.items

    if (viewMode === 'movies') {
      items = items.filter(item => item.media_type === 'movie')
    } else if (viewMode === 'series') {
      // Inclure les séries ET les épisodes individuels
      items = items.filter(item => item.media_type === 'series' || item.media_type === 'episode')
    }

    return items
  }, [plan, viewMode])

  if (loading || loadingLatest) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-500">Chargement du plan...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-800">Erreur: {error}</p>
        </div>
      </div>
    )
  }

  if (!plan && !loadingLatest) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-500 mb-4">Aucun plan trouvé</p>
          <button
            onClick={() => navigate('/')}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Retour au dashboard pour créer un scan
          </button>
        </div>
      </div>
    )
  }

  if (!plan) {
    return null // Still loading
  }

  return (
    <div className="max-w-6xl mx-auto">
      <PlanHeader
        plan={plan}
        selectedCount={selectedCount}
        totalCount={totalCount}
        onSelectAll={() => updateAllItems(true)}
        onDeselectAll={() => updateAllItems(false)}
        onApply={handleApply}
        applying={applying}
      />

      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center space-x-4 mb-6">
          <button
            onClick={() => handleViewModeChange('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Tous
          </button>
          <button
            onClick={() => handleViewModeChange('movies')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'movies'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Films ({plan.items?.filter(item => item.media_type === 'movie').length || 0})
          </button>
          <button
            onClick={() => handleViewModeChange('series')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'series'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Séries ({plan.items?.filter(item => item.media_type === 'series' || item.media_type === 'episode').length || 0})
          </button>
        </div>

        <div className="mb-4 flex items-center space-x-4">
          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="alphabetical">Alphabétique</option>
            <option value="view_count">Nombre de vues</option>
            <option value="last_viewed">Dernier visionnage</option>
            <option value="added_date">Date d'ajout</option>
            <option value="size">Taille</option>
          </select>
          <select
            value={sortDirection}
            onChange={(e) => setSortDirection(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="asc">Croissant</option>
            <option value="desc">Décroissant</option>
          </select>
        </div>

        <PlanItemList
          items={filteredItems}
          onToggle={updateItemSelection}
          onProtect={handleProtect}
          filters={filters}
          sortOption={sortOption}
          sortDirection={sortDirection}
        />
      </div>

      {showConfirm && (
        <ConfirmationModal
          onConfirm={handleConfirmApply}
          onCancel={() => setShowConfirm(false)}
          requirePhrase={requireConfirmPhrase}
          selectedCount={selectedCount}
        />
      )}
    </div>
  )
}

export default Plans

