import { useState } from 'react';

const API_BASE = 'http://65.0.103.28:8000';

function ScoreGauge({ label, score, icon }) {
    const pct = Math.round(score * 100);
    const color = pct >= 80 ? 'text-emerald-400' : pct >= 50 ? 'text-amber-400' : 'text-red-400';
    const bg = pct >= 80 ? 'from-emerald-500/20 to-emerald-500/5' : pct >= 50 ? 'from-amber-500/20 to-amber-500/5' : 'from-red-500/20 to-red-500/5';
    const ring = pct >= 80 ? 'ring-emerald-500/30' : pct >= 50 ? 'ring-amber-500/30' : 'ring-red-500/30';
    const circumference = 2 * Math.PI * 54;
    const dashoffset = circumference - (pct / 100) * circumference;

    return (
        <div className={`flex flex-col items-center p-6 rounded-2xl bg-gradient-to-b ${bg} ring-1 ${ring} backdrop-blur-sm`}>
            <div className="relative w-32 h-32 mb-3">
                <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="54" fill="none" stroke="currentColor" strokeWidth="8" className="text-slate-800" />
                    <circle cx="60" cy="60" r="54" fill="none" strokeWidth="8" strokeLinecap="round"
                        className={color}
                        style={{
                            strokeDasharray: circumference,
                            strokeDashoffset: dashoffset,
                            transition: 'stroke-dashoffset 1s ease-in-out',
                            stroke: 'currentColor'
                        }}
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={`text-3xl font-bold ${color}`}>{pct}%</span>
                </div>
            </div>
            <span className="text-lg font-medium text-slate-200">{icon} {label}</span>
        </div>
    );
}

function SampleRow({ sample, index }) {
    const [expanded, setExpanded] = useState(false);

    const avgScore = (
        (sample.scores.faithfulness + sample.scores.answer_relevancy + sample.scores.context_precision) / 3
    );
    const pct = Math.round(avgScore * 100);
    const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';

    return (
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 backdrop-blur-sm overflow-hidden transition-all hover:border-slate-600/50">
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full p-4 text-left flex items-center gap-4 hover:bg-slate-700/20 transition-colors"
            >
                <span className="text-xs font-mono text-slate-500 w-6">#{index + 1}</span>
                <span className="flex-1 text-sm text-slate-300 truncate">{sample.question}</span>
                <div className="flex items-center gap-3 shrink-0">
                    <div className="w-24 h-2 rounded-full bg-slate-700 overflow-hidden">
                        <div className={`h-full rounded-full ${barColor} transition-all duration-500`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-mono text-slate-400 w-10 text-right">{pct}%</span>
                    <svg className={`w-4 h-4 text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </button>

            {expanded && (
                <div className="px-4 pb-4 pt-2 border-t border-slate-700/50 space-y-4 animate-fade-in">
                    {/* Individual Scores */}
                    <div className="grid grid-cols-3 gap-3">
                        {Object.entries(sample.scores).map(([key, value]) => {
                            const sp = Math.round(value * 100);
                            const sc = sp >= 80 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : sp >= 50 ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20';
                            return (
                                <div key={key} className={`rounded-lg p-2 text-center border ${sc}`}>
                                    <div className="text-xs text-slate-400 mb-1">{key.replace('_', ' ')}</div>
                                    <div className="text-lg font-bold">{sp}%</div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Answer */}
                    <div>
                        <div className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Answer</div>
                        <p className="text-sm text-slate-300 bg-slate-900/50 rounded-lg p-3 border border-slate-700/30">{sample.answer}</p>
                    </div>

                    {/* Contexts */}
                    <div>
                        <div className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Contexts</div>
                        <ul className="space-y-1.5">
                            {sample.contexts.map((ctx, i) => (
                                <li key={i} className="text-xs text-slate-400 bg-slate-900/50 rounded-lg p-2 border border-slate-700/30">
                                    {ctx}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}
        </div>
    );
}

function EvalDashboard({ onClose }) {
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const runEval = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/api/evals/run`, { method: 'POST' });
            if (!res.ok) throw new Error(`API error: ${res.status}`);
            const data = await res.json();
            setResults(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const loadCached = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/evals/results`);
            if (res.ok) {
                const data = await res.json();
                if (data.status !== 'no_results') setResults(data);
            }
        } catch { /* ignore */ }
    };

    // Load cached results on mount
    useState(() => { loadCached(); });

    return (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex flex-col overflow-hidden text-slate-200 animate-fade-in">
            {/* Header */}
            <header className="h-16 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between px-6 shrink-0 backdrop-blur-md">
                <div className="flex items-center gap-4">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent flex items-center gap-2">
                        <span>📈</span> RAGAS Evaluation
                    </h2>
                    {results && (
                        <span className="text-xs text-slate-500 font-mono">
                            {results.dataset_size} samples • {(results.duration_ms / 1000).toFixed(1)}s
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={runEval}
                        disabled={loading}
                        className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-all
                            ${loading
                                ? 'bg-slate-800 border-slate-700 text-slate-500 cursor-wait'
                                : 'bg-gradient-to-r from-primary-500 to-accent-500 border-transparent text-white hover:shadow-lg hover:shadow-primary-500/20'
                            }`}
                    >
                        {loading ? '⏳ Running Evaluation...' : '▶ Run Evaluation'}
                    </button>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white"
                    >
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            </header>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800">
                {error && (
                    <div className="mb-6 p-4 rounded-xl border border-red-500/30 bg-red-500/5 text-red-400 text-sm">
                        ❌ {error}
                    </div>
                )}

                {!results && !loading && (
                    <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4">
                        <span className="text-6xl opacity-30">📈</span>
                        <p className="text-lg">No evaluation results yet</p>
                        <p className="text-sm">Click <strong>"Run Evaluation"</strong> to evaluate the recommendation pipeline</p>
                    </div>
                )}

                {loading && (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
                        <div className="w-16 h-16 border-4 border-slate-700 border-t-primary-500 rounded-full animate-spin" />
                        <p className="text-lg">Evaluating with Gemini judge...</p>
                        <p className="text-sm text-slate-500">Scoring 5 samples across 3 RAGAS metrics (15 LLM calls)</p>
                    </div>
                )}

                {results && !loading && (
                    <div className="max-w-5xl mx-auto space-y-8">
                        {/* Aggregate Scores */}
                        <div className="grid grid-cols-3 gap-6">
                            <ScoreGauge label="Faithfulness" score={results.aggregate_scores.faithfulness} icon="🎯" />
                            <ScoreGauge label="Relevancy" score={results.aggregate_scores.answer_relevancy} icon="💬" />
                            <ScoreGauge label="Precision" score={results.aggregate_scores.context_precision} icon="🔍" />
                        </div>

                        {/* JSON Export */}
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-semibold text-slate-200">Per-Sample Breakdown</h3>
                            <button
                                onClick={() => {
                                    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = `ragas-eval-${new Date().toISOString().slice(0, 10)}.json`;
                                    a.click();
                                }}
                                className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-600 bg-slate-800/50 hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-all"
                            >
                                📥 Download JSON
                            </button>
                        </div>

                        {/* Sample Rows */}
                        <div className="space-y-3">
                            {results.samples.map((sample, i) => (
                                <SampleRow key={i} sample={sample} index={i} />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default EvalDashboard;
