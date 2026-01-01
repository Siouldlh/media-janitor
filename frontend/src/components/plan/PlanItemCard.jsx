import React, { useState } from 'react'
import { HiShieldCheck, HiInformationCircle, HiChevronDown, HiChevronUp } from 'react-icons/hi2'

function PlanItemCard({ item, onToggle, onProtect }) {
  const [showTorrents, setShowTorrents] = useState(false)
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

          <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
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
              <p className="text-gray-500">Torrents</p>
              <p className="font-medium text-gray-900">
                {item.qb_hashes && item.qb_hashes.length > 0 ? (
                  <span className="text-green-600">{item.qb_hashes.length} trouvé{item.qb_hashes.length > 1 ? 's' : ''}</span>
                ) : (
                  <span className="text-gray-400">Aucun</span>
                )}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Règle</p>
              <p className="font-medium text-gray-900">{item.rule || '-'}</p>
            </div>
          </div>
          
          {/* Afficher les détails des torrents si disponibles */}
          {item.qb_hashes && item.qb_hashes.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setShowTorrents(!showTorrents)}
                className="w-full flex items-center justify-between p-2 bg-blue-50 hover:bg-blue-100 rounded text-sm text-blue-800 font-medium transition-colors"
              >
                <span>
                  Torrents associés ({item.qb_hashes.length})
                </span>
                {showTorrents ? (
                  <HiChevronUp className="h-5 w-5" />
                ) : (
                  <HiChevronDown className="h-5 w-5" />
                )}
              </button>
              
              {showTorrents && (
                <div className="mt-2 p-3 bg-gray-50 rounded border border-gray-200">
                  <div className="space-y-2">
                    {item.meta?.qb_torrents && item.meta.qb_torrents.length > 0 ? (
                      // Afficher les noms des torrents si disponibles
                      item.meta.qb_torrents.map((torrent, idx) => (
                        <div key={idx} className="flex items-start space-x-2 text-sm">
                          <span className="text-gray-500">•</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-gray-900 font-medium truncate" title={torrent.name}>
                              {torrent.name || `Torrent ${idx + 1}`}
                            </p>
                            <p className="text-xs text-gray-500 font-mono">
                              {torrent.hash?.substring(0, 16)}...
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      // Fallback: afficher les hash si les noms ne sont pas disponibles
                      item.qb_hashes.map((hash, idx) => (
                        <div key={idx} className="flex items-center space-x-2 text-sm">
                          <span className="text-gray-500">•</span>
                          <p className="text-gray-700 font-mono text-xs">
                            {hash.substring(0, 16)}...
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

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

