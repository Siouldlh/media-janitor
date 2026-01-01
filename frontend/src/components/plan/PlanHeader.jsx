import React from 'react'
import { HiCheckCircle, HiXCircle, HiTrash } from 'react-icons/hi2'

function PlanHeader({ plan, selectedCount, totalCount, onSelectAll, onDeselectAll, onApply, applying }) {
  if (!plan) return null

  const totalSize = plan.items?.reduce((sum, item) => sum + (item.size_bytes || 0), 0) || 0
  const sizeGB = (totalSize / 1024 / 1024 / 1024).toFixed(2)

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            Plan #{plan.id}
          </h1>
          <p className="text-sm text-gray-600">
            Créé le {new Date(plan.created_at).toLocaleString('fr-FR')}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={onSelectAll}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <HiCheckCircle className="mr-2 h-4 w-4" />
            Tout sélectionner
          </button>
          <button
            onClick={onDeselectAll}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <HiXCircle className="mr-2 h-4 w-4" />
            Tout désélectionner
          </button>
          <button
            onClick={onApply}
            disabled={selectedCount === 0 || applying}
            className={`
              inline-flex items-center px-6 py-2 text-sm font-medium text-white rounded-lg
              ${selectedCount === 0 || applying
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-red-600 hover:bg-red-700'
              }
              transition-colors
            `}
          >
            <HiTrash className="mr-2 h-4 w-4" />
            {applying ? 'Application...' : `Appliquer (${selectedCount})`}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200">
        <div>
          <p className="text-sm text-gray-500">Items sélectionnés</p>
          <p className="text-2xl font-bold text-gray-900">
            {selectedCount} / {totalCount}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Films</p>
          <p className="text-2xl font-bold text-gray-900">
            {plan.items?.filter(item => item.media_type === 'movie').length || 0}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Séries</p>
          <p className="text-2xl font-bold text-gray-900">
            {plan.items?.filter(item => item.media_type === 'series').length || 0}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Taille totale</p>
          <p className="text-2xl font-bold text-gray-900">{sizeGB} GB</p>
        </div>
      </div>
    </div>
  )
}

export default PlanHeader

