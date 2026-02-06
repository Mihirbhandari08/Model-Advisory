import { useState, useEffect, useRef } from 'react'
import CodeBlock from './CodeBlock'

const API_BASE = 'http://localhost:8000'

/**
 * SystemDesignChat - Chat interface for the ML System Design Expert
 * 
 * Provides a conversational interface for asking implementation,
 * deployment, and infrastructure questions about the recommended model.
 */
function SystemDesignChat({ sessionId, modelContext, onClose }) {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [suggestions, setSuggestions] = useState([])
    const messagesEndRef = useRef(null)

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Fetch suggested questions on mount
    useEffect(() => {
        fetchSuggestions()
    }, [sessionId])

    const fetchSuggestions = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/advisor/system-design/suggestions?session_id=${sessionId}`)
            if (response.ok) {
                const data = await response.json()
                setSuggestions(data.suggestions || [])
            }
        } catch (error) {
            console.error('Failed to fetch suggestions:', error)
        }
    }

    const handleSubmit = async (question) => {
        if (!question?.trim()) return

        const userMessage = { role: 'user', content: question }
        setMessages(prev => [...prev, userMessage])
        setInput('')
        setLoading(true)

        try {
            const response = await fetch(`${API_BASE}/api/advisor/system-design`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    session_id: sessionId
                })
            })

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`)
            }

            const data = await response.json()

            const assistantMessage = {
                role: 'assistant',
                content: data.answer,
                code_samples: data.code_samples || [],
                tradeoffs: data.tradeoffs || [],
                alternatives: data.alternatives || [],
                resources: data.resources || [],
                context_summary: data.context_summary
            }

            setMessages(prev => [...prev, assistantMessage])

            // Update suggestions with follow-ups
            if (data.suggested_followups?.length > 0) {
                setSuggestions(data.suggested_followups)
            }

        } catch (error) {
            console.error('Error asking expert:', error)
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
                isError: true
            }])
        } finally {
            setLoading(false)
        }
    }

    const handleSuggestionClick = (suggestion) => {
        handleSubmit(suggestion)
    }

    return (
        <div className="glass-card overflow-hidden animate-fade-in">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 p-4 border-b border-slate-700/50">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg">
                            <span className="text-lg">🔧</span>
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-white">ML System Design Expert</h3>
                            <p className="text-xs text-slate-400">
                                Advising on: <span className="text-purple-300">{modelContext?.name || modelContext?.model_id || 'Selected Model'}</span>
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-white transition-colors"
                        title="Close"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Messages Area */}
            <div className="h-[400px] overflow-y-auto p-4 space-y-4 bg-slate-900/30">
                {messages.length === 0 ? (
                    <div className="text-center py-8 space-y-4">
                        <div className="text-slate-400">
                            <p className="text-sm">Ask me about deployment, infrastructure, quantization, vector DBs, fine-tuning, and more!</p>
                        </div>

                        {/* Suggested Questions */}
                        {suggestions.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-xs text-slate-500 uppercase tracking-wider">Suggested Questions</p>
                                <div className="flex flex-wrap gap-2 justify-center">
                                    {suggestions.map((suggestion, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => handleSuggestionClick(suggestion)}
                                            className="px-3 py-2 text-sm bg-slate-800/50 hover:bg-slate-700/50 
                               border border-slate-600/50 hover:border-purple-500/50
                               rounded-lg text-slate-300 hover:text-white transition-all duration-200"
                                        >
                                            {suggestion}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    messages.map((message, idx) => (
                        <MessageBubble key={idx} message={message} />
                    ))
                )}

                {loading && (
                    <div className="flex items-center gap-2 text-slate-400">
                        <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                            <span className="animate-pulse">🔧</span>
                        </div>
                        <div className="flex gap-1">
                            <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                            <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                            <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Follow-up Suggestions (after conversation starts) */}
            {messages.length > 0 && suggestions.length > 0 && !loading && (
                <div className="px-4 py-2 bg-slate-800/30 border-t border-slate-700/50">
                    <div className="flex gap-2 overflow-x-auto pb-1">
                        {suggestions.slice(0, 3).map((suggestion, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="flex-shrink-0 px-3 py-1 text-xs bg-slate-700/50 hover:bg-slate-600/50 
                         border border-slate-600/50 hover:border-purple-500/50
                         rounded-full text-slate-300 hover:text-white transition-all"
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input Area */}
            <div className="p-4 bg-slate-800/50 border-t border-slate-700/50">
                <form onSubmit={(e) => { e.preventDefault(); handleSubmit(input); }} className="flex gap-3">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about deployment, quantization, vector DBs..."
                        className="flex-1 px-4 py-3 bg-slate-900/50 border border-slate-600/50 rounded-xl
                     text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50
                     focus:ring-2 focus:ring-purple-500/20 transition-all"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 
                     hover:from-purple-400 hover:to-blue-400
                     disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed
                     text-white font-medium rounded-xl shadow-lg shadow-purple-500/25
                     hover:shadow-purple-500/40 transition-all duration-200"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </form>
            </div>
        </div>
    )
}

/**
 * MessageBubble - Individual message in the chat
 */
function MessageBubble({ message }) {
    const isUser = message.role === 'user'

    return (
        <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center
                      ${isUser
                    ? 'bg-blue-500/20'
                    : message.isError
                        ? 'bg-red-500/20'
                        : 'bg-purple-500/20'}`}>
                <span className="text-sm">{isUser ? '👤' : message.isError ? '⚠️' : '🔧'}</span>
            </div>

            {/* Message Content */}
            <div className={`flex-1 max-w-[85%] space-y-3 ${isUser ? 'text-right' : ''}`}>
                {/* Main Text */}
                <div className={`inline-block px-4 py-3 rounded-xl ${isUser
                        ? 'bg-blue-500/20 text-blue-100'
                        : message.isError
                            ? 'bg-red-500/10 border border-red-500/30 text-red-300'
                            : 'bg-slate-800/50 text-slate-200'
                    }`}>
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                </div>

                {/* Context Summary */}
                {message.context_summary && (
                    <p className="text-xs text-slate-500 italic">{message.context_summary}</p>
                )}

                {/* Code Samples */}
                {message.code_samples?.length > 0 && (
                    <div className="space-y-3">
                        {message.code_samples.map((sample, idx) => (
                            <div key={idx} className="text-left">
                                {sample.description && (
                                    <p className="text-xs text-slate-400 mb-1">{sample.description}</p>
                                )}
                                <CodeBlock
                                    code={sample.code}
                                    language={sample.language}
                                    filename={sample.filename}
                                />
                            </div>
                        ))}
                    </div>
                )}

                {/* Trade-offs */}
                {message.tradeoffs?.length > 0 && (
                    <div className="text-left space-y-2">
                        <p className="text-xs text-slate-500 uppercase tracking-wider">Trade-offs</p>
                        {message.tradeoffs.map((tradeoff, idx) => (
                            <div key={idx} className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
                                <p className="text-sm font-medium text-slate-200 mb-2">{tradeoff.approach}</p>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div>
                                        <p className="text-green-400 font-medium mb-1">✓ Pros</p>
                                        <ul className="text-slate-400 space-y-0.5">
                                            {tradeoff.pros?.map((pro, i) => (
                                                <li key={i}>• {pro}</li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div>
                                        <p className="text-red-400 font-medium mb-1">✗ Cons</p>
                                        <ul className="text-slate-400 space-y-0.5">
                                            {tradeoff.cons?.map((con, i) => (
                                                <li key={i}>• {con}</li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Alternatives */}
                {message.alternatives?.length > 0 && (
                    <div className="text-left">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Alternatives</p>
                        <ul className="text-xs text-slate-400 space-y-0.5">
                            {message.alternatives.map((alt, idx) => (
                                <li key={idx}>→ {alt}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Resources */}
                {message.resources?.length > 0 && (
                    <div className="text-left">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Resources</p>
                        <div className="flex flex-wrap gap-2">
                            {message.resources.map((resource, idx) => (
                                <a
                                    key={idx}
                                    href={resource.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 px-2 py-1 text-xs
                           bg-slate-700/50 hover:bg-slate-600/50 rounded-md
                           text-blue-300 hover:text-blue-200 transition-colors"
                                >
                                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                    {resource.title}
                                </a>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default SystemDesignChat
