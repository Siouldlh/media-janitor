import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDiagnostics } from '../api'
import './SettingsTab.css'

function SettingsTab() {
  const navigate = useNavigate()
  const [diagnostics, setDiagnostics] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadDiagnostics()
  }, [])

  const loadDiagnostics = async () => {
    setLoading(true)
    try {
      const data = await getDiagnostics()
      setDiagnostics(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>Paramètres</h1>
      <div className="tabs">
        <button className="tab" onClick={() => navigate('/')}>
          Dashboard
        </button>
        <button className="tab" onClick={() => navigate('/movies')}>
          Films
        </button>
        <button className="tab" onClick={() => navigate('/series')}>
          Séries
        </button>
        <button className="tab" onClick={() => navigate('/history')}>
          Historique
        </button>
        <button className="tab active" onClick={() => navigate('/settings')}>
          Paramètres
        </button>
      </div>

      <div className="card">
        <h2>Diagnostics des connexions</h2>
        <button className="btn btn-secondary" onClick={loadDiagnostics} disabled={loading}>
          {loading ? 'Vérification...' : 'Vérifier les connexions'}
        </button>
        {diagnostics && (
          <div className="diagnostics">
            <div className="diagnostic-item">
              <strong>Plex:</strong>{' '}
              {diagnostics.plex.connected ? (
                <span className="status-ok">✓ Connecté</span>
              ) : (
                <span className="status-error">✗ Erreur: {diagnostics.plex.error}</span>
              )}
            </div>
            <div className="diagnostic-item">
              <strong>Radarr:</strong>{' '}
              {diagnostics.radarr.connected ? (
                <span className="status-ok">✓ Connecté</span>
              ) : (
                <span className="status-error">✗ Erreur: {diagnostics.radarr.error}</span>
              )}
            </div>
            <div className="diagnostic-item">
              <strong>Sonarr:</strong>{' '}
              {diagnostics.sonarr.connected ? (
                <span className="status-ok">✓ Connecté</span>
              ) : (
                <span className="status-error">✗ Erreur: {diagnostics.sonarr.error}</span>
              )}
            </div>
            <div className="diagnostic-item">
              <strong>Overseerr:</strong>{' '}
              {diagnostics.overseerr.connected ? (
                <span className="status-ok">✓ Connecté</span>
              ) : (
                <span className="status-error">✗ Erreur: {diagnostics.overseerr.error}</span>
              )}
            </div>
            <div className="diagnostic-item">
              <strong>qBittorrent:</strong>{' '}
              {diagnostics.qbittorrent.connected ? (
                <span className="status-ok">✓ Connecté</span>
              ) : (
                <span className="status-error">✗ Erreur: {diagnostics.qbittorrent.error}</span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Configuration</h2>
        <p>La configuration se fait via le fichier <code>config.yaml</code> monté dans le container Docker.</p>
        <p>Consultez <code>config.example.yaml</code> pour un exemple de configuration.</p>
      </div>
    </div>
  )
}

export default SettingsTab

