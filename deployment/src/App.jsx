import { useState, useRef, useEffect, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SUGGESTIONS = [
  'What programmes are available?',
  'Tell me about Online BCA fees',
  'What is the eligibility for MBA?',
  'How long is the BBA programme?',
]

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState('checking') // 'checking' | 'ok' | 'error'
  const [healthDocs, setHealthDocs] = useState(null)
  const [error, setError] = useState(null)
  const chatEndRef = useRef(null)
  const textareaRef = useRef(null)

  // --- Health check ---
  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(8000) })
        if (!res.ok) throw new Error('unhealthy')
        const data = await res.json()
        if (!cancelled) {
          setHealth('ok')
          setHealthDocs(data.vector_store_documents)
        }
      } catch {
        if (!cancelled) setHealth('error')
      }
    }
    check()
    return () => { cancelled = true }
  }, [])

  // --- Auto-scroll ---
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // --- Auto-resize textarea ---
  const handleInputChange = (e) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  // --- Send message ---
  const sendMessage = useCallback(async (text) => {
    const question = (text || input).trim()
    if (!question || loading) return

    setInput('')
    setError(null)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // Add user message
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
          text: data.answer,
          sources: data.sources,
          resolvedQuery: data.resolved_query,
          llmStatus: data.llm_status,
        },
      ])
    } catch (err) {
      setError(err.message || 'Failed to connect to the backend API.')
      // Remove the user message if the request completely failed
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }, [input, loading, sessionId])

  // --- New chat ---
  const handleNewChat = async () => {
    if (sessionId) {
      try {
        await fetch(`${API_URL}/chat/history/${sessionId}`, { method: 'DELETE' })
      } catch {
        // Ignore — just reset locally
      }
    }
    setMessages([])
    setSessionId(null)
    setError(null)
  }

  // --- Key handler ---
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="header-logo">🎓</div>
          <div>
            <div className="header-title">CHARUSAT Course Assistant</div>
            <div className="header-subtitle">AI-powered programme enquiries</div>
          </div>
        </div>
        <div className="header-actions">
          <div className="health-badge" title={healthDocs != null ? `${healthDocs} docs indexed` : ''}>
            <span className={`health-dot ${health}`} />
            {health === 'ok' ? `${healthDocs} docs` : health === 'error' ? 'Offline' : 'Checking…'}
          </div>
          {!isEmpty && (
            <button className="btn-new-chat" onClick={handleNewChat} id="btn-new-chat">
              ✦ New Chat
            </button>
          )}
        </div>
      </header>

      {/* Chat Area */}
      <div className="chat-area" id="chat-area">
        {isEmpty && !loading ? (
          <div className="welcome">
            <div className="welcome-icon">🎓</div>
            <h2>Welcome to CHARUSAT Assistant</h2>
            <p>
              Ask me anything about CHARUSAT's online programmes — fees, eligibility,
              duration, curriculum, and more.
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
              <div className="msg-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="msg-content">
                <div className="msg-bubble">{msg.text}</div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="msg-sources">
                    {msg.sources.map((src, j) => (
                      <span key={j} className="source-tag">📄 {src}</span>
                    ))}
                  </div>
                )}
                {msg.llmStatus && (
                  <div className="msg-meta">
                    via {msg.llmStatus}
                    {msg.resolvedQuery && msg.resolvedQuery !== msg.text && (
                      <> · resolved: "{msg.resolvedQuery}"</>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="message bot">
            <div className="msg-avatar">🤖</div>
            <div className="msg-content">
              <div className="msg-bubble">
                <div className="typing-indicator">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          </div>
        )}

        {error && <div className="error-banner">⚠ {error}</div>}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
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
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
