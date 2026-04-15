import { useState, useEffect, useMemo } from 'react';
import { apiMetrics, logger } from '../utils/logger';

function MetricsDashboard({ onClose }) {
    const [metrics, setMetrics] = useState({
        api: apiMetrics.getStats(),
        logs: []
    });
    const [isPaused, setIsPaused] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            if (isPaused) return;

            // Fetch backend logs
            let backendLogs = [];
            try {
                const res = await fetch('http://65.0.103.28:5000/api/logs?count=100');
                if (res.ok) {
                    const data = await res.json();
                    backendLogs = data.logs.map(log => ({
                        ...log,
                        source: 'BACKEND',
                        timestamp: new Date(log.timestamp)
                    }));
                }
            } catch (err) {
                console.error('Failed to fetch backend logs', err);
            }

            // Get frontend logs
            const frontendLogs = logger.getRecentLogs(50).map(log => ({
                ...log,
                source: 'FRONTEND',
                timestamp: new Date(log.timestamp)
            }));

            // Merge and sort
            const allLogs = [...backendLogs, ...frontendLogs].sort(
                (a, b) => b.timestamp - a.timestamp
            ).slice(0, 200);

            setMetrics({
                api: apiMetrics.getStats(),
                logs: allLogs
            });
        };

        fetchData();
        const interval = setInterval(fetchData, 20000);
        return () => clearInterval(interval);
    }, [isPaused]);

    // Group logs into Kanban columns
    const columns = useMemo(() => {
        const cols = {
            requests: [],
            llm: [],
            agents: [],
            tools: [],
            errors: []
        };

        metrics.logs.forEach(log => {
            // Check for errors first
            if (log.level === 'ERROR' || log.status_code >= 500) {
                cols.errors.push(log);
                return;
            }

            // Categorize based on log content
            if (log.category === 'request' || log.category === 'API') {
                cols.requests.push(log);
            } else if (log.category === 'llm') {
                cols.llm.push(log);
            } else if (log.category === 'agent') {
                cols.agents.push(log);
            } else if (log.category === 'tool') {
                cols.tools.push(log);
            }
        });

        return cols;
    }, [metrics.logs]);

    return (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex flex-col overflow-hidden text-slate-200 animate-fade-in">
            {/* Header */}
            <header className="h-16 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between px-6 shrink-0 backdrop-blur-md">
                <div className="flex items-center gap-4">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent flex items-center gap-2">
                        <span>📊</span> System Diagnostics
                    </h2>
                    <div className="h-6 w-px bg-slate-700" />
                    <div className="flex gap-4 text-sm font-mono text-slate-400">
                        <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50">
                            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                            <span>{metrics.api.totalRequests} REQ</span>
                        </div>
                        <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50">
                            <span className={`w-2 h-2 rounded-full ${metrics.api.totalErrors > 0 ? 'bg-red-500 animate-bounce' : 'bg-slate-600'}`} />
                            <span className={metrics.api.totalErrors > 0 ? 'text-red-400' : ''}>{metrics.api.totalErrors} ERR</span>
                        </div>
                        <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50">
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                            <span>{metrics.api.avgResponseTime}ms AVG</span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setIsPaused(!isPaused)}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all ${isPaused
                            ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/20'
                            : 'bg-slate-800 border-slate-700 hover:bg-slate-700 text-slate-300'
                            }`}
                    >
                        {isPaused ? '⏸ PAUSED' : '⚡ LIVE'}
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

            {/* Kanban Board */}
            <div className="flex-1 overflow-x-auto overflow-y-hidden p-6 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800">
                <div className="flex gap-6 h-full min-w-max pb-4">
                    <KanbanColumn
                        title="HTTP Requests"
                        icon="🌐"
                        logs={columns.requests}
                        color="blue"
                    />
                    <KanbanColumn
                        title="LLM Operations"
                        icon="🧠"
                        logs={columns.llm}
                        color="purple"
                    />
                    <KanbanColumn
                        title="Agent Activity"
                        icon="🤖"
                        logs={columns.agents}
                        color="emerald"
                    />
                    <KanbanColumn
                        title="Tool Execution"
                        icon="🛠️"
                        logs={columns.tools}
                        color="amber"
                    />
                    <KanbanColumn
                        title="Errors & Alerts"
                        icon="⚠️"
                        logs={columns.errors}
                        color="red"
                        isAlert
                    />
                </div>
            </div>
        </div>
    );
}

function KanbanColumn({ title, icon, logs, color }) {
    const colorStyles = {
        blue: 'border-blue-500/20 bg-blue-500/5 shadow-[0_0_15px_-3px_rgba(59,130,246,0.1)]',
        purple: 'border-purple-500/20 bg-purple-500/5 shadow-[0_0_15px_-3px_rgba(168,85,247,0.1)]',
        emerald: 'border-emerald-500/20 bg-emerald-500/5 shadow-[0_0_15px_-3px_rgba(16,185,129,0.1)]',
        amber: 'border-amber-500/20 bg-amber-500/5 shadow-[0_0_15px_-3px_rgba(245,158,11,0.1)]',
        red: 'border-red-500/20 bg-red-500/5 shadow-[0_0_15px_-3px_rgba(239,68,68,0.1)]',
    };

    const headerColors = {
        blue: 'text-blue-400 border-blue-500/20 bg-blue-500/10',
        purple: 'text-purple-400 border-purple-500/20 bg-purple-500/10',
        emerald: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10',
        amber: 'text-amber-400 border-amber-500/20 bg-amber-500/10',
        red: 'text-red-400 border-red-500/20 bg-red-500/10',
    };

    return (
        <div className={`w-80 flex flex-col rounded-xl border ${colorStyles[color]} h-full backdrop-blur-sm transition-all duration-300 hover:shadow-lg hover:border-slate-600/50`}>
            {/* Column Header */}
            <div className={`p-4 border-b rounded-t-xl flex items-center justify-between ${headerColors[color]}`}>
                <div className="flex items-center gap-2 font-bold tracking-wide">
                    <span className="text-xl filter drop-shadow-md">{icon}</span>
                    <span className="drop-shadow-sm">{title}</span>
                </div>
                <span className="text-xs px-2 py-1 rounded bg-black/30 font-mono border border-white/10">
                    {logs.length}
                </span>
            </div>

            {/* Cards Container */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar relative">
                {logs.map((log, i) => (
                    <LogCard key={i} log={log} color={color} />
                ))}

                {logs.length === 0 && (
                    <div className="absolute inset-0 flex items-center justify-center text-slate-600 font-mono text-sm opacity-50 flex-col gap-2">
                        <span className="text-2xl opacity-20">{icon}</span>
                        <span>No Logs</span>
                    </div>
                )}
            </div>
        </div>
    );
}

function LogCard({ log, color }) {
    const [expanded, setExpanded] = useState(false);

    // Dynamic border for active status or errors
    const borderColor = log.success === false ? 'border-red-500/50' : 'border-slate-700/50';
    const bgColor = log.success === false ? 'bg-gradient-to-br from-red-900/10 to-red-900/5' : 'bg-slate-800/60';
    const hoverBorder = log.success === false ? 'group-hover:border-red-500/80' : 'group-hover:border-slate-500/50';

    return (
        <div
            className={`rounded-lg border ${borderColor} ${bgColor} p-3 transition-all duration-200 
                shadow-sm hover:shadow-md cursor-pointer group backdrop-blur-sm
                ${expanded ? 'ring-1 ring-slate-600 bg-slate-800' : 'hover:translate-y-[-2px]'} 
                ${hoverBorder}`}
            onClick={() => setExpanded(!expanded)}
        >
            <div className="flex justify-between items-start mb-2">
                <span className="font-mono text-[10px] text-slate-500 group-hover:text-slate-400 transition-colors">
                    {log.timestamp.toLocaleTimeString()}
                </span>
                {log.duration_ms && (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-900/50 text-slate-400 border border-slate-700/50">
                        {log.duration_ms}ms
                    </span>
                )}
            </div>

            {/* Primary Info */}
            <div className="font-medium text-sm mb-1 text-slate-300 group-hover:text-white transition-colors leading-tight">
                {getLogTitle(log)}
            </div>

            {/* Secondary Info */}
            <div className={`text-xs break-words line-clamp-2 leading-relaxed ${log.success === false ? 'text-red-400' : 'text-slate-500 group-hover:text-slate-400'}`}>
                {getLogSubtitle(log)}
            </div>

            {/* Expanded Details */}
            {expanded && (
                <div className="mt-3 pt-3 border-t border-slate-700/50 text-[11px] font-mono animate-fade-in-down">
                    <div className="space-y-1.5">
                        {Object.entries(log)
                            .filter(([k]) => !['timestamp', 'level', 'category', 'message', 'source', 'logger', 'details', 'extra_data', 'success'].includes(k))
                            .map(([k, v]) => (
                                <div key={k} className="flex gap-2">
                                    <span className="text-slate-500 shrink-0 min-w-[60px]">{k}:</span>
                                    <span className="text-slate-300 break-all">{String(v)}</span>
                                </div>
                            ))}

                        {/* Recursive details viewer if present */}
                        {log.details && Object.keys(log.details).length > 0 && (
                            <div className="mt-2 text-slate-400">
                                <div className="text-xs mb-1 opacity-70">Details:</div>
                                <pre className="p-2 bg-black/40 rounded border border-slate-700/50 overflow-x-auto custom-scrollbar">
                                    {JSON.stringify(log.details, null, 2)}
                                </pre>
                            </div>
                        )}

                        {/* Show error explicitly if present */}
                        {log.error && (
                            <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-red-300 break-all">
                                <span className="font-bold">Error:</span> {log.error}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

// Helpers to format card titles based on log type
function getLogTitle(log) {
    if (log.category === 'request') {
        return (
            <div className="flex items-center gap-2">
                <span className={`text-[10px] px-1 rounded font-bold ${log.method === 'GET' ? 'bg-blue-500/20 text-blue-400' :
                    log.method === 'POST' ? 'bg-green-500/20 text-green-400' :
                        log.method === 'DELETE' ? 'bg-red-500/20 text-red-400' :
                            'bg-slate-500/20 text-slate-400'
                    }`}>{log.method}</span>
                <span className="truncate">{log.path}</span>
            </div>
        );
    }
    if (log.category === 'API') return log.message.split('(')[0];
    if (log.category === 'llm') return (
        <div className="flex flex-col">
            <span className="text-xs text-purple-400 opacity-80">{log.model}</span>
            <span>{log.operation}</span>
        </div>
    );
    if (log.category === 'agent') {
        return (
            <div className="flex items-center gap-2">
                <span>{log.agent}</span>
                <span className="text-slate-500">➜</span>
                <span className="text-emerald-400">{log.step}</span>
            </div>
        );
    }
    if (log.category === 'tool') return `${log.tool}.${log.operation}`;
    return log.message.slice(0, 50);
}

function getLogSubtitle(log) {
    if (log.error) return <span className="flex items-center gap-1">❌ {log.error}</span>;
    if (log.category === 'llm') return (
        <span className="flex items-center gap-2">
            <span>📝 {log.total_tokens || 0} tokens</span>
            {log.cost_estimate_usd && <span>💰 ${log.cost_estimate_usd}</span>}
        </span>
    );
    if (log.details?.question) return `Q: ${log.details.question}`;
    if (log.status_code) {
        const color = log.status_code >= 500 ? 'text-red-400' : log.status_code >= 400 ? 'text-yellow-400' : 'text-green-400';
        return <span className={color}>Status: {log.status_code}</span>;
    }
    if (log.source) return <span className="opacity-50 text-[10px] uppercase tracking-wider">{log.source}</span>;
    return '';
}

export default MetricsDashboard;
