import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { getRun, getRunLogs } from '../api'
import './HistoryTab.css'

function HistoryTab() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const runId = searchParams.get('run')
  const [run, setRun] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (runId) {
      loadRun()
    }
  }, [runId])

  const loadRun = async () => {
    setLoading(true)
    try {
      const runData = await getRun(runId)
      setRun(runData)
      const logsData = await getRunLogs(runId)
      setLogs(logsData.logs || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>Historique</h1>
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
        <button className="tab active" onClick={() => navigate('/history')}>
          Historique
        </button>
        <button className="tab" onClick={() => navigate('/settings')}>
          Paramètres
        </button>
      </div>

      {runId && run ? (
        <div className="card">
          <h2>Run #{run.id}</h2>
          <p>Statut: <strong>{run.status}</strong></p>
          <p>Démarré: {new Date(run.started_at).toLocaleString('fr-FR')}</p>
          {run.finished_at && (
            <p>Terminé: {new Date(run.finished_at).toLocaleString('fr-FR')}</p>
          )}
          <div className="stats">
            <div className="stat-item">
              <div className="stat-value">{run.results.success_count || 0}</div>
              <div className="stat-label">Succès</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{run.results.failed_count || 0}</div>
              <div className="stat-label">Échecs</div>
            </div>
          </div>
          {logs.length > 0 && (
            <div>
              <h3>Logs</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Statut</th>
                    <th>qB</th>
                    <th>Radarr/Sonarr</th>
                    <th>Plex</th>
                    <th>Erreur</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, idx) => (
                    <tr key={idx}>
                      <td>{log.title}</td>
                      <td>{log.status}</td>
                      <td>{log.qb_removed ? '✓' : '-'}</td>
                      <td>{log.radarr_sonarr_removed ? '✓' : '-'}</td>
                      <td>{log.plex_refreshed ? '✓' : '-'}</td>
                      <td>{log.error || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <p>Pas de run sélectionné. Les runs apparaîtront ici après l'exécution d'un plan.</p>
        </div>
      )}
    </div>
  )
}

export default HistoryTab

