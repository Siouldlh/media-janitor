import React, { useState, useEffect } from 'react'
import './ConfirmationModal.css'

function ConfirmationModal({ itemCount, totalSize, onConfirm, onCancel, requireConfirmPhrase }) {
  const [confirmPhrase, setConfirmPhrase] = useState('')
  const [canConfirm, setCanConfirm] = useState(false)

  useEffect(() => {
    if (requireConfirmPhrase) {
      setCanConfirm(confirmPhrase === requireConfirmPhrase)
    } else {
      setCanConfirm(true)
    }
  }, [confirmPhrase, requireConfirmPhrase])

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Confirmation de suppression</h2>
          <button className="close-btn" onClick={onCancel}>×</button>
        </div>
        <div className="modal-body">
          <p><strong>Attention:</strong> Cette action est irréversible.</p>
          <div className="confirmation-stats">
            <div className="stat-item">
              <div className="stat-value">{itemCount}</div>
              <div className="stat-label">Items à supprimer</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{formatSize(totalSize)}</div>
              <div className="stat-label">Taille totale</div>
            </div>
          </div>
          <div className="confirmation-steps">
            <h3>Ordre d'exécution:</h3>
            <ol>
              <li>Suppression des torrents qBittorrent (cross-seed)</li>
              <li>Suppression via Radarr/Sonarr (fichiers + DB)</li>
              <li>Rafraîchissement Plex (optionnel)</li>
            </ol>
          </div>
        </div>
        {requireConfirmPhrase && (
          <div className="confirm-phrase-section">
            <label>
              Tapez <strong>{requireConfirmPhrase}</strong> pour confirmer :
            </label>
            <input
              type="text"
              value={confirmPhrase}
              onChange={(e) => setConfirmPhrase(e.target.value)}
              placeholder={requireConfirmPhrase}
              className="confirm-phrase-input"
            />
          </div>
        )}
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onCancel}>
            Annuler
          </button>
          <button
            className="btn btn-danger"
            onClick={() => onConfirm(confirmPhrase)}
            disabled={!canConfirm}
          >
            Confirmer et appliquer
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmationModal

