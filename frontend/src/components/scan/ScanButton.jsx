import React from 'react'
import { HiPlay } from 'react-icons/hi2'

function ScanButton({ onScan, scanning, disabled }) {
  return (
    <button
      onClick={onScan}
      disabled={disabled || scanning}
      className={`
        inline-flex items-center px-6 py-3 rounded-lg font-medium
        transition-all duration-200
        ${scanning
          ? 'bg-gray-400 cursor-not-allowed'
          : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
        }
        text-white shadow-lg hover:shadow-xl
        disabled:opacity-50 disabled:cursor-not-allowed
      `}
    >
      <HiPlay className={`mr-2 h-5 w-5 ${scanning ? 'animate-pulse' : ''}`} />
      {scanning ? 'Scan en cours...' : 'Nouveau scan'}
    </button>
  )
}

export default ScanButton

