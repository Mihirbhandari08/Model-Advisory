/**
 * Frontend Logging Utility for ModelAdvisor
 * 
 * Provides structured logging for:
 * - API calls with timing
 * - User interactions
 * - Errors with context
 */

const LOG_LEVELS = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
};

// Current log level (can be configured)
let currentLogLevel = LOG_LEVELS.INFO;

// In-memory log buffer for retrieval
const logBuffer = [];
const MAX_BUFFER_SIZE = 500;

/**
 * Format a log entry for console output
 */
function formatLog(level, category, message, data) {
    const timestamp = new Date().toISOString();
    return {
        timestamp,
        level,
        category,
        message,
        ...data,
    };
}

/**
 * Add log to buffer
 */
function addToBuffer(entry) {
    logBuffer.push(entry);
    if (logBuffer.length > MAX_BUFFER_SIZE) {
        logBuffer.shift();
    }
}

/**
 * Log with specific level
 */
function log(level, category, message, data = {}) {
    if (LOG_LEVELS[level] < currentLogLevel) return;

    const entry = formatLog(level, category, message, data);
    addToBuffer(entry);

    // Console output with styling
    const styles = {
        DEBUG: 'color: #888',
        INFO: 'color: #0ea5e9',
        WARN: 'color: #f59e0b',
        ERROR: 'color: #ef4444; font-weight: bold',
    };

    console.log(
        `%c[${level}] [${category}] ${message}`,
        styles[level],
        data
    );
}

/**
 * Logger API
 */
export const logger = {
    debug: (category, message, data) => log('DEBUG', category, message, data),
    info: (category, message, data) => log('INFO', category, message, data),
    warn: (category, message, data) => log('WARN', category, message, data),
    error: (category, message, data) => log('ERROR', category, message, data),

    /**
     * Log an API call with timing
     */
    logApiCall: async (url, options, fetchFn) => {
        const startTime = performance.now();
        const requestId = Math.random().toString(36).substring(7);

        logger.info('API', `Request: ${options.method || 'GET'} ${url}`, {
            requestId,
            body: options.body ? JSON.parse(options.body) : undefined,
        });

        try {
            const response = await fetchFn();
            const duration = Math.round(performance.now() - startTime);

            logger.info('API', `Response: ${response.status} (${duration}ms)`, {
                requestId,
                status: response.status,
                duration_ms: duration,
            });

            // Record metrics
            apiMetrics.recordRequest(url, options.method || 'GET', response.status, duration);

            return response;
        } catch (error) {
            const duration = Math.round(performance.now() - startTime);

            logger.error('API', `Error: ${error.message} (${duration}ms)`, {
                requestId,
                error: error.message,
                duration_ms: duration,
            });

            apiMetrics.recordError(url, error.message);
            throw error;
        }
    },

    /**
     * Log user interaction
     */
    logInteraction: (action, details = {}) => {
        logger.info('USER', action, { ...details, timestamp: Date.now() });
    },

    /**
     * Get recent logs
     */
    getRecentLogs: (count = 100) => {
        return logBuffer.slice(-count);
    },

    /**
     * Set log level
     */
    setLogLevel: (level) => {
        if (LOG_LEVELS[level] !== undefined) {
            currentLogLevel = LOG_LEVELS[level];
        }
    },
};

/**
 * API Metrics Tracker
 */
export const apiMetrics = {
    requests: [],
    errors: [],
    stats: {
        totalRequests: 0,
        totalErrors: 0,
        avgResponseTime: 0,
    },

    recordRequest(url, method, status, duration) {
        this.requests.push({
            timestamp: new Date().toISOString(),
            url,
            method,
            status,
            duration,
        });

        // Keep only last 100 requests
        if (this.requests.length > 100) {
            this.requests.shift();
        }

        // Update stats
        this.stats.totalRequests++;
        this.stats.avgResponseTime = Math.round(
            this.requests.reduce((sum, r) => sum + r.duration, 0) / this.requests.length
        );
    },

    recordError(url, message) {
        this.errors.push({
            timestamp: new Date().toISOString(),
            url,
            message,
        });

        if (this.errors.length > 50) {
            this.errors.shift();
        }

        this.stats.totalErrors++;
    },

    getStats() {
        return {
            ...this.stats,
            recentRequests: this.requests.slice(-10),
            recentErrors: this.errors.slice(-5),
        };
    },

    reset() {
        this.requests = [];
        this.errors = [];
        this.stats = {
            totalRequests: 0,
            totalErrors: 0,
            avgResponseTime: 0,
        };
    },
};

/**
 * Wrapped fetch with automatic logging
 */
export async function loggedFetch(url, options = {}) {
    return logger.logApiCall(url, options, () => fetch(url, options));
}

export default logger;
