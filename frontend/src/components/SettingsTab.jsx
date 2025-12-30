import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDiagnostics, getConfig, updateConfig } from '../api'
import './SettingsTab.css'

function SettingsTab() {
  const navigate = useNavigate()
  const [diagnostics, setDiagnostics] = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState(null)
  const [activeTab, setActiveTab] = useState('diagnostics') // 'diagnostics' ou 'config'

  useEffect(() => {
    loadDiagnostics()
    loadConfig()
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

  const loadConfig = async () => {
    try {
      const data = await getConfig()
      setConfig(data)
    } catch (err) {
      console.error(err)
    }
  }

  const handleConfigChange = (section, field, value) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }))
  }

  const handleNestedConfigChange = (section, nestedKey, field, value) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [nestedKey]: {
          ...prev[section][nestedKey],
          [field]: value
        }
      }
    }))
  }

  const handleArrayChange = (section, field, index, value) => {
    setConfig(prev => {
      const newArray = [...(prev[section][field] || [])]
      newArray[index] = value
      return {
        ...prev,
        [section]: {
          ...prev[section],
          [field]: newArray
        }
      }
    })
  }

  const handleAddArrayItem = (section, field, defaultValue = '') => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: [...(prev[section][field] || []), defaultValue]
      }
    }))
  }

  const handleRemoveArrayItem = (section, field, index) => {
    setConfig(prev => {
      const newArray = [...(prev[section][field] || [])]
      newArray.splice(index, 1)
      return {
        ...prev,
        [section]: {
          ...prev[section],
          [field]: newArray
        }
      }
    })
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveMessage(null)
    try {
      await updateConfig({
        rules: config.rules,
        scheduler: config.scheduler,
        app: config.app
      })
      setSaveMessage({ type: 'success', text: 'Configuration sauvegardée avec succès !' })
      // Recharger la config pour s'assurer qu'elle est à jour
      await loadConfig()
    } catch (err) {
      setSaveMessage({ type: 'error', text: err.message || 'Erreur lors de la sauvegarde' })
    } finally {
      setSaving(false)
      setTimeout(() => setSaveMessage(null), 5000)
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

      <div className="settings-tabs">
        <button
          className={`settings-tab ${activeTab === 'diagnostics' ? 'active' : ''}`}
          onClick={() => setActiveTab('diagnostics')}
        >
          Diagnostics
        </button>
        <button
          className={`settings-tab ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          Configuration
        </button>
      </div>

      {activeTab === 'diagnostics' && (
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
      )}

      {activeTab === 'config' && config && (
        <>
          <div className="card">
            <h2>Règles de suppression - Films</h2>
            <div className="form-group">
              <label>
                Stratégie de suppression:
                <select
                  value={config.rules?.movies?.strategy || 'not_watched_days'}
                  onChange={(e) => handleNestedConfigChange('rules', 'movies', 'strategy', e.target.value)}
                >
                  <option value="never_watched_only">Uniquement jamais regardés</option>
                  <option value="not_watched_days">Jamais regardés OU non regardés depuis X jours</option>
                </select>
              </label>
              <small>
                {config.rules?.movies?.strategy === 'never_watched_only'
                  ? 'Supprime uniquement les films jamais regardés'
                  : 'Supprime les films jamais regardés OU non regardés depuis X jours'}
              </small>
            </div>
            <div className="form-group">
              <label>
                Jours depuis le dernier visionnage (si strategy = "not_watched_days"):
                <input
                  type="number"
                  value={config.rules?.movies?.delete_if_not_watched_days || 60}
                  onChange={(e) => handleNestedConfigChange('rules', 'movies', 'delete_if_not_watched_days', parseInt(e.target.value))}
                  min="1"
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Jours depuis l'ajout si jamais regardé:
                <input
                  type="number"
                  value={config.rules?.movies?.if_never_watched_use_added_days || 60}
                  onChange={(e) => handleNestedConfigChange('rules', 'movies', 'if_never_watched_use_added_days', parseInt(e.target.value))}
                  min="1"
                />
              </label>
            </div>
          </div>

          <div className="card">
            <h2>Règles de suppression - Séries</h2>
            <div className="form-group">
              <label>
                Jours d'inactivité pour supprimer une série entière:
                <input
                  type="number"
                  value={config.rules?.series?.delete_entire_series_if_inactive_days || 120}
                  onChange={(e) => handleNestedConfigChange('rules', 'series', 'delete_entire_series_if_inactive_days', parseInt(e.target.value))}
                  min="1"
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Jours depuis le dernier visionnage pour supprimer un épisode:
                <input
                  type="number"
                  value={config.rules?.series?.delete_episodes_not_watched_days || 60}
                  onChange={(e) => handleNestedConfigChange('rules', 'series', 'delete_episodes_not_watched_days', parseInt(e.target.value))}
                  min="1"
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Garder les N derniers épisodes:
                <input
                  type="number"
                  value={config.rules?.series?.keep_last_n_episodes || 0}
                  onChange={(e) => handleNestedConfigChange('rules', 'series', 'keep_last_n_episodes', parseInt(e.target.value))}
                  min="0"
                />
              </label>
            </div>
          </div>

          <div className="card">
            <h2>Paramètres de l'application</h2>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.app?.dry_run_default || false}
                  onChange={(e) => handleConfigChange('app', 'dry_run_default', e.target.checked)}
                />
                Mode dry-run par défaut
              </label>
            </div>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.app?.require_manual_approval || false}
                  onChange={(e) => handleConfigChange('app', 'require_manual_approval', e.target.checked)}
                />
                Requérir approbation manuelle
              </label>
            </div>
            <div className="form-group">
              <label>
                Phrase de confirmation (optionnel, laisser vide pour désactiver):
                <input
                  type="text"
                  value={config.app?.require_confirm_phrase || ''}
                  onChange={(e) => handleConfigChange('app', 'require_confirm_phrase', e.target.value || null)}
                  placeholder="Ex: DELETE"
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Limite d'items par scan (laisser vide pour pas de limite):
                <input
                  type="number"
                  value={config.app?.max_items_per_scan || ''}
                  onChange={(e) => handleConfigChange('app', 'max_items_per_scan', e.target.value ? parseInt(e.target.value) : null)}
                  min="1"
                  placeholder="null"
                />
              </label>
            </div>
            <div className="form-group">
              <label>Chemins exclus:</label>
              {(config.app?.excluded_paths || []).map((path, index) => (
                <div key={index} className="array-item">
                  <input
                    type="text"
                    value={path}
                    onChange={(e) => handleArrayChange('app', 'excluded_paths', index, e.target.value)}
                    placeholder="/chemin/a/exclure"
                  />
                  <button
                    className="btn btn-small btn-danger"
                    onClick={() => handleRemoveArrayItem('app', 'excluded_paths', index)}
                  >
                    Supprimer
                  </button>
                </div>
              ))}
              <button
                className="btn btn-small btn-secondary"
                onClick={() => handleAddArrayItem('app', 'excluded_paths', '')}
              >
                + Ajouter un chemin
              </button>
            </div>
          </div>

          <div className="card">
            <h2>Planificateur automatique</h2>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.scheduler?.enabled || false}
                  onChange={(e) => handleConfigChange('scheduler', 'enabled', e.target.checked)}
                />
                Activer le planificateur automatique
              </label>
            </div>
            <div className="form-group">
              <label>
                Fréquence:
                <input
                  type="text"
                  value={config.scheduler?.cadence || '1 day'}
                  onChange={(e) => handleConfigChange('scheduler', 'cadence', e.target.value)}
                  placeholder="Ex: 1 day, 2 days, 1 week"
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Fuseau horaire:
                <input
                  type="text"
                  value={config.scheduler?.timezone || 'Europe/Paris'}
                  onChange={(e) => handleConfigChange('scheduler', 'timezone', e.target.value)}
                  placeholder="Europe/Paris"
                />
              </label>
            </div>
          </div>

          {saveMessage && (
            <div className={`message ${saveMessage.type === 'success' ? 'message-success' : 'message-error'}`}>
              {saveMessage.text}
            </div>
          )}

          <div className="card">
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Sauvegarde...' : 'Sauvegarder la configuration'}
            </button>
            <p className="help-text">
              Note: Les URLs et clés API ne peuvent pas être modifiées depuis l'interface pour des raisons de sécurité.
              Modifiez-les directement dans le fichier config.yaml.
            </p>
          </div>
        </>
      )}
    </div>
  )
}

export default SettingsTab
