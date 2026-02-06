"""
Metrics Collection Module for ModelAdvisor Backend.

Collects and aggregates metrics for:
- HTTP request counts and latency
- LLM usage (tokens, costs, latency)
- Agent execution metrics
- Tool usage statistics
- Error tracking
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import threading


@dataclass
class LatencyStats:
    """Track latency statistics with min/max/avg."""
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    
    def record(self, duration_ms: float):
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
    
    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "count": self.count,
            "total_ms": round(self.total_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else None,
            "max_ms": round(self.max_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
        }


class MetricsCollector:
    """Centralized metrics collector for the ModelAdvisor application."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._start_time = datetime.utcnow()
        
        # Request metrics
        self._request_counts: Dict[str, int] = defaultdict(int)  # endpoint -> count
        self._status_counts: Dict[int, int] = defaultdict(int)   # status_code -> count
        self._request_latency: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        
        # LLM metrics
        self._llm_calls: Dict[str, int] = defaultdict(int)  # model -> count
        self._llm_tokens: Dict[str, Dict[str, int]] = defaultdict(lambda: {"prompt": 0, "completion": 0})
        self._llm_latency: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        self._llm_errors: Dict[str, int] = defaultdict(int)
        self._llm_cost_estimate: float = 0.0
        
        # Agent metrics
        self._agent_executions: Dict[str, int] = defaultdict(int)
        self._agent_latency: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        self._agent_errors: Dict[str, int] = defaultdict(int)
        
        # Tool metrics
        self._tool_calls: Dict[str, int] = defaultdict(int)
        self._tool_latency: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        self._tool_errors: Dict[str, int] = defaultdict(int)
        
        # Error tracking
        self._errors: List[Dict] = []
        self.MAX_ERRORS = 100
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                       duration_ms: float):
        """Record an HTTP request."""
        key = f"{method}:{endpoint}"
        self._request_counts[key] += 1
        self._status_counts[status_code] += 1
        self._request_latency[key].record(duration_ms)
    
    def record_llm_call(self, model: str, prompt_tokens: int = 0, 
                        completion_tokens: int = 0, duration_ms: float = 0,
                        success: bool = True, cost_estimate: float = 0):
        """Record an LLM API call."""
        self._llm_calls[model] += 1
        self._llm_tokens[model]["prompt"] += prompt_tokens
        self._llm_tokens[model]["completion"] += completion_tokens
        self._llm_latency[model].record(duration_ms)
        self._llm_cost_estimate += cost_estimate
        
        if not success:
            self._llm_errors[model] += 1
    
    def record_agent_execution(self, agent: str, step: str, 
                               duration_ms: float = 0, success: bool = True):
        """Record an agent execution step."""
        key = f"{agent}.{step}"
        self._agent_executions[key] += 1
        self._agent_latency[key].record(duration_ms)
        
        if not success:
            self._agent_errors[agent] += 1
    
    def record_tool_call(self, tool: str, operation: str, 
                         duration_ms: float = 0, success: bool = True):
        """Record a tool invocation."""
        key = f"{tool}.{operation}"
        self._tool_calls[key] += 1
        self._tool_latency[key].record(duration_ms)
        
        if not success:
            self._tool_errors[tool] += 1
    
    def record_error(self, category: str, error_type: str, 
                     message: str, details: Dict = None):
        """Record an error for tracking."""
        self._errors.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "category": category,
            "type": error_type,
            "message": message,
            "details": details,
        })
        
        # Keep error buffer limited
        if len(self._errors) > self.MAX_ERRORS:
            self._errors = self._errors[-self.MAX_ERRORS:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        return {
            "system": {
                "start_time": self._start_time.isoformat() + "Z",
                "uptime_seconds": round(uptime, 2),
                "collected_at": datetime.utcnow().isoformat() + "Z",
            },
            "requests": {
                "total": sum(self._request_counts.values()),
                "by_endpoint": dict(self._request_counts),
                "by_status": dict(self._status_counts),
                "latency_by_endpoint": {
                    k: v.to_dict() for k, v in self._request_latency.items()
                },
            },
            "llm": {
                "total_calls": sum(self._llm_calls.values()),
                "calls_by_model": dict(self._llm_calls),
                "tokens_by_model": {
                    k: {
                        "prompt": v["prompt"],
                        "completion": v["completion"],
                        "total": v["prompt"] + v["completion"],
                    } for k, v in self._llm_tokens.items()
                },
                "total_tokens": sum(
                    v["prompt"] + v["completion"] 
                    for v in self._llm_tokens.values()
                ),
                "latency_by_model": {
                    k: v.to_dict() for k, v in self._llm_latency.items()
                },
                "errors_by_model": dict(self._llm_errors),
                "total_errors": sum(self._llm_errors.values()),
                "estimated_cost_usd": round(self._llm_cost_estimate, 4),
            },
            "agents": {
                "total_executions": sum(self._agent_executions.values()),
                "executions_by_step": dict(self._agent_executions),
                "latency_by_step": {
                    k: v.to_dict() for k, v in self._agent_latency.items()
                },
                "errors_by_agent": dict(self._agent_errors),
                "total_errors": sum(self._agent_errors.values()),
            },
            "tools": {
                "total_calls": sum(self._tool_calls.values()),
                "calls_by_operation": dict(self._tool_calls),
                "latency_by_operation": {
                    k: v.to_dict() for k, v in self._tool_latency.items()
                },
                "errors_by_tool": dict(self._tool_errors),
                "total_errors": sum(self._tool_errors.values()),
            },
            "errors": {
                "total": len(self._errors),
                "recent": self._errors[-10:],  # Last 10 errors
            },
        }
    
    def reset(self):
        """Reset all metrics (useful for testing)."""
        self.__init__()
        self._initialized = False
        self.__init__()


# Global metrics instance
metrics = MetricsCollector()
