import React from 'react'
import './Header.css'

export default function Header({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'diagnose', label: '🌿 Diagnose', title: 'Crop Disease Scan' },
    { id: 'prices',   label: '📈 Prices',   title: 'Mandi Price Trend' },
    { id: 'advisor',  label: '🤝 Advisor',  title: 'Sell / Hold Advisor' },
  ]

  return (
    <header className="app-header">
      <div className="header-brand">
        <span className="brand-icon" aria-hidden="true">🌾</span>
        <div>
          <h1 className="brand-name">Farmitra</h1>
          <p className="brand-tagline">AI Farm Companion</p>
        </div>
      </div>

      <nav className="tab-nav" role="tablist" aria-label="Main navigation">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={activeTab === t.id}
            aria-label={t.title}
            className={`tab-btn ${activeTab === t.id ? 'tab-btn--active' : ''}`}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
    </header>
  )
}
