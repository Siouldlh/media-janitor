import React, { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import usePlan from '../hooks/usePlan'
import PlanHeader from '../components/plan/PlanHeader'
import PlanItemList from '../components/plan/PlanItemList'
import ConfirmationModal from '../components/ConfirmationModal'
import { applyPlan, protectItem } from '../api'
import { toast } from '../lib/toast.jsx'

function Plans() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const planId = searchParams.get('planId') || searchParams.get('plan')
  
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
  const [viewMode, setViewMode] = useState('all') // 'all', 'movies', 'series'
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
      items = items.filter(item => item.media_type === 'series')
    }

    return items
  }, [plan, viewMode])

  if (!planId) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-500 mb-4">Aucun plan sélectionné</p>
          <button
            onClick={() => navigate('/')}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Retour au dashboard
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
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

  if (!plan) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-500">Plan non trouvé</p>
        </div>
      </div>
    )
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
            onClick={() => setViewMode('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Tous
          </button>
          <button
            onClick={() => setViewMode('movies')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'movies'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Films ({plan.items?.filter(item => item.media_type === 'movie').length || 0})
          </button>
          <button
            onClick={() => setViewMode('series')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'series'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Séries ({plan.items?.filter(item => item.media_type === 'series').length || 0})
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

