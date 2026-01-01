import React from 'react'

// Simple toast notification system
class ToastManager {
  constructor() {
    this.toasts = []
    this.listeners = []
  }

  subscribe(listener) {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  notify(toast) {
    const id = Date.now()
    const newToast = { ...toast, id }
    this.toasts.push(newToast)
    this.listeners.forEach(listener => listener([...this.toasts]))

    // Auto remove after 5 seconds
    setTimeout(() => {
      this.remove(id)
    }, 5000)

    return id
  }

  remove(id) {
    this.toasts = this.toasts.filter(t => t.id !== id)
    this.listeners.forEach(listener => listener([...this.toasts]))
  }

  success(message) {
    return this.notify({ type: 'success', message })
  }

  error(message) {
    return this.notify({ type: 'error', message })
  }

  info(message) {
    return this.notify({ type: 'info', message })
  }

  warning(message) {
    return this.notify({ type: 'warning', message })
  }
}

export const toast = new ToastManager()

// React component for displaying toasts
export function ToastContainer() {
  const [toasts, setToasts] = React.useState([])

  React.useEffect(() => {
    return toast.subscribe(setToasts)
  }, [])

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`
            px-4 py-3 rounded-lg shadow-lg min-w-[300px] max-w-md
            ${t.type === 'success' ? 'bg-green-50 border border-green-200 text-green-800' : ''}
            ${t.type === 'error' ? 'bg-red-50 border border-red-200 text-red-800' : ''}
            ${t.type === 'info' ? 'bg-blue-50 border border-blue-200 text-blue-800' : ''}
            ${t.type === 'warning' ? 'bg-yellow-50 border border-yellow-200 text-yellow-800' : ''}
          `}
        >
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">{t.message}</p>
            <button
              onClick={() => toast.remove(t.id)}
              className="ml-4 text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

