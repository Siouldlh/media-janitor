import React, { useState } from 'react'
import { HiChevronDown, HiChevronUp } from 'react-icons/hi2'

const stepLabels = {
  'initializing': 'Initialisation...',
  'tautulli_fetching': 'Récupération Tautulli...',
  'tautulli_fetched': 'Tautulli récupéré',
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

function ScanProgress({ progress, currentStep, logs, error }) {
  const [showLogs, setShowLogs] = useState(false)

  const getStepLabel = (step) => {
    return stepLabels[step] || step
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900">Scan en cours</h3>
          <span className="text-sm font-medium text-gray-600">{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className="bg-blue-600 h-full rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-2 text-sm text-gray-600">{getStepLabel(currentStep)}</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {logs.length > 0 && (
        <div>
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="flex items-center justify-between w-full text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            <span>Logs ({logs.length})</span>
            {showLogs ? (
              <HiChevronUp className="h-5 w-5" />
            ) : (
              <HiChevronDown className="h-5 w-5" />
            )}
          </button>
          {showLogs && (
            <div className="mt-2 bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
              <div className="space-y-1 font-mono text-xs">
                {logs.slice(-20).map((log, index) => (
                  <div
                    key={index}
                    className={`${
                      log.level === 'error' ? 'text-red-600' : 'text-gray-700'
                    }`}
                  >
                    <span className="text-gray-500">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>{' '}
                    {log.message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ScanProgress

