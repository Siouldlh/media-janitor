import React, { useState } from 'react'
import { protectItem } from '../api'
import './PlanItemRow.css'

function PlanItemRow({ item, onToggle }) {
  const [showDetails, setShowDetails] = useState(false)
  const [protecting, setProtecting] = useState(false)

  const formatDate = (date) => {
    if (!date) return 'Jamais vu'
    return new Date(date).toLocaleDateString('fr-FR')
  }

  const daysSinceWatched = (date) => {
    if (!date) return '-'
    const days = Math.floor((new Date() - new Date(date)) / (1000 * 60 * 60 * 24))
    return days
  }

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const overseerrStatus = item.meta?.overseerr_status
    ? `Protégé (${item.meta.overseerr_status})`
    : 'Non protégé'

  const isProtected = !!item.protected_reason

  const handleProtect = async () => {
    if (!confirm(`Protéger "${item.title}" de toute suppression future ?`)) {
      return
    }
    setProtecting(true)
    try {
      await protectItem({
        media_type: item.media_type,
        tmdb_id: item.ids.tmdb,
        tvdb_id: item.ids.tvdb,
        imdb_id: item.ids.imdb,
        path: item.path,
        reason: 'Protection manuelle',
      })
      alert('Item protégé avec succès')
    } catch (err) {
      alert(`Erreur: ${err.message}`)
    } finally {
      setProtecting(false)
    }
  }

  return (
    <>
      <tr className={isProtected ? 'protected-row' : ''}>
        <td>
          <input
            type="checkbox"
            checked={item.selected}
            onChange={(e) => onToggle(e.target.checked)}
            disabled={isProtected}
          />
        </td>
        <td>
          {item.title} {item.year && `(${item.year})`}
        </td>
        <td>{formatDate(item.last_viewed_at)}</td>
        <td>{daysSinceWatched(item.last_viewed_at)}</td>
        <td>{item.rule || '-'}</td>
        <td>{formatSize(item.size_bytes)}</td>
        <td>{item.qb_hashes?.length || 0}</td>
        <td>{overseerrStatus}</td>
        <td>
          <div className="action-buttons">
            <button
              className="btn btn-secondary"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? 'Masquer' : 'Détails'}
            </button>
            {!isProtected && (
              <button
                className="btn btn-secondary"
                onClick={handleProtect}
                disabled={protecting}
              >
                {protecting ? '...' : 'Protéger'}
              </button>
            )}
            {isProtected && (
              <span className="protected-badge">PROTÉGÉ</span>
            )}
          </div>
        </td>
      </tr>
      {showDetails && (
        <tr>
          <td colSpan="9">
            <div className="item-details">
              <h4>Détails</h4>
              <div className="details-grid">
                <div>
                  <strong>Chemin:</strong> {item.path}
                </div>
                <div>
                  <strong>IDs:</strong> TMDb: {item.ids.tmdb || '-'}, TVDb: {item.ids.tvdb || '-'}, IMDb: {item.ids.imdb || '-'}
                </div>
                <div>
                  <strong>Vues:</strong> {item.view_count}
                </div>
                <div>
                  <strong>Torrents qBittorrent:</strong> {item.qb_hashes?.join(', ') || 'Aucun'}
                </div>
                {item.meta?.overseerr_requested_by && (
                  <div>
                    <strong>Demandé par:</strong> {item.meta.overseerr_requested_by}
                  </div>
                )}
                {item.meta?.tags && item.meta.tags.length > 0 && (
                  <div>
                    <strong>Tags:</strong> {item.meta.tags.join(', ')}
                  </div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export default PlanItemRow

