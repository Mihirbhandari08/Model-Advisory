"""
Centralized Logging Module for ModelAdvisor Backend.

Provides structured JSON logging for:
- HTTP requests/responses
- LLM API calls (Gemini)
- Agent execution steps
- Tool invocations
"""
import logging
import json
import time
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
from contextlib import contextmanager
import traceback


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-structured log entries."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class ModelAdvisorLogger:
    """Centralized logger for the ModelAdvisor application."""
    
    _instance = None
    _logs_buffer: list = []
    MAX_BUFFER_SIZE = 1000
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._logs_buffer = []
        
        # Create main logger
        self.logger = logging.getLogger("model_advisor")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # Clear any existing handlers
        
        # Console handler with JSON formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # Create specialized loggers
        self.request_logger = logging.getLogger("model_advisor.request")
        self.llm_logger = logging.getLogger("model_advisor.llm")
        self.agent_logger = logging.getLogger("model_advisor.agent")
        self.tool_logger = logging.getLogger("model_advisor.tool")
    
    def _add_to_buffer(self, entry: Dict[str, Any]):
        """Add log entry to in-memory buffer for retrieval."""
        self._logs_buffer.append({
            **entry,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        # Keep buffer size limited
        if len(self._logs_buffer) > self.MAX_BUFFER_SIZE:
            self._logs_buffer = self._logs_buffer[-self.MAX_BUFFER_SIZE:]
    
    def get_recent_logs(self, count: int = 100, level: Optional[str] = None, 
                        category: Optional[str] = None) -> list:
        """Get recent logs from buffer with optional filtering."""
        logs = self._logs_buffer[-count:]
        
        if level:
            logs = [l for l in logs if l.get("level") == level.upper()]
        if category:
            logs = [l for l in logs if l.get("category") == category]
        
        return logs
    
    def log_request(self, method: str, path: str, status_code: int, 
                    duration_ms: float, request_id: str = None,
                    error: str = None):
        """Log an HTTP request/response."""
        entry = {
            "category": "request",
            "level": "ERROR" if status_code >= 500 else "INFO",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "request_id": request_id,
        }
        if error:
            entry["error"] = error
        
        self._add_to_buffer(entry)
        
        log_msg = f"{method} {path} -> {status_code} ({duration_ms:.2f}ms)"
        record = self.request_logger.makeRecord(
            "model_advisor.request", 
            logging.ERROR if status_code >= 500 else logging.INFO,
            "", 0, log_msg, (), None
        )
        record.extra_data = entry
        self.request_logger.handle(record)
    
    def log_llm_call(self, model: str, operation: str, 
                     prompt_tokens: int = None, completion_tokens: int = None,
                     duration_ms: float = None, success: bool = True,
                     error: str = None, cost_estimate: float = None):
        """Log an LLM API call."""
        entry = {
            "category": "llm",
            "level": "ERROR" if not success else "INFO",
            "model": model,
            "operation": operation,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": (prompt_tokens or 0) + (completion_tokens or 0),
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
            "success": success,
            "cost_estimate_usd": cost_estimate,
        }
        if error:
            entry["error"] = error
        
        self._add_to_buffer(entry)
        
        log_msg = f"LLM:{model} {operation} - tokens:{entry['total_tokens']} ({duration_ms:.2f}ms)"
        record = self.llm_logger.makeRecord(
            "model_advisor.llm",
            logging.ERROR if not success else logging.INFO,
            "", 0, log_msg, (), None
        )
        record.extra_data = entry
        self.llm_logger.handle(record)
    
    def log_agent_step(self, agent: str, step: str, 
                       duration_ms: float = None, success: bool = True,
                       details: Dict = None, error: str = None):
        """Log an agent execution step."""
        entry = {
            "category": "agent",
            "level": "ERROR" if not success else "INFO",
            "agent": agent,
            "step": step,
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
            "success": success,
            "details": details,
        }
        if error:
            entry["error"] = error
        
        self._add_to_buffer(entry)
        
        log_msg = f"Agent:{agent} -> {step} ({'✓' if success else '✗'})"
        if duration_ms:
            log_msg += f" ({duration_ms:.2f}ms)"
        
        record = self.agent_logger.makeRecord(
            "model_advisor.agent",
            logging.ERROR if not success else logging.INFO,
            "", 0, log_msg, (), None
        )
        record.extra_data = entry
        self.agent_logger.handle(record)
    
    def log_tool_call(self, tool: str, operation: str,
                      duration_ms: float = None, success: bool = True,
                      input_size: int = None, output_size: int = None,
                      error: str = None):
        """Log a tool invocation."""
        entry = {
            "category": "tool",
            "level": "ERROR" if not success else "INFO",
            "tool": tool,
            "operation": operation,
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
            "success": success,
            "input_size": input_size,
            "output_size": output_size,
        }
        if error:
            entry["error"] = error
        
        self._add_to_buffer(entry)
        
        log_msg = f"Tool:{tool}.{operation} ({'✓' if success else '✗'})"
        if duration_ms:
            log_msg += f" ({duration_ms:.2f}ms)"
        
        record = self.tool_logger.makeRecord(
            "model_advisor.tool",
            logging.ERROR if not success else logging.INFO,
            "", 0, log_msg, (), None
        )
        record.extra_data = entry
        self.tool_logger.handle(record)


# Global logger instance
logger = ModelAdvisorLogger()


# ============ Decorators for automatic logging ============

def log_llm_operation(model: str, operation: str):
    """Decorator to automatically log LLM operations with timing."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                
                # Estimate tokens (rough approximation)
                prompt_tokens = len(str(kwargs.get('prompt', args[1] if len(args) > 1 else ''))) // 4
                completion_tokens = len(str(result)) // 4 if result else 0
                
                logger.log_llm_call(
                    model=model,
                    operation=operation,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.log_llm_call(
                    model=model,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.log_llm_call(
                    model=model,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.log_llm_call(
                    model=model,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def log_agent_operation(agent_name: str):
    """Decorator to log agent method execution."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            step_name = func.__name__
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.log_agent_step(
                    agent=agent_name,
                    step=step_name,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.log_agent_step(
                    agent=agent_name,
                    step=step_name,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            step_name = func.__name__
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.log_agent_step(
                    agent=agent_name,
                    step=step_name,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.log_agent_step(
                    agent=agent_name,
                    step=step_name,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def log_tool_operation(tool_name: str):
    """Decorator to log tool invocations."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            operation = func.__name__
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.log_tool_call(
                    tool=tool_name,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=True,
                    output_size=len(str(result)) if result else 0
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.log_tool_call(
                    tool=tool_name,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            operation = func.__name__
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.log_tool_call(
                    tool=tool_name,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=True,
                    output_size=len(str(result)) if result else 0
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.log_tool_call(
                    tool=tool_name,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


@contextmanager
def log_step(agent: str, step: str):
    """Context manager for logging execution steps with timing."""
    start = time.time()
    try:
        yield
        duration_ms = (time.time() - start) * 1000
        logger.log_agent_step(agent, step, duration_ms, success=True)
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        logger.log_agent_step(agent, step, duration_ms, success=False, error=str(e))
        raise
