import React, { useState, useRef, useCallback } from 'react'
import './VoiceButton.css'

/**
 * Microphone button using browser-native Web Speech API.
 * onTranscript(text) is called when speech is recognized.
 * No external speech service — fully offline-capable.
 */
export default function VoiceButton({ onTranscript, disabled }) {
  const [listening, setListening]   = useState(false)
  const [supported]                  = useState(() =>
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)
  )
  const recogRef = useRef(null)

  const startListening = useCallback(() => {
    if (!supported || listening) return

    const SpeechRec =
      window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SpeechRec()
    recogRef.current = rec

    rec.continuous    = false
    rec.interimResults = false
    rec.lang          = 'en-IN'   // Indian English; farmer may use Hindi words too

    rec.onstart  = () => setListening(true)
    rec.onend    = () => setListening(false)
    rec.onerror  = () => setListening(false)

    rec.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join(' ')
        .trim()
      if (transcript) onTranscript(transcript)
    }

    rec.start()
  }, [supported, listening, onTranscript])

  const stopListening = useCallback(() => {
    recogRef.current?.stop()
    setListening(false)
  }, [])

  if (!supported) return null   // hide button if browser doesn't support it

  return (
    <button
      type="button"
      className={`voice-btn ${listening ? 'voice-btn--active' : ''}`}
      onClick={listening ? stopListening : startListening}
      disabled={disabled}
      aria-label={listening ? 'Stop recording' : 'Start voice input'}
      title={listening ? 'Stop recording' : 'Speak your question'}
    >
      {listening ? (
        <span className="mic-pulse" aria-hidden="true">🔴</span>
      ) : (
        <span aria-hidden="true">🎤</span>
      )}
      <span className="sr-only">{listening ? 'Recording…' : 'Voice input'}</span>
    </button>
  )
}
