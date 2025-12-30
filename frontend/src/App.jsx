import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import MoviesTab from './components/MoviesTab'
import SeriesTab from './components/SeriesTab'
import HistoryTab from './components/HistoryTab'
import SettingsTab from './components/SettingsTab'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/movies" element={<MoviesTab />} />
        <Route path="/series" element={<SeriesTab />} />
        <Route path="/history" element={<HistoryTab />} />
        <Route path="/settings" element={<SettingsTab />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

