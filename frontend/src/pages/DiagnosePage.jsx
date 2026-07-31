import React, { useState, useRef, useCallback } from 'react'
import PhotoUpload from '../components/PhotoUpload'
import DiagnosisCard from '../components/DiagnosisCard'
import ChatBubble from '../components/ChatBubble'
import VoiceButton from '../components/VoiceButton'
import { diagnoseImage, explainDiagnosis } from '../api'
import './DiagnosePage.css'

/**
 * Full vertical slice: photo upload → AI diagnosis → chatbot explanation.
 * Chat also accepts free-form typed/voice questions about the diagnosis.
 */
export default function DiagnosePage() {
  const [imageFile,   setImageFile]   = useState(null)
  const [imageUrl,    setImageUrl]    = useState(null)
  const [diagnosis,   setDiagnosis]   = useState(null)
  const [diagLoading, setDiagLoading] = useState(false)
  const [diagError,   setDiagError]   = useState(null)

  const [messages,    setMessages]    = useState([])
  const [chatInput,   setChatInput]   = useState('')
  const [chatLoading, setChatLoading] = useState(false)

  const chatEndRef = useRef(null)

  const scrollToBottom = () =>
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)

  // ---- Step 1: upload photo → diagnose ----
  const handleFileSelected = useCallback(async (file) => {
    setImageFile(file)
    setImageUrl(URL.createObjectURL(file))
    setDiagnosis(null)
    setDiagError(null)
    setMessages([])
    setDiagLoading(true)

    try {
      const { data } = await diagnoseImage(file)
      setDiagnosis(data)

      // Auto-trigger chatbot explanation once we have a diagnosis
      await fetchExplanation(data, null, file)
    } catch (err) {
      setDiagError(
        err.response?.data?.detail || 'Diagnosis failed. Is the backend running?'
      )
    } finally {
      setDiagLoading(false)
    }
  }, [])

  // ---- Step 2: chatbot explanation ----
  const fetchExplanation = useCallback(
    async (diagnosisData, userQuestion, file) => {
      const diag = diagnosisData || diagnosis
      if (!diag) return

      if (userQuestion) {
        setMessages((prev) => [
          ...prev,
          { role: 'user', text: userQuestion },
        ])
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: '', isLoading: true },
      ])
      setChatLoading(true)
      scrollToBottom()

      try {
        const { data } = await explainDiagnosis({
          disease_label:    diag.disease_label,
          confidence_score: diag.confidence_score,
          user_question:    userQuestion || null,
        })

        setMessages((prev) => {
          const updated = [...prev]
          const lastIdx = updated.map((m) => m.isLoading).lastIndexOf(true)
          if (lastIdx !== -1) {
            updated[lastIdx] = {
              role:        'assistant',
              text:        data.explanation,
              remedySteps: data.remedy_steps,
              isLoading:   false,
            }
          }
          return updated
        })
      } catch (err) {
        setMessages((prev) => {
          const updated = [...prev]
          const lastIdx = updated.map((m) => m.isLoading).lastIndexOf(true)
          if (lastIdx !== -1) {
            updated[lastIdx] = {
              role:      'assistant',
              text:      'Sorry, I could not get an explanation right now. Please check your OpenAI API key.',
              isLoading: false,
            }
          }
          return updated
        })
      } finally {
        setChatLoading(false)
        scrollToBottom()
      }
    },
    [diagnosis]
  )

  // ---- Step 3: follow-up chat (typed or voice) ----
  const handleSendMessage = useCallback(
    async (text) => {
      const msg = (text || chatInput).trim()
      if (!msg || chatLoading) return
      setChatInput('')
      await fetchExplanation(diagnosis, msg, null)
    },
    [chatInput, chatLoading, diagnosis, fetchExplanation]
  )

  const handleVoiceTranscript = useCallback(
    (transcript) => {
      setChatInput(transcript)
    },
    []
  )

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="diagnose-page">
      {/* Upload zone */}
      <section className="section" aria-label="Photo upload">
        <h2 className="section-title">📷 Scan Your Crop</h2>
        <PhotoUpload onFileSelected={handleFileSelected} disabled={diagLoading} />
      </section>

      {/* Loading state */}
      {diagLoading && (
        <div className="status-banner status-banner--loading" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          Analysing your crop photo…
        </div>
      )}

      {/* Error state */}
      {diagError && (
        <div className="status-banner status-banner--error" role="alert">
          ⚠️ {diagError}
        </div>
      )}

      {/* Diagnosis result card */}
      {diagnosis && <DiagnosisCard result={diagnosis} imageUrl={imageUrl} />}

      {/* Chat interface */}
      {(messages.length > 0 || diagnosis) && (
        <section className="chat-section" aria-label="AI explanation chat">
          <h2 className="section-title">💬 AI Farm Advisor</h2>

          <div className="chat-messages" role="log" aria-live="polite" aria-label="Chat messages">
            {messages.map((msg, i) => (
              <ChatBubble
                key={i}
                role={msg.role}
                text={msg.text}
                remedySteps={msg.remedySteps}
                isLoading={msg.isLoading}
              />
            ))}
            <div ref={chatEndRef} />
          </div>

          {diagnosis && (
            <div className="chat-input-row">
              <textarea
                className="chat-input"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a follow-up question… or tap the mic 🎤"
                rows={2}
                disabled={chatLoading}
                aria-label="Type your question"
              />
              <div className="chat-actions">
                <VoiceButton
                  onTranscript={handleVoiceTranscript}
                  disabled={chatLoading}
                />
                <button
                  className="send-btn"
                  onClick={() => handleSendMessage()}
                  disabled={chatLoading || !chatInput.trim()}
                  aria-label="Send message"
                >
                  Send
                </button>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
