import React, { useState } from 'react'
import AdvisorPanel from '../components/AdvisorPanel'
import { getAdvisorRecommendation } from '../api'
import './AdvisorPage.css'

const CROPS = ['tomato', 'wheat', 'onion', 'potato', 'rice']

export default function AdvisorPage() {
  const [selectedCrop, setSelectedCrop] = useState('tomato')
  const [location,     setLocation]     = useState('Maharashtra, India')
  const [result,       setResult]       = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState(null)

  const handleAnalyse = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const { data } = await getAdvisorRecommendation(selectedCrop, location)
      setResult(data)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Advisor failed. Check your OpenAI API key and backend connection.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="advisor-page">
      <section className="section">
        <h2 className="section-title">🤝 Sell / Hold Advisor</h2>
        <p className="section-desc">
          Our AI agent checks current prices, the weather forecast, and how
          long your crop can be stored — then gives you a clear recommendation.
        </p>
      </section>

      <div className="advisor-form">
        <div className="form-group">
          <label className="form-label" htmlFor="crop-select">Your crop</label>
          <div className="crop-chips" role="group" aria-label="Select crop">
            {CROPS.map((c) => (
              <button
                key={c}
                id={c === selectedCrop ? 'crop-select' : undefined}
                className={`crop-chip ${selectedCrop === c ? 'crop-chip--active' : ''}`}
                onClick={() => setSelectedCrop(c)}
                aria-pressed={selectedCrop === c}
              >
                {c.charAt(0).toUpperCase() + c.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="location-input">Your location</label>
          <input
            id="location-input"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Nashik, Maharashtra"
            className="location-input"
          />
        </div>

        <button
          className="analyse-btn"
          onClick={handleAnalyse}
          disabled={loading}
          aria-label="Get sell or hold recommendation"
        >
          {loading ? (
            <>
              <span className="btn-spinner" aria-hidden="true" />
              Analysing…
            </>
          ) : (
            '🔍 Get Recommendation'
          )}
        </button>
      </div>

      {error && (
        <div className="status-banner status-banner--error" role="alert">
          ⚠️ {error}
        </div>
      )}

      <AdvisorPanel result={result} isLoading={loading && !result} />

      {!result && !loading && (
        <div className="advisor-explainer">
          <h3>How it works</h3>
          <ul>
            <li>🔧 The AI agent calls <strong>3 tools</strong> automatically</li>
            <li>📊 <strong>Price trend</strong> — current market price + 7-day forecast</li>
            <li>🌤️ <strong>Weather forecast</strong> — rainfall &amp; temperature outlook</li>
            <li>⏱️ <strong>Storage life</strong> — how long can you hold without spoiling</li>
            <li>💡 It reasons over all three to give you a clear <em>Sell Now</em> or <em>Hold</em> decision</li>
          </ul>
          <p className="explainer-note">
            After getting the result, expand "Why?" to see the full agent reasoning trace.
          </p>
        </div>
      )}
    </div>
  )
}
