import { useState } from 'react'
import ResultCard from './ResultCard'
import CodeBlock from './CodeBlock'
import SystemDesignChat from './SystemDesignChat'

export default function ModelRecommendation({ result }) {
    const [expandedSections, setExpandedSections] = useState({
        code: false,
        alternatives: false
    })
    const [showExpertChat, setShowExpertChat] = useState(false)

    const toggleSection = (section) => {
        setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
    }

    const {
        best_match,
        reality_check,
        trade_offs,
        use_case_fit,
        pro_tips,
        next_steps,
        cost_breakdown,
        deployment_code,
        also_considered,
        constraints
    } = result

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Best Match */}
            <ResultCard
                icon="🏆"
                title="Best Match"
                gradient="from-amber-500/20 to-orange-500/20"
                glow="shadow-amber-500/10"
            >
                <div className="space-y-4">
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <h3 className="text-2xl font-bold text-slate-100">{best_match?.name || 'Unknown'}</h3>
                            <p className="text-slate-400">{best_match?.model_id}</p>
                        </div>
                        <div className="flex gap-2">
                            <span className="px-3 py-1 bg-primary-500/20 text-primary-300 rounded-full text-sm">
                                {best_match?.task || 'general'}
                            </span>
                            <span className="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-sm">
                                {best_match?.license || 'unknown'}
                            </span>
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-700/50">
                        <div className="text-center">
                            <p className="text-2xl font-bold text-slate-100">
                                {(best_match?.downloads || 0).toLocaleString()}
                            </p>
                            <p className="text-sm text-slate-400">Downloads</p>
                        </div>
                        <div className="text-center">
                            <p className="text-2xl font-bold text-slate-100">{best_match?.likes || 0}</p>
                            <p className="text-sm text-slate-400">Likes</p>
                        </div>
                        <div className="text-center">
                            <p className="text-2xl font-bold text-slate-100">
                                {best_match?.vram_required || 'Unknown'}
                            </p>
                            <p className="text-sm text-slate-400">VRAM</p>
                        </div>
                    </div>

                    {best_match?.model_card_url && (
                        <a
                            href={best_match.model_card_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 transition-colors"
                        >
                            View on Hugging Face →
                        </a>
                    )}
                </div>
            </ResultCard>

            {/* Reality Check */}
            <ResultCard icon="✅" title="The Reality Check">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <tbody className="divide-y divide-slate-700/50">
                            {Object.entries(reality_check || {}).map(([key, value]) => (
                                <tr key={key} className="hover:bg-slate-700/20">
                                    <td className="py-3 pr-4 text-slate-400 capitalize">
                                        {key.replace(/_/g, ' ')}
                                    </td>
                                    <td className="py-3 font-medium text-slate-100">{value}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </ResultCard>

            {/* Trade-offs */}
            <ResultCard icon="⚖️" title="Honest Trade-Offs">
                <div className="space-y-4">
                    {(trade_offs || []).map((tradeoff, i) => (
                        <div key={i} className="p-4 bg-slate-800/50 rounded-xl">
                            <h4 className="font-semibold text-slate-200 mb-3">{tradeoff.aspect}</h4>
                            <div className="grid md:grid-cols-2 gap-4">
                                <div>
                                    <p className="text-green-400 text-sm font-medium mb-2">✓ Pros</p>
                                    <ul className="space-y-1">
                                        {(tradeoff.pros || []).map((pro, j) => (
                                            <li key={j} className="text-sm text-slate-300 flex items-start gap-2">
                                                <span className="text-green-400 mt-1">•</span>
                                                {pro}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div>
                                    <p className="text-amber-400 text-sm font-medium mb-2">✗ Cons</p>
                                    <ul className="space-y-1">
                                        {(tradeoff.cons || []).map((con, j) => (
                                            <li key={j} className="text-sm text-slate-300 flex items-start gap-2">
                                                <span className="text-amber-400 mt-1">•</span>
                                                {con}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </ResultCard>

            {/* Use Case Fit */}
            <ResultCard icon="🎯" title="Use Case Fit">
                <p className="text-slate-300 leading-relaxed">{use_case_fit}</p>
            </ResultCard>

            {/* Pro Tips */}
            <ResultCard icon="💡" title="Pro Tips">
                <ul className="space-y-3">
                    {(pro_tips || []).map((tip, i) => (
                        <li key={i} className="flex items-start gap-3">
                            <span className="w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 
                           flex items-center justify-center text-sm font-medium flex-shrink-0">
                                {i + 1}
                            </span>
                            <span className="text-slate-300">{tip}</span>
                        </li>
                    ))}
                </ul>
            </ResultCard>

            {/* What to Do Next */}
            <ResultCard icon="🧭" title="What to Do Next">
                <ol className="space-y-3">
                    {(next_steps || []).map((step, i) => (
                        <li key={i} className="flex items-start gap-3">
                            <span className="w-6 h-6 rounded-full bg-primary-500/20 text-primary-400 
                           flex items-center justify-center text-sm font-medium flex-shrink-0">
                                {i + 1}
                            </span>
                            <span className="text-slate-300">{step}</span>
                        </li>
                    ))}
                </ol>
            </ResultCard>

            {/* Cost Breakdown */}
            <ResultCard
                icon="💸"
                title="Cost Breakdown"
                gradient="from-emerald-500/10 to-teal-500/10"
            >
                <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl">
                        <div>
                            <p className="text-sm text-slate-400">Deployment Type</p>
                            <p className="text-lg font-semibold text-slate-100 capitalize">
                                {cost_breakdown?.deployment_type || 'Unknown'}
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-slate-400">Monthly Cost</p>
                            <p className="text-2xl font-bold text-emerald-400">
                                ${cost_breakdown?.monthly_cost_low || 0} - ${cost_breakdown?.monthly_cost_high || 0}
                            </p>
                        </div>
                    </div>

                    {cost_breakdown?.notes?.length > 0 && (
                        <ul className="space-y-2">
                            {cost_breakdown.notes.map((note, i) => (
                                <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                                    <span className="text-emerald-400">•</span>
                                    {note}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </ResultCard>

            {/* Deployment Code */}
            <ResultCard
                icon="🐍"
                title="Python Deployment Snippet"
                collapsible
                collapsed={!expandedSections.code}
                onToggle={() => toggleSection('code')}
            >
                <CodeBlock code={deployment_code || '# No code generated'} />
            </ResultCard>

            {/* Also Considered */}
            {also_considered?.length > 0 && (
                <ResultCard
                    icon="🔄"
                    title="Also Considered"
                    collapsible
                    collapsed={!expandedSections.alternatives}
                    onToggle={() => toggleSection('alternatives')}
                >
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="border-b border-slate-700/50">
                                    <th className="pb-3 text-slate-400 font-medium">Model</th>
                                    <th className="pb-3 text-slate-400 font-medium">Task</th>
                                    <th className="pb-3 text-slate-400 font-medium">License</th>
                                    <th className="pb-3 text-slate-400 font-medium">Downloads</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-700/30">
                                {also_considered.map((model, i) => (
                                    <tr key={i} className="hover:bg-slate-700/20">
                                        <td className="py-3 pr-4">
                                            <a
                                                href={model.model_card_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-primary-400 hover:text-primary-300"
                                            >
                                                {model.name}
                                            </a>
                                        </td>
                                        <td className="py-3 pr-4 text-slate-300">{model.task}</td>
                                        <td className="py-3 pr-4 text-slate-300">{model.license}</td>
                                        <td className="py-3 text-slate-300">{model.downloads?.toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </ResultCard>
            )}

            {/* Ask Expert Button */}
            <div className="flex justify-center pt-4">
                <button
                    onClick={() => setShowExpertChat(!showExpertChat)}
                    className={`flex items-center gap-3 px-6 py-3 rounded-xl font-medium
                              transition-all duration-300 shadow-lg
                              ${showExpertChat
                            ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                            : 'bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-400 hover:to-blue-400 shadow-purple-500/25 hover:shadow-purple-500/40'}`}
                >
                    <span className="text-xl">{showExpertChat ? '✕' : '🔧'}</span>
                    <span>{showExpertChat ? 'Close Expert Chat' : 'Ask Implementation Expert'}</span>
                </button>
            </div>

            {/* System Design Expert Chat */}
            {showExpertChat && (
                <SystemDesignChat
                    sessionId={result.session_id}
                    modelContext={best_match}
                    onClose={() => setShowExpertChat(false)}
                />
            )}
        </div>
    )
}
