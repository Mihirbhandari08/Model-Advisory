export default function ResultCard({
    icon,
    title,
    children,
    gradient = '',
    glow = '',
    collapsible = false,
    collapsed = false,
    onToggle
}) {
    return (
        <div className={`glass-card overflow-hidden animate-slide-up ${glow}`}>
            {/* Gradient accent bar */}
            {gradient && (
                <div className={`h-1 bg-gradient-to-r ${gradient}`} />
            )}

            <div className="p-6">
                {/* Header */}
                <div
                    className={`flex items-center justify-between mb-4 ${collapsible ? 'cursor-pointer' : ''}`}
                    onClick={collapsible ? onToggle : undefined}
                >
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">{icon}</span>
                        <h3 className="text-xl font-semibold text-slate-100">{title}</h3>
                    </div>

                    {collapsible && (
                        <button className="p-1 hover:bg-slate-700/50 rounded-lg transition-colors">
                            <svg
                                className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${collapsed ? '' : 'rotate-180'}`}
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>
                    )}
                </div>

                {/* Content */}
                <div className={`transition-all duration-300 ${collapsed ? 'hidden' : ''}`}>
                    {children}
                </div>

                {/* Collapsed indicator */}
                {collapsed && (
                    <p className="text-sm text-slate-500">Click to expand</p>
                )}
            </div>
        </div>
    )
}
