import React, { useState, useEffect, useRef } from 'react'
import './ScanProgress.css'

function ScanProgress({ scanId, onComplete, onError }) {
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('initializing')
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState('running')
  const wsRef = useRef(null)

  useEffect(() => {
    if (!scanId) return

    // Connecter au WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/scan/${scanId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setProgress(data.progress || 0)
      setCurrentStep(data.current_step || 'unknown')
      setStatus(data.status || 'running')
      
      if (data.logs && data.logs.length > 0) {
        setLogs(data.logs)
      }
      
      if (data.status === 'completed' && data.plan_id) {
        setTimeout(() => {
          if (onComplete) onComplete(data.plan_id)
        }, 1000)
      } else if (data.status === 'error') {
        if (onError) onError(data.error || 'Scan failed')
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      if (onError) onError('Connection error')
    }

    ws.onclose = () => {
      console.log('WebSocket closed')
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [scanId, onComplete, onError])

  const stepLabels = {
    'initializing': 'Initialisation...',
    'plex_fetching': 'Récupération Plex...',
    'plex_fetched': 'Plex récupéré',
    'radarr_fetching': 'Récupération Radarr...',
    'radarr_fetched': 'Radarr récupéré',
    'sonarr_fetching': 'Récupération Sonarr...',
    'sonarr_fetched': 'Sonarr récupéré',
    'overseerr_fetching': 'Récupération Overseerr...',
    'overseerr_fetched': 'Overseerr récupéré',
    'qbittorrent_fetching': 'Récupération qBittorrent...',
    'qbittorrent_fetched': 'qBittorrent récupéré',
    'matching_started': 'Matching en cours...',
    'matching_completed': 'Matching terminé',
    'rules_evaluating': 'Évaluation des règles...',
    'rules_evaluated': 'Règles évaluées',
    'plan_creating': 'Création du plan...',
    'plan_created': 'Plan créé',
    'completed': 'Terminé',
    'error': 'Erreur'
  }

  const getStepLabel = (step) => {
    return stepLabels[step] || step
  }

  return (
    <div className="scan-progress">
      <div className="progress-header">
        <h3>Scan en cours...</h3>
        <div className="progress-bar-container">
          <div className="progress-bar" style={{ width: `${progress}%` }}></div>
          <span className="progress-text">{progress}%</span>
        </div>
        <div className="current-step">{getStepLabel(currentStep)}</div>
      </div>
      
      <div className="progress-logs">
        <h4>Logs</h4>
        <div className="logs-container">
          {logs.slice(-20).map((log, index) => (
            <div key={index} className={`log-entry log-${log.level || 'info'}`}>
              <span className="log-time">{new Date(log.timestamp).toLocaleTimeString()}</span>
              <span className="log-message">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
      
      {status === 'error' && (
        <div className="error-message">
          Une erreur s'est produite pendant le scan. Consultez les logs pour plus de détails.
        </div>
      )}
    </div>
  )
}

export default ScanProgress

