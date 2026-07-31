import React from 'react'
import './DiagnosisCard.css'

/**
 * Displays the HuggingFace plant disease prediction result.
 */
export default function DiagnosisCard({ result, imageUrl }) {
  if (!result) return null

  const pct = (result.confidence_score * 100).toFixed(1)
  const severity =
    result.confidence_score >= 0.8 ? 'high' :
    result.confidence_score >= 0.5 ? 'medium' : 'low'

  return (
    <div className="diagnosis-card" role="region" aria-label="Diagnosis result">
      {imageUrl && (
        <div className="diagnosis-img-wrap">
          <img src={imageUrl} alt="Uploaded crop" className="diagnosis-img" />
        </div>
      )}

      <div className="diagnosis-body">
        <div className="diagnosis-label-row">
          <span className="diagnosis-icon" aria-hidden="true">
            {severity === 'high' ? '🔴' : severity === 'medium' ? '🟡' : '🟢'}
          </span>
          <div>
            <p className="diagnosis-label">{result.disease_label}</p>
            <p className="diagnosis-sub">Top prediction</p>
          </div>
        </div>

        <div className="confidence-bar-wrap" aria-label={`Confidence: ${pct}%`}>
          <div className="confidence-bar-track">
            <div
              className={`confidence-bar-fill confidence-bar-fill--${severity}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="confidence-label">{pct}% confidence</span>
        </div>

        {result.top_predictions?.length > 1 && (
          <details className="other-preds">
            <summary>Other possibilities</summary>
            <ul className="other-preds-list">
              {result.top_predictions.slice(1).map((p, i) => (
                <li key={i}>
                  <span>{p.label}</span>
                  <span className="pred-score">{(p.score * 100).toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  )
}
