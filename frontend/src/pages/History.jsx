import React, { useState, useEffect } from 'react'
import { getRun, getRunLogs } from '../api'

function History() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedRun, setSelectedRun] = useState(null)
  const [runDetails, setRunDetails] = useState(null)

  useEffect(() => {
    loadRuns()
  }, [])

  const loadRuns = async () => {
    try {
      // TODO: Implement API endpoint to get all runs
      // For now, we'll show a placeholder
      setRuns([])
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const loadRunDetails = async (runId) => {
    try {
      const details = await getRun(runId)
      setRunDetails(details)
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-500">Chargement de l'historique...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-800">Erreur: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Historique</h1>
        <p className="text-gray-600">
          Consultez l'historique des exécutions de plans de suppression.
        </p>
      </div>

      {runs.length === 0 ? (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-500">Aucun historique disponible</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Résultats
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    #{run.id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(run.started_at).toLocaleString('fr-FR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`
                        inline-flex px-2 py-1 text-xs font-semibold rounded-full
                        ${run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : ''}
                        ${run.status === 'FAILED' ? 'bg-red-100 text-red-800' : ''}
                        ${run.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' : ''}
                      `}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {run.results?.success_count || 0} succès, {run.results?.failed_count || 0} échecs
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => {
                        setSelectedRun(run.id)
                        loadRunDetails(run.id)
                      }}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Détails
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedRun && runDetails && (
        <div className="mt-6 bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Détails de l'exécution #{selectedRun}
          </h2>
          <pre className="bg-gray-50 p-4 rounded-lg overflow-auto text-sm">
            {JSON.stringify(runDetails, null, 2)}
          </pre>
          <button
            onClick={() => {
              setSelectedRun(null)
              setRunDetails(null)
            }}
            className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            Fermer
          </button>
        </div>
      )}
    </div>
  )
}

export default History

