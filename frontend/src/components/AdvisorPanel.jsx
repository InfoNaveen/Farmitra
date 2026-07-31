import React, { useState } from 'react'
import './AdvisorPanel.css'

const TOOL_ICONS = {
  get_price_trend:      '📊',
  get_weather_forecast: '🌤️',
  get_perishability:    '⏱️',
}

const TOOL_LABELS = {
  get_price_trend:      'Price Trend',
  get_weather_forecast: 'Weather Forecast',
  get_perishability:    'Storage Life',
}

/**
 * Displays the sell/hold advisor result including the full LLM tool-call trace.
 * The reasoning trace is surfaced in a collapsible "Why?" section —
 * this is the most important demo element showing genuine tool-calling.
 */
export default function AdvisorPanel({ result, isLoading }) {
  const [traceOpen, setTraceOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="advisor-card advisor-card--loading" role="status" aria-live="polite">
        <div className="advisor-spinner" aria-hidden="true" />
        <p>Farmitra is checking prices, weather, and storage life…</p>
      </div>
    )
  }

  if (!result) return null

  const isSell = result.recommendation === 'Sell Now'

  return (
    <div className={`advisor-card ${isSell ? 'advisor-card--sell' : 'advisor-card--hold'}`}
         role="region" aria-label="Sell or Hold recommendation">

      {/* Main recommendation badge */}
      <div className="advisor-badge">
        <span className="advisor-badge-icon" aria-hidden="true">
          {isSell ? '🚀' : '⏳'}
        </span>
        <div>
          <p className="advisor-rec">{result.recommendation}</p>
          <p className="advisor-rec-sub">AI Recommendation</p>
        </div>
      </div>

      {/* Justification */}
      <p className="advisor-justification">{result.justification}</p>

      {/* Tool call reasoning trace — the star of the demo */}
      {result.tool_calls?.length > 0 && (
        <div className="reasoning-trace">
          <button
            className="trace-toggle"
            onClick={() => setTraceOpen((o) => !o)}
            aria-expanded={traceOpen}
            aria-controls="trace-body"
          >
            <span aria-hidden="true">{traceOpen ? '▾' : '▸'}</span>
            🔍 Why? — See agent reasoning ({result.tool_calls.length} tool calls)
          </button>

          {traceOpen && (
            <div id="trace-body" className="trace-body">
              {result.tool_calls.map((tc, i) => (
                <div key={i} className="trace-step">
                  <div className="trace-step-header">
                    <span className="trace-tool-icon" aria-hidden="true">
                      {TOOL_ICONS[tc.tool_name] || '🔧'}
                    </span>
                    <div>
                      <p className="trace-tool-name">
                        {TOOL_LABELS[tc.tool_name] || tc.tool_name}
                      </p>
                      <p className="trace-tool-fn">
                        <code>{tc.tool_name}({JSON.stringify(tc.arguments)})</code>
                      </p>
                    </div>
                  </div>
                  <TraceResult toolName={tc.tool_name} result={tc.result} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** Renders tool result in a human-friendly way */
function TraceResult({ toolName, result }) {
  if (result?.error) {
    return <p className="trace-result trace-result--error">⚠️ {result.error}</p>
  }

  if (toolName === 'get_price_trend') {
    return (
      <div className="trace-result">
        <p>Current: <strong>₹{result.current_price}/qtl</strong></p>
        <p>Trend: <strong style={{ textTransform: 'capitalize' }}>{result.trend}</strong></p>
        <p>7-day avg forecast: <strong>₹{result.avg_forecast}/qtl</strong></p>
        <p className="trace-note">{result.data_note}</p>
      </div>
    )
  }

  if (toolName === 'get_weather_forecast') {
    const source = result.source === 'mock_fallback' ? '(mock fallback)' : '(Open-Meteo)'
    return (
      <div className="trace-result">
        <p>Source: <strong>{source}</strong></p>
        {result.precipitation && (
          <p>
            Rain next 7 days: <strong>
              {result.precipitation.map((v) => `${v}mm`).join(', ')}
            </strong>
          </p>
        )}
        {result.temp_max && (
          <p>Max temps: <strong>{result.temp_max.map((v) => `${v}°C`).join(', ')}</strong></p>
        )}
      </div>
    )
  }

  if (toolName === 'get_perishability') {
    return (
      <div className="trace-result">
        <p>Perishability: <strong style={{ textTransform: 'capitalize' }}>{result.rating}</strong></p>
        <p>Storage life: <strong>~{result.days} days</strong></p>
        <p>{result.description}</p>
      </div>
    )
  }

  // Fallback: raw JSON
  return (
    <pre className="trace-result trace-result--json">
      {JSON.stringify(result, null, 2)}
    </pre>
  )
}
