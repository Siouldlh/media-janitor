import React, { useState } from 'react'

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function ConfirmationModal({ onConfirm, onCancel, requirePhrase, selectedCount, itemCount, totalSize }) {
  const [confirmPhrase, setConfirmPhrase] = useState('')

  const handleConfirm = () => {
    if (requirePhrase && confirmPhrase !== requirePhrase) {
      alert('Phrase de confirmation incorrecte')
      return
    }
    onConfirm(confirmPhrase)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Confirmer la suppression
        </h2>
        <p className="text-gray-700 mb-4">
          Vous êtes sur le point de supprimer <strong>{itemCount || selectedCount}</strong> item{(itemCount || selectedCount) > 1 ? 's' : ''}.
          Cette action est irréversible.
        </p>
        {totalSize && (
          <p className="text-gray-600 mb-4 text-sm">
            Taille totale : {formatSize(totalSize)}
          </p>
        )}
        {requirePhrase && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tapez "{requirePhrase}" pour confirmer :
            </label>
            <input
              type="text"
              value={confirmPhrase}
              onChange={(e) => setConfirmPhrase(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder={requirePhrase}
            />
          </div>
        )}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleConfirm}
            disabled={requirePhrase && confirmPhrase !== requirePhrase}
            className={`
              px-4 py-2 text-white rounded-lg transition-colors
              ${requirePhrase && confirmPhrase !== requirePhrase
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-red-600 hover:bg-red-700'
              }
            `}
          >
            Confirmer
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmationModal
