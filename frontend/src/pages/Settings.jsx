import React, { useState, useEffect } from 'react'
import { getConfig, updateConfig } from '../api'
import { toast } from '../lib/toast'

function Settings() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const data = await getConfig()
      setConfig(data)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!config) return

    setSaving(true)
    try {
      await updateConfig(config)
      toast.success('Configuration sauvegardée avec succès')
    } catch (err) {
      toast.error(`Erreur: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-500">Chargement de la configuration...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-800">Erreur: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Paramètres</h1>
        <p className="text-gray-600">
          Configurez les services et les règles de suppression.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Services</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tautulli URL
            </label>
            <input
              type="text"
              value={config?.tautulli?.url || ''}
              onChange={(e) =>
                setConfig({
                  ...config,
                  tautulli: { ...config.tautulli, url: e.target.value },
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="http://192.168.1.59:8282"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Radarr URL
            </label>
            <input
              type="text"
              value={config?.radarr?.url || ''}
              onChange={(e) =>
                setConfig({
                  ...config,
                  radarr: { ...config.radarr, url: e.target.value },
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="http://192.168.1.59:7878"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sonarr URL
            </label>
            <input
              type="text"
              value={config?.sonarr?.url || ''}
              onChange={(e) =>
                setConfig({
                  ...config,
                  sonarr: { ...config.sonarr, url: e.target.value },
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="http://192.168.1.59:8989"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Règles</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Supprimer si non regardé depuis (jours)
            </label>
            <input
              type="number"
              value={config?.rules?.movies?.delete_if_not_watched_days || 60}
              onChange={(e) =>
                setConfig({
                  ...config,
                  rules: {
                    ...config.rules,
                    movies: {
                      ...config.rules?.movies,
                      delete_if_not_watched_days: parseInt(e.target.value),
                    },
                  },
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className={`
            px-6 py-2 rounded-lg font-medium text-white
            ${saving
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
            }
            transition-colors
          `}
        >
          {saving ? 'Sauvegarde...' : 'Sauvegarder'}
        </button>
      </div>
    </div>
  )
}

export default Settings

