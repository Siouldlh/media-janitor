import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import Plans from './pages/Plans'
import History from './pages/History'
import Settings from './pages/Settings'
// Legacy routes for backward compatibility
import MoviesTab from './components/MoviesTab'
import SeriesTab from './components/SeriesTab'
import LegacyDashboard from './components/Dashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/plans" element={<Plans />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        {/* Legacy routes - redirect to new routes */}
        <Route path="/movies" element={<MoviesTab />} />
        <Route path="/series" element={<SeriesTab />} />
        <Route path="/dashboard-old" element={<LegacyDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

