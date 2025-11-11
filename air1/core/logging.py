"""
Structured logging module using Loguru
"""

from loguru import logger
from contextvars import ContextVar
from typing import Any, Dict, Optional
import json
import sys
from functools import wraps
import asyncio
import time

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def get_logger():
    """Get configured logger instance"""
    return logger


class StructuredLogger:
    """Wrapper for structured logging with context"""

    @staticmethod
    def bind(**kwargs) -> logger:
        """Bind context to logger"""
        context = {
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            **kwargs,
        }
        # Remove None values
        context = {k: v for k, v in context.items() if v is not None}
        return logger.bind(**context)

    @staticmethod
    def info(message: str, **kwargs):
        """Log info with context"""
        StructuredLogger.bind(**kwargs).info(message)

    @staticmethod
    def error(message: str, **kwargs):
        """Log error with context"""
        StructuredLogger.bind(**kwargs).error(message)

    @staticmethod
    def warning(message: str, **kwargs):
        """Log warning with context"""
        StructuredLogger.bind(**kwargs).warning(message)

    @staticmethod
    def debug(message: str, **kwargs):
        """Log debug with context"""
        StructuredLogger.bind(**kwargs).debug(message)

    @staticmethod
    def exception(message: str, **kwargs):
        """Log exception with context"""
        StructuredLogger.bind(**kwargs).exception(message)


def log_execution_time(func):
    """Decorator to log function execution time"""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            StructuredLogger.info(
                "Function executed successfully",
                function=func.__name__,
                duration=duration,
                status="success",
            )
            return result
        except Exception as e:
            duration = time.time() - start
            StructuredLogger.error(
                "Function failed",
                function=func.__name__,
                duration=duration,
                status="error",
                error=str(e),
            )
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            StructuredLogger.info(
                "Function executed successfully",
                function=func.__name__,
                duration=duration,
                status="success",
            )
            return result
        except Exception as e:
            duration = time.time() - start
            StructuredLogger.error(
                "Function failed",
                function=func.__name__,
                duration=duration,
                status="error",
                error=str(e),
            )
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_database_query(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    duration: Optional[float] = None,
):
    """Log database query with parameters"""
    log_data = {
        "query": query[:500] if len(query) > 500 else query,  # Truncate long queries
        "type": "database",
    }

    if params:
        # Don't log sensitive data
        safe_params = {
            k: "***" if "password" in k.lower() or "token" in k.lower() else v
            for k, v in params.items()
        }
        log_data["params"] = safe_params

    if duration:
        log_data["duration"] = duration

    StructuredLogger.debug("Database query executed", **log_data)


def log_http_request(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration: Optional[float] = None,
    **kwargs,
):
    """Log HTTP request"""
    log_data = {"method": method, "url": url, "type": "http_request"}

    if status_code:
        log_data["status_code"] = status_code

    if duration:
        log_data["duration"] = duration

    log_data.update(kwargs)

    if status_code and status_code >= 400:
        StructuredLogger.error("HTTP request failed", **log_data)
    else:
        StructuredLogger.info("HTTP request completed", **log_data)


# JSON formatter for structured logs
def json_formatter(record):
    """Format log record as JSON"""
    log_format = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }

    # Add extra fields
    if record.get("extra"):
        log_format.update(record["extra"])

    # Add exception info if present
    if record.get("exception"):
        log_format["exception"] = record["exception"]

    return json.dumps(log_format)


def setup_json_logging():
    """Setup JSON formatted logging (useful for production)"""
    logger.remove()
    logger.add(sys.stdout, format=json_formatter, serialize=False)


# Export main logger and structured logger
structured_logger = StructuredLogger()
__all__ = [
    "logger",
    "structured_logger",
    "log_execution_time",
    "log_database_query",
    "log_http_request",
    "setup_json_logging",
    "request_id_var",
    "user_id_var",
]
