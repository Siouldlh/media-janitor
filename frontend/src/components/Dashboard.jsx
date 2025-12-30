import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { scan } from '../api'
import './Dashboard.css'

function Dashboard() {
  const navigate = useNavigate()
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState(null)

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    try {
      const result = await scan()
      navigate(`/movies?plan=${result.plan_id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="container">
      <h1>Media Janitor</h1>
      <div className="card">
        <h2>Dashboard</h2>
        <p>Lancez un scan pour générer un plan de suppression.</p>
        {error && <div className="error">{error}</div>}
        <button
          className="btn btn-primary"
          onClick={handleScan}
          disabled={scanning}
        >
          {scanning ? 'Scan en cours...' : 'Lancer un scan'}
        </button>
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

