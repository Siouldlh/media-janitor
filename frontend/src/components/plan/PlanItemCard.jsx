import React from 'react'
import { HiShieldCheck, HiInformationCircle } from 'react-icons/hi2'

function PlanItemCard({ item, onToggle, onProtect }) {
  const formatDate = (date) => {
    if (!date) return 'Jamais vu'
    return new Date(date).toLocaleDateString('fr-FR')
  }

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const daysSinceWatched = (date) => {
    if (!date) return '-'
    const days = Math.floor((new Date() - new Date(date)) / (1000 * 60 * 60 * 24))
    return days
  }

  const isProtected = !!item.protected_reason

  return (
    <div
      className={`
        bg-white rounded-lg border-2 p-4 transition-all
        ${item.selected ? 'border-blue-500 shadow-md' : 'border-gray-200 hover:border-gray-300'}
        ${isProtected ? 'bg-yellow-50 border-yellow-300' : ''}
      `}
    >
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0 pt-1">
          <input
            type="checkbox"
            checked={item.selected}
            onChange={(e) => onToggle(item.id, e.target.checked)}
            disabled={isProtected}
            className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">
                {item.title} {item.year && `(${item.year})`}
              </h3>
              <p className="text-sm text-gray-500 mt-1">{item.path}</p>
            </div>
            <div className="flex items-center space-x-2 ml-4">
              {isProtected && (
                <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded">
                  <HiShieldCheck className="mr-1 h-4 w-4" />
                  Protégé
                </span>
              )}
              {!isProtected && (
                <button
                  onClick={() => onProtect(item)}
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Protéger"
                >
                  <HiShieldCheck className="h-5 w-5" />
                </button>
              )}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Dernier visionnage</p>
              <p className="font-medium text-gray-900">{formatDate(item.last_viewed_at)}</p>
              <p className="text-xs text-gray-500">{daysSinceWatched(item.last_viewed_at)} jours</p>
            </div>
            <div>
              <p className="text-gray-500">Vues</p>
              <p className="font-medium text-gray-900">{item.view_count || 0}</p>
            </div>
            <div>
              <p className="text-gray-500">Taille</p>
              <p className="font-medium text-gray-900">{formatSize(item.size_bytes)}</p>
            </div>
            <div>
              <p className="text-gray-500">Règle</p>
              <p className="font-medium text-gray-900">{item.rule || '-'}</p>
            </div>
          </div>

          {item.protected_reason && (
            <div className="mt-3 p-2 bg-yellow-50 rounded text-sm text-yellow-800">
              <HiInformationCircle className="inline mr-1 h-4 w-4" />
              {item.protected_reason}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PlanItemCard

