import { useState, useCallback } from 'react'
import './index.css'
import QueryInput from './components/QueryInput'
import ModelRecommendation from './components/ModelRecommendation'
import LoadingState from './components/LoadingState'
import MetricsDashboard from './components/MetricsDashboard'
import EvalDashboard from './components/EvalDashboard'
import { loggedFetch, logger } from './utils/logger'

const API_BASE = 'http://65.0.103.28:5000'

function App() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [showDashboard, setShowDashboard] = useState(false)
  const [showEvalDashboard, setShowEvalDashboard] = useState(false)

  const handleSubmit = useCallback(async (inputQuery) => {
    if (!inputQuery.trim()) return

    setLoading(true)
    setError(null)
    logger.logInteraction('submit_query', { query_length: inputQuery.length, has_session: !!sessionId })

    try {
      const endpoint = sessionId ? '/api/advisor/followup' : '/api/advisor'
      const body = sessionId
        ? { query: inputQuery, session_id: sessionId }
        : { query: inputQuery }

      const response = await loggedFetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
      setSessionId(data.session_id)
      logger.info('APP', 'Recommendation received', { session_id: data.session_id })

    } catch (err) {
      console.error('Error fetching recommendation:', err)
      logger.error('APP', 'Recommendation failed', { error: err.message })
      setError(err.message || 'Failed to get recommendation. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  const handleNewSession = () => {
    setSessionId(null)
    setResult(null)
    setQuery('')
    setError(null)
  }

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <header className="max-w-5xl mx-auto mb-12 text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-500/30">
            <span className="text-2xl">🧠</span>
          </div>
          <h1 className="text-4xl font-bold gradient-text">ModelAdvisor</h1>
        </div>
        <p className="text-slate-400 text-lg max-w-2xl mx-auto">
          AI-powered model recommendations. Describe your use case in natural language
          and get the perfect model with trade-offs, costs, and deployment code.
        </p>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto space-y-8">
        {/* Query Input */}
        <QueryInput
          query={query}
          setQuery={setQuery}
          onSubmit={handleSubmit}
          loading={loading}
          hasSession={!!sessionId}
          onNewSession={handleNewSession}
        />

        {/* Error State */}
        {error && (
          <div className="glass-card p-6 border-red-500/30 animate-fade-in">
            <div className="flex items-center gap-3 text-red-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium">{error}</span>
            </div>
            <p className="text-slate-400 mt-2 text-sm">
              Make sure the backend server is running: <code className="text-primary-400">uvicorn main:app --reload</code>
            </p>
          </div>
        )}

        {/* Loading State */}
        {loading && <LoadingState />}

        {/* Results */}
        {result && !loading && (
          <ModelRecommendation result={result} />
        )}

        {/* Example Queries */}
        {!result && !loading && (
          <div className="glass-card p-6 animate-fade-in">
            <h3 className="text-lg font-semibold text-slate-200 mb-4">💡 Try these example queries:</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                "I need a model around multilingual chatbot",
                "Looking for something that runs on 4GB RAM",
                "Need to embed 10M legal docs — what's cheapest?",
                "Building a memory for my AI agent"
              ].map((example, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setQuery(example)
                    handleSubmit(example)
                  }}
                  className="text-left p-3 rounded-lg bg-slate-700/30 hover:bg-slate-600/40 
                           border border-slate-600/30 hover:border-slate-500/50
                           text-slate-300 hover:text-slate-100 transition-all duration-200"
                >
                  "{example}"
                </button>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="max-w-5xl mx-auto mt-16 text-center text-slate-500 text-sm pb-8">
        <p className="mb-4">Powered by Gemini 2.5 Flash &amp; Hugging Face</p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setShowDashboard(true)}
            className="text-xs px-3 py-1 bg-slate-800/50 hover:bg-slate-700/50 rounded-full border border-slate-700 hover:border-slate-600 transition-colors"
          >
            View System Diagnostics
          </button>
          <button
            onClick={() => setShowEvalDashboard(true)}
            className="text-xs px-3 py-1 bg-gradient-to-r from-primary-500/10 to-accent-500/10 hover:from-primary-500/20 hover:to-accent-500/20 rounded-full border border-primary-500/30 hover:border-primary-500/50 text-primary-400 hover:text-primary-300 transition-all"
          >
            📈 Run Evals
          </button>
        </div>
      </footer>

      {showDashboard && (
        <MetricsDashboard onClose={() => setShowDashboard(false)} />
      )}

      {showEvalDashboard && (
        <EvalDashboard onClose={() => setShowEvalDashboard(false)} />
      )}
    </div>
  )
}

export default App
