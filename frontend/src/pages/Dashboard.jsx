import React from 'react'
import useScan from '../hooks/useScan'
import ScanButton from '../components/scan/ScanButton'
import ScanProgress from '../components/scan/ScanProgress'

function Dashboard() {
  const {
    scanState,
    progress,
    currentStep,
    logs,
    error,
    startScan,
  } = useScan()

  const scanning = scanState === 'starting' || scanState === 'running'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
        <p className="text-gray-600">
          Lancez un scan pour analyser votre bibliothèque et générer un plan de suppression.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Nouveau scan</h2>
            <p className="text-sm text-gray-600 mt-1">
              Analysez vos films et séries pour identifier ceux à supprimer
            </p>
          </div>
          <ScanButton onScan={startScan} scanning={scanning} />
        </div>

        {scanning && (
          <div className="mt-6">
            <ScanProgress
              progress={progress}
              currentStep={currentStep}
              logs={logs}
              error={error}
            />
          </div>
        )}

        {scanState === 'completed' && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-green-800">
              ✓ Scan terminé avec succès. Redirection en cours...
            </p>
          </div>
        )}

        {scanState === 'error' && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">
              ✗ Erreur lors du scan : {error}
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Statut</h3>
          <p className="text-2xl font-bold text-gray-900">
            {scanState === 'idle' ? 'Prêt' : scanState === 'running' ? 'En cours' : 'Terminé'}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Dernier scan</h3>
          <p className="text-2xl font-bold text-gray-900">-</p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Plans actifs</h3>
          <p className="text-2xl font-bold text-gray-900">-</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard

