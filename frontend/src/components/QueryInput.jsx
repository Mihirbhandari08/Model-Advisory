import { useState } from 'react'

export default function QueryInput({ query, setQuery, onSubmit, loading, hasSession, onNewSession }) {
    const [isFocused, setIsFocused] = useState(false)

    const handleSubmit = (e) => {
        e.preventDefault()
        if (query.trim() && !loading) {
            onSubmit(query)
        }
    }

    return (
        <div className={`glass-card p-6 transition-all duration-300 ${isFocused ? 'glow-effect ring-2 ring-primary-500/30' : ''}`}>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="relative">
                    <textarea
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setIsFocused(false)}
                        placeholder={hasSession
                            ? "Follow up: 'make it smaller', 'cheaper option?', 'what about mobile?'"
                            : "Describe your AI model needs... e.g., 'I need a text embedding model for legal documents that runs on 8GB VRAM'"
                        }
                        className="w-full h-24 px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-xl
                     text-slate-100 placeholder-slate-400 resize-none
                     focus:outline-none focus:border-primary-500/50 input-glow
                     transition-all duration-200"
                        disabled={loading}
                    />

                    {/* Character counter */}
                    <span className="absolute bottom-2 right-3 text-xs text-slate-500">
                        {query.length}/500
                    </span>
                </div>

                <div className="flex items-center justify-between gap-4">
                    <div className="flex gap-2">
                        {hasSession && (
                            <button
                                type="button"
                                onClick={onNewSession}
                                className="btn-secondary flex items-center gap-2"
                                disabled={loading}
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M12 4v16m8-8H4" />
                                </svg>
                                New Search
                            </button>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={loading || !query.trim()}
                        className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? (
                            <>
                                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                Analyzing...
                            </>
                        ) : (
                            <>
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                                {hasSession ? 'Refine Search' : 'Find Model'}
                            </>
                        )}
                    </button>
                </div>
            </form>

            {/* Session indicator */}
            {hasSession && (
                <div className="mt-4 pt-4 border-t border-slate-700/50 flex items-center gap-2 text-sm text-slate-400">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span>Active session — follow-up queries will refine your search</span>
                </div>
            )}
        </div>
    )
}
