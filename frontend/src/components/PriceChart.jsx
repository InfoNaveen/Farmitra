import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import './PriceChart.css'

const TREND_LABELS = {
  rising:  { icon: '📈', text: 'Rising',  color: '#16a34a' },
  falling: { icon: '📉', text: 'Falling', color: '#dc2626' },
  stable:  { icon: '➡️', text: 'Stable',  color: '#d97706' },
}

/**
 * Renders the 90-day history + 7-day forecast line chart.
 * Uses recharts for a lightweight, responsive chart.
 * DATA NOTE: prices are SIMULATED — disclosed in tooltip and card.
 */
export default function PriceChart({ data }) {
  if (!data) return null

  const { crop, history, forecast, current_price, trend_direction, note } = data
  const trend = TREND_LABELS[trend_direction] || TREND_LABELS.stable

  // Merge history + forecast, mark forecast points
  const chartData = [
    ...history.map((p) => ({ date: p.date.slice(5), price: p.price, type: 'history' })),
    ...forecast.map((p) => ({ date: p.date.slice(5), forecast: p.price, type: 'forecast' })),
  ]

  // Date where forecast begins
  const forecastStart = history.length > 0 ? history[history.length - 1].date.slice(5) : null

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="chart-tooltip">
        <p className="chart-tooltip-date">{label}</p>
        {payload.map((p) => (
          <p key={p.dataKey} style={{ color: p.color }}>
            {p.dataKey === 'price' ? 'Actual' : 'Forecast'}: ₹{p.value?.toFixed(0)}/qtl
          </p>
        ))}
        <p className="chart-tooltip-note">Simulated data</p>
      </div>
    )
  }

  return (
    <div className="price-chart-card">
      <div className="price-chart-header">
        <div>
          <h2 className="price-chart-title">
            {crop.charAt(0).toUpperCase() + crop.slice(1)} — Mandi Price Trend
          </h2>
          <p className="price-chart-subtitle">Last 90 days + 7-day forecast</p>
        </div>
        <div className="price-meta">
          <div className="current-price">
            <span className="current-price-label">Current</span>
            <span className="current-price-value">₹{current_price.toLocaleString('en-IN')}</span>
            <span className="current-price-unit">/qtl</span>
          </div>
          <div className="trend-badge" style={{ color: trend.color }}>
            {trend.icon} {trend.text}
          </div>
        </div>
      </div>

      <div className="chart-wrap" role="img" aria-label={`Price trend chart for ${crop}`}>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: 'var(--gray-500)' }}
              interval={14}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: 'var(--gray-500)' }}
              tickFormatter={(v) => `₹${v}`}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="line"
              formatter={(v) => v === 'price' ? 'Actual price' : '7-day forecast'}
              wrapperStyle={{ fontSize: '0.8rem' }}
            />
            {forecastStart && (
              <ReferenceLine
                x={forecastStart}
                stroke="var(--gray-300)"
                strokeDasharray="4 2"
                label={{ value: 'Today', position: 'insideTopRight', fontSize: 10, fill: 'var(--gray-500)' }}
              />
            )}
            <Line
              type="monotone"
              dataKey="price"
              stroke="var(--primary)"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4, fill: 'var(--primary-dark)' }}
            />
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="var(--primary-light)"
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={{ r: 3, fill: 'var(--accent)' }}
              activeDot={{ r: 5, fill: 'var(--accent)' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="chart-disclaimer">⚠️ {note}</p>
    </div>
  )
}
