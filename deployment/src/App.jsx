import { useState, useRef, useEffect, useCallback } from 'react'

const DEFAULT_API_URL =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://charusat-chatbot-api.onrender.com'

const API_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, '')

const APP_TITLE = 'CHARUSAT Online Course Assistant'

const SUGGESTIONS = [
  'What programmes are offered?',
  'What is the eligibility for Online BCA?',
  'What is the total fee of MBA?',
  'How long is the BBA programme?',
  'How do I apply for admission?',
  'What is the refund policy?',
]

const sanitizeUserAnswer = (text) => {
  if (!text || typeof text !== 'string') return ''

  const trimmed = text.trim()
  const isFallback = /available university knowledge base|available knowledge-base source files/i.test(trimmed)

  if (isFallback) {
    return trimmed
  }

  let cleaned = trimmed
  cleaned = cleaned.replace(/(?:^|\n)\s*(?:Source|Page|Chunk ID|Score|Programme|Content Type|Document Type)\s*:\s*.*$/gim, '')
  cleaned = cleaned.replace(/\b(?:programs|pdfs|knowledge_base)[/\\][^\n\r,;:()]+\.(?:md|pdf|txt|docx)\b/gi, '')
  cleaned = cleaned.replace(/\b(?:PPR_Online\s+(?:BBA|BCA|MBA|MCA)|Fees\s+Refund\s+Policy|ciqa|feedback|home|mandatory-disclosures|privacy-policy|terms-conditions|contact|online_bba|online_bca|online_mba|online_mca)(?:\.(?:pdf|md|txt))?\b/gi, '')
  cleaned = cleaned.replace(/\b(?:via|generated\s+by)\s+(?:groq|gemini)\b/gi, '')
  cleaned = cleaned.replace(/\bresolved\s*:\s*.*$/gim, '')
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim()
  return cleaned
}

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState('checking')
  const [theme, setTheme] = useState(() => localStorage.getItem('charusat-theme') || 'light')
  const [error, setError] = useState(null)
  const chatEndRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    document.body.dataset.theme = theme
    localStorage.setItem('charusat-theme', theme)
  }, [theme])

  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 8000)
        const res = await fetch(`${API_URL}/health`, { signal: controller.signal })
        clearTimeout(timeout)
        if (!res.ok) throw new Error(`health_status_${res.status}`)
        const data = await res.json()
        if (!cancelled) setHealth(data && data.status === 'ok' ? 'ok' : 'error')
      } catch {
        if (!cancelled) setHealth('error')
      }
    }

    check()
    const interval = setInterval(check, 30000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleInputChange = (e) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  const sendMessage = useCallback(async (text) => {
    const question = (text || input).trim()
    if (!question || loading) return

    setInput('')
    setError(null)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    setMessages((prev) => [...prev, { role: 'user', text: question }])
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          question,
        }),
      })

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      setSessionId(data.session_id)

      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: sanitizeUserAnswer(data.answer),
        },
      ])
    } catch (err) {
      setError(err.message || 'Failed to connect to the backend API.')
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }, [input, loading, sessionId])

  const handleNewChat = async () => {
    if (sessionId) {
      try {
        await fetch(`${API_URL}/chat/history/${sessionId}`, { method: 'DELETE' })
      } catch {
        // Ignore and reset locally.
      }
    }
    setMessages([])
    setSessionId(null)
    setError(null)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className={`app-shell ${theme}`}>
      <div className="app-container">
        <header className="app-header">
          <div className="header-left">
            <div className="header-logo" aria-hidden="true">C</div>
            <div>
              <div className="header-title">{APP_TITLE}</div>
              <div className="header-subtitle">Online programme enquiries and support</div>
            </div>
          </div>

          <div className="header-actions">
            <button
              type="button"
              className="theme-toggle"
              aria-label="Toggle colour theme"
              onClick={() => setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))}
            >
              <span>{theme === 'light' ? 'Dark' : 'Light'}</span>
            </button>

            <div className="health-badge" aria-live="polite">
              <span className={`health-dot ${health}`} />
              {health === 'ok' ? 'Online' : health === 'error' ? 'Offline' : 'Checking…'}
            </div>

            {!isEmpty && (
              <button className="btn-new-chat" onClick={handleNewChat} id="btn-new-chat">
                New Chat
              </button>
            )}
          </div>
        </header>

        <div className="chat-area" id="chat-area">
          {isEmpty && !loading ? (
            <div className="welcome">
              <div className="welcome-icon" aria-hidden="true">C</div>
              <h2>Welcome to the {APP_TITLE}</h2>
              <p>
                Ask about CHARUSAT's online programmes — fees, eligibility, duration,
                curriculum, admissions and more. Answers are based on the materials
                available in the university knowledge base.
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="suggestion-chip"
                    onClick={() => sendMessage(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="msg-avatar">{msg.role === 'user' ? 'U' : 'A'}</div>
                <div className="msg-content">
                  <div className="msg-bubble">{msg.text}</div>
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="message bot">
              <div className="msg-avatar">A</div>
              <div className="msg-content">
                <div className="msg-bubble">
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && <div className="error-banner">{error}</div>}

          <div ref={chatEndRef} />
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              id="chat-input"
              rows={1}
              placeholder="Ask about programmes, fees, eligibility…"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              className="btn-send"
              id="btn-send"
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              title="Send message"
              aria-label="Send"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
