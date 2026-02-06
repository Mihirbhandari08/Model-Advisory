import { useState } from 'react'

export default function CodeBlock({ code, language = 'python' }) {
    const [copied, setCopied] = useState(false)

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch (err) {
            console.error('Failed to copy:', err)
        }
    }

    return (
        <div className="relative group">
            {/* Copy button */}
            <button
                onClick={handleCopy}
                className="absolute top-3 right-3 p-2 bg-slate-700/50 hover:bg-slate-600/50 
                 rounded-lg text-slate-400 hover:text-slate-200 transition-all
                 opacity-0 group-hover:opacity-100"
                title="Copy to clipboard"
            >
                {copied ? (
                    <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                )}
            </button>

            {/* Language badge */}
            <span className="absolute top-3 left-3 px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-400 font-mono">
                {language}
            </span>

            {/* Code content */}
            <div className="code-block pt-10">
                <pre className="whitespace-pre-wrap break-words">
                    <code>{code}</code>
                </pre>
            </div>

            {/* Copied feedback */}
            {copied && (
                <div className="absolute top-3 right-14 px-2 py-1 bg-green-500/20 text-green-400 
                      text-xs rounded animate-fade-in">
                    Copied!
                </div>
            )}
        </div>
    )
}
