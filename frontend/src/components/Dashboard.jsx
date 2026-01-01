import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { scan } from '../api'
import ScanProgress from './ScanProgress'
import './Dashboard.css'

function Dashboard() {
  const navigate = useNavigate()
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState(null)
  const [scanId, setScanId] = useState(null)

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    setScanId(null)
    try {
      const result = await scan()
      if (result.scan_id) {
        // Scan avec progression en temps réel
        setScanId(result.scan_id)
      } else if (result.plan_id) {
        // Scan terminé immédiatement (fallback)
        navigate(`/movies?plan=${result.plan_id}`)
        setScanning(false)
      }
    } catch (err) {
      setError(err.message)
      setScanning(false)
    }
  }

  const handleScanComplete = (planId) => {
    setScanning(false)
    navigate(`/movies?plan=${planId}`)
  }

  const handleScanError = (errorMessage) => {
    setError(errorMessage)
    setScanning(false)
    setScanId(null)
  }

  return (
    <div className="container">
      <h1>Media Janitor</h1>
      <div className="card">
        <h2>Dashboard</h2>
        <p>Lancez un scan pour générer un plan de suppression.</p>
        {error && <div className="error">{error}</div>}
        {!scanning && (
          <button
            className="btn btn-primary"
            onClick={handleScan}
            disabled={scanning}
          >
            Lancer un scan
          </button>
        )}
        {scanning && scanId && (
          <ScanProgress
            scanId={scanId}
            onComplete={handleScanComplete}
            onError={handleScanError}
          />
        )}
        {scanning && !scanId && (
          <div className="scan-loading">Initialisation du scan...</div>
        )}
      </div>
      <div className="tabs">
        <button className="tab active" onClick={() => navigate('/')}>
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
        <button className="tab" onClick={() => navigate('/settings')}>
          Paramètres
        </button>
      </div>
    </div>
  )
}

export default Dashboard


