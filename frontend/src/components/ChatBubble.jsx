import React from 'react'
import './ChatBubble.css'

/**
 * Renders a single chat message bubble.
 * role: 'user' | 'assistant'
 */
export default function ChatBubble({ role, text, remedySteps, isLoading }) {
  const isUser = role === 'user'

  return (
    <div className={`bubble-wrap ${isUser ? 'bubble-wrap--user' : 'bubble-wrap--assistant'}`}>
      {!isUser && (
        <span className="bubble-avatar" aria-hidden="true">🌾</span>
      )}

      <div className={`bubble ${isUser ? 'bubble--user' : 'bubble--assistant'}`}
           role="article"
           aria-label={`${isUser ? 'You' : 'Farmitra'}: ${isLoading ? 'loading' : text}`}>
        {isLoading ? (
          <span className="bubble-loading" aria-live="polite">
            <span /><span /><span />
          </span>
        ) : (
          <>
            <p className="bubble-text">{text}</p>
            {remedySteps?.length > 0 && (
              <div className="bubble-remedies">
                <p className="remedies-title">💊 Remedy Steps</p>
                <ol className="remedies-list">
                  {remedySteps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>
            )}
          </>
        )}
      </div>

      {isUser && (
        <span className="bubble-avatar bubble-avatar--user" aria-hidden="true">👤</span>
      )}
    </div>
  )
}
