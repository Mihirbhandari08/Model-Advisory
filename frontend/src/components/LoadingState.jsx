export default function LoadingState() {
    const steps = [
        { icon: '🔍', text: 'Extracting constraints from your query', delay: 0 },
        { icon: '🌐', text: 'Searching Hugging Face model hub', delay: 1 },
        { icon: '⚡', text: 'Filtering by your requirements', delay: 2 },
        { icon: '💰', text: 'Estimating deployment costs', delay: 3 },
        { icon: '✨', text: 'Generating recommendations', delay: 4 },
    ]

    return (
        <div className="glass-card p-8 animate-fade-in">
            <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-primary-500 to-accent-500 animate-pulse" />
                <h3 className="text-xl font-semibold text-slate-200">
                    Finding your ideal model<span className="loading-dots"></span>
                </h3>
            </div>

            <div className="space-y-3">
                {steps.map((step, i) => (
                    <div
                        key={i}
                        className="flex items-center gap-3 animate-slide-up"
                        style={{ animationDelay: `${step.delay * 0.3}s` }}
                    >
                        <span className="text-xl">{step.icon}</span>
                        <div className="flex-1 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full animate-pulse"
                                style={{
                                    width: `${Math.min(100, (i + 1) * 25)}%`,
                                    animationDelay: `${step.delay * 0.3}s`
                                }}
                            />
                        </div>
                        <span className="text-sm text-slate-400 min-w-[200px]">{step.text}</span>
                    </div>
                ))}
            </div>

            <p className="mt-6 text-center text-slate-500 text-sm">
                This usually takes 5-10 seconds depending on model availability
            </p>
        </div>
    )
}
