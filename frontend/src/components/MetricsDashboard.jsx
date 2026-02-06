import { useState, useEffect } from 'react';
import { apiMetrics, logger } from '../utils/logger';

function MetricsDashboard({ onClose }) {
    const [metrics, setMetrics] = useState({
        api: apiMetrics.getStats(),
        logs: logger.getRecentLogs(50)
    });
    const [activeTab, setActiveTab] = useState('metrics'); // 'metrics' or 'logs'

    useEffect(() => {
        const fetchData = async () => {
            // Fetch backend logs
            let backendLogs = [];
            try {
                const res = await fetch('http://localhost:8000/api/logs?count=50');
                if (res.ok) {
                    const data = await res.json();
                    backendLogs = data.logs.map(log => ({
                        ...log,
                        source: 'BACKEND',
                        timestamp: new Date(log.timestamp) // Normalize timestamp
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

            // Merge and sort by timestamp (newest first)
            const allLogs = [...backendLogs, ...frontendLogs].sort(
                (a, b) => b.timestamp - a.timestamp
            ).slice(0, 100);

            setMetrics({
                api: apiMetrics.getStats(),
                logs: allLogs
            });
        };

        fetchData(); // Initial fetch

        // Refresh every second
        const interval = setInterval(fetchData, 1000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-700">
                    <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                        📊 System Diagnostics
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
                    >
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-700">
                    <button
                        onClick={() => setActiveTab('metrics')}
                        className={`flex-1 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'metrics'
                            ? 'border-primary-500 text-primary-400 bg-primary-500/5'
                            : 'border-transparent text-slate-400 hover:text-slate-200'
                            }`}
                    >
                        Metrics & Stats
                    </button>
                    <button
                        onClick={() => setActiveTab('logs')}
                        className={`flex-1 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'logs'
                            ? 'border-primary-500 text-primary-400 bg-primary-500/5'
                            : 'border-transparent text-slate-400 hover:text-slate-200'
                            }`}
                    >
                        Recent Logs
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {activeTab === 'metrics' ? (
                        <div className="space-y-6">
                            {/* Key Stats Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard
                                    label="Total Requests"
                                    value={metrics.api.totalRequests}
                                    icon="🔄"
                                />
                                <StatCard
                                    label="Avg Latency"
                                    value={`${metrics.api.avgResponseTime}ms`}
                                    icon="⚡"
                                    color={metrics.api.avgResponseTime > 1000 ? 'text-yellow-400' : 'text-green-400'}
                                />
                                <StatCard
                                    label="Errors"
                                    value={metrics.api.totalErrors}
                                    icon="⚠️"
                                    color={metrics.api.totalErrors > 0 ? 'text-red-400' : 'text-slate-200'}
                                />
                            </div>

                            {/* Recent Requests Table */}
                            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
                                <div className="px-4 py-3 border-b border-slate-700/50 font-medium text-slate-300">
                                    Recent API Calls
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm text-left">
                                        <thead className="text-xs text-slate-500 uppercase bg-slate-800/80">
                                            <tr>
                                                <th className="px-4 py-2">Time</th>
                                                <th className="px-4 py-2">Method</th>
                                                <th className="px-4 py-2">Endpoint</th>
                                                <th className="px-4 py-2">Status</th>
                                                <th className="px-4 py-2">Duration</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-700/50">
                                            {metrics.api.recentRequests.slice().reverse().map((req, i) => (
                                                <tr key={i} className="hover:bg-slate-700/30">
                                                    <td className="px-4 py-2 text-slate-400">
                                                        {new Date(req.timestamp).toLocaleTimeString()}
                                                    </td>
                                                    <td className="px-4 py-2 font-mono text-xs">{req.method}</td>
                                                    <td className="px-4 py-2 text-slate-300 truncate max-w-[200px]" title={req.url}>
                                                        {req.url.replace('http://localhost:8000', '')}
                                                    </td>
                                                    <td className="px-4 py-2">
                                                        <StatusBadge status={req.status} />
                                                    </td>
                                                    <td className="px-4 py-2 text-slate-400">{req.duration}ms</td>
                                                </tr>
                                            ))}
                                            {metrics.api.recentRequests.length === 0 && (
                                                <tr>
                                                    <td colSpan="5" className="px-4 py-8 text-center text-slate-500">
                                                        No requests recorded yet
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {metrics.logs.map((log, i) => (
                                <div key={i} className={`p-3 rounded-lg border text-sm font-mono ${log.level === 'ERROR' ? 'bg-red-900/10 border-red-500/30 text-red-300' :
                                        log.level === 'WARN' ? 'bg-yellow-900/10 border-yellow-500/30 text-yellow-300' :
                                            log.source === 'BACKEND' ? 'bg-indigo-900/10 border-indigo-500/30 text-indigo-300' :
                                                'bg-slate-800/50 border-slate-700/50 text-slate-300'
                                    }`}>
                                    <div className="flex justify-between items-start mb-1 opacity-70 text-xs">
                                        <div className="flex gap-2 items-center">
                                            <span>{log.timestamp.toLocaleTimeString()}</span>
                                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider ${log.source === 'BACKEND' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-500/20 text-slate-400'
                                                }`}>
                                                {log.source}
                                            </span>
                                        </div>
                                        <span className="uppercase font-bold tracking-wider">{log.category}</span>
                                    </div>
                                    <div>{log.message}</div>
                                    {/* Backend extra details often come as flattened fields, so we show them if present */}
                                    {log.source === 'BACKEND' && Object.keys(log).filter(k =>
                                        !['timestamp', 'level', 'category', 'message', 'source', 'logger', 'details'].includes(k)
                                    ).length > 0 && (
                                            <details className="mt-2">
                                                <summary className="cursor-pointer text-xs opacity-60 hover:opacity-100">
                                                    View Extra Data
                                                </summary>
                                                <pre className="mt-2 text-xs overflow-x-auto p-2 bg-black/20 rounded">
                                                    {JSON.stringify(
                                                        Object.fromEntries(
                                                            Object.entries(log).filter(([k]) =>
                                                                !['timestamp', 'level', 'category', 'message', 'source', 'logger', 'details'].includes(k)
                                                            )
                                                        ),
                                                        null, 2
                                                    )}
                                                </pre>
                                            </details>
                                        )}
                                    {/* Frontend/Agent details object */}
                                    {log.details && Object.keys(log.details).length > 0 && (
                                        <details className="mt-2">
                                            <summary className="cursor-pointer text-xs opacity-60 hover:opacity-100">
                                                View Details
                                            </summary>
                                            <pre className="mt-2 text-xs overflow-x-auto p-2 bg-black/20 rounded">
                                                {JSON.stringify(log.details, null, 2)}
                                            </pre>
                                        </details>
                                    )}
                                </div>
                            ))}
                            {metrics.logs.length === 0 && (
                                <div className="text-center text-slate-500 py-12">
                                    No logs recorded yet
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatCard({ label, value, icon, color = 'text-slate-100' }) {
    return (
        <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-slate-700/50 flex items-center justify-center text-2xl">
                {icon}
            </div>
            <div>
                <div className="text-sm text-slate-400">{label}</div>
                <div className={`text-2xl font-bold ${color}`}>{value}</div>
            </div>
        </div>
    );
}

function StatusBadge({ status }) {
    if (status >= 200 && status < 300) {
        return <span className="px-2 py-0.5 rounded text-xs bg-green-500/10 text-green-400 border border-green-500/20">OK</span>;
    }
    if (status >= 400 && status < 500) {
        return <span className="px-2 py-0.5 rounded text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">{status}</span>;
    }
    return <span className="px-2 py-0.5 rounded text-xs bg-red-500/10 text-red-400 border border-red-500/20">{status}</span>;
}

export default MetricsDashboard;
