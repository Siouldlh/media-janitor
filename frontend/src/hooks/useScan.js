import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { scan } from '../api'

const useScan = () => {
  const navigate = useNavigate()
  const [scanState, setScanState] = useState('idle') // idle, starting, running, completed, error
  const [scanId, setScanId] = useState(null)
  const [planId, setPlanId] = useState(null)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')
  const [logs, setLogs] = useState([])
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const pollIntervalRef = useRef(null)

  const startScan = async () => {
    try {
      setScanState('starting')
      setError(null)
      setProgress(0)
      setLogs([])
      
      const result = await scan()
      
      if (result.scan_id) {
        setScanId(result.scan_id)
        setScanState('running')
        connectWebSocket(result.scan_id)
        startPolling(result.scan_id)
      } else if (result.plan_id) {
        // Scan terminé immédiatement (fallback)
        setPlanId(result.plan_id)
        setScanState('completed')
        navigate(`/plans?planId=${result.plan_id}`)
      }
    } catch (err) {
      setError(err.message)
      setScanState('error')
    }
  }

  const connectWebSocket = (id) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/scan/${id}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.progress !== undefined) {
          setProgress(data.progress)
        }
        
        if (data.current_step) {
          setCurrentStep(data.current_step)
        }
        
        if (data.logs && Array.isArray(data.logs)) {
          setLogs(data.logs)
        }
        
        if (data.status === 'completed' && data.plan_id) {
          setPlanId(data.plan_id)
          setScanState('completed')
          setProgress(100)
          
          // Redirection automatique après un court délai
          setTimeout(() => {
            navigate(`/plans?planId=${data.plan_id}`)
          }, 1500)
        } else if (data.status === 'error') {
          setError(data.error || 'Scan failed')
          setScanState('error')
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err)
      }
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
      // Fallback sur polling si WebSocket échoue
    }

    ws.onclose = () => {
      console.log('WebSocket closed')
    }
  }

  const startPolling = (id) => {
    // Polling de secours si WebSocket ne fonctionne pas
    pollIntervalRef.current = setInterval(async () => {
      try {
        // Vérifier le statut via l'API si nécessaire
        // Pour l'instant, on se fie au WebSocket
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 2000)
  }

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      stopPolling()
    }
  }, [])

  return {
    scanState,
    scanId,
    planId,
    progress,
    currentStep,
    logs,
    error,
    startScan,
  }
}

export default useScan

