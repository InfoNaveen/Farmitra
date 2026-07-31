import React, { useState, useEffect } from 'react'
import PriceChart from '../components/PriceChart'
import { getPriceTrend } from '../api'
import './PricesPage.css'

const CROPS = ['tomato', 'wheat', 'onion', 'potato', 'rice']
const CROP_ICONS = { tomato: '🍅', wheat: '🌾', onion: '🧅', potato: '🥔', rice: '🍚' }

export default function PricesPage() {
  const [selectedCrop, setSelectedCrop] = useState('tomato')
  const [priceData,    setPriceData]    = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setPriceData(null)

    getPriceTrend(selectedCrop)
      .then(({ data }) => { if (!cancelled) setPriceData(data) })
      .catch((err) => {
        if (!cancelled)
          setError(err.response?.data?.detail || 'Could not load price data.')
      })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [selectedCrop])

  return (
    <div className="prices-page">
      <section className="section">
        <h2 className="section-title">📈 Mandi Price Trends</h2>
        <p className="section-desc">
          Historical prices + 7-day forecast. Uses polynomial regression on
          simulated data — not real mandi prices.
        </p>

        <div className="crop-selector" role="group" aria-label="Select crop">
          {CROPS.map((c) => (
            <button
              key={c}
              className={`crop-btn ${selectedCrop === c ? 'crop-btn--active' : ''}`}
              onClick={() => setSelectedCrop(c)}
              aria-pressed={selectedCrop === c}
            >
            {CROP_ICONS[c] || '🌿'} {c.charAt(0).toUpperCase() + c.slice(1)}
            </button>
          ))}
        </div>
      </section>

      {loading && (
        <div className="status-banner status-banner--loading" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          Loading price data…
        </div>
      )}

      {error && (
        <div className="status-banner status-banner--error" role="alert">
          ⚠️ {error}
        </div>
      )}

      {priceData && <PriceChart data={priceData} />}

      {priceData && (
        <div className="forecast-table-card">
          <h3 className="forecast-table-title">📅 7-Day Price Forecast</h3>
          <table className="forecast-table" aria-label="7-day price forecast">
            <thead>
              <tr>
                <th>Date</th>
                <th>Forecast (₹/qtl)</th>
              </tr>
            </thead>
            <tbody>
              {priceData.forecast.map((row, i) => (
                <tr key={i}>
                  <td>{row.date}</td>
                  <td className="forecast-price">₹{row.price.toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
