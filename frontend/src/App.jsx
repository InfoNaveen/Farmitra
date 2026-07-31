import React, { useState, useEffect } from 'react'
import Header from './components/Header'
import DiagnosePage from './pages/DiagnosePage'
import PricesPage from './pages/PricesPage'
import AdvisorPage from './pages/AdvisorPage'
import { checkHealth } from './api'
import './App.css'

export default function App() {
  const [activeTab,     setActiveTab]     = useState('diagnose')
  const [backendOnline, setBackendOnline] = useState(null)  // null = unknown

  // Health-check on mount — purely informational, never blocks the UI
  useEffect(() => {
    checkHealth()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false))
  }, [])

  return (
    <div className="app">
      <Header activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Backend offline banner — non-blocking */}
      {backendOnline === false && (
        <div className="offline-banner" role="alert">
          ⚠️ Backend not reachable at <code>localhost:8000</code> — start it with{' '}
          <code>uvicorn main:app --reload</code> in the <code>farmitra-backend/</code> folder.
        </div>
      )}

      <main className="app-main" role="main">
        {activeTab === 'diagnose' && <DiagnosePage />}
        {activeTab === 'prices'   && <PricesPage />}
        {activeTab === 'advisor'  && <AdvisorPage />}
      </main>

      <footer className="app-footer">
        <p>
          Farmitra — AI Farm Companion &nbsp;·&nbsp;
          <span className="footer-note">
            Disease model: MobileNetV2 / PlantVillage (HuggingFace) &nbsp;·&nbsp;
            Price data: simulated
          </span>
        </p>
      </footer>
    </div>
  )
}
