"""
Advanced error handling and custom exceptions for production ML system.
Provides structured error responses, error tracking, and graceful degradation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import logging


logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    
    # Validation errors (4xx)
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_RANGE = "INVALID_RANGE"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Database errors (5xx)
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_TRANSACTION_ERROR = "DATABASE_TRANSACTION_ERROR"
    
    # Model errors (5xx)
    MODEL_LOAD_ERROR = "MODEL_LOAD_ERROR"
    MODEL_PREDICTION_ERROR = "MODEL_PREDICTION_ERROR"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    
    # API errors (5xx)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Authentication errors (4xx)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_API_KEY = "INVALID_API_KEY"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # System errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"


@dataclass
class APIError:
    """Structured API error response."""
    
    code: ErrorCode
    message: str
    status_code: int
    details: Dict[str, Any] | None = None
    request_id: str | None = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "timestamp": self._get_timestamp(),
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        if self.request_id:
            result["request_id"] = self.request_id
        return result
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get ISO format timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


class MLPipelineError(Exception):
    """Base exception for ML pipeline errors."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 500,
        details: Dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        
        logger.error(
            f"{code.value}: {message}",
            extra={"details": self.details, "cause": str(cause) if cause else None},
        )
        super().__init__(self.message)


class ValidationError(MLPipelineError):
    """Validation error for input data."""
    
    def __init__(self, message: str, details: Dict[str, Any] | None = None):
        super().__init__(
            code=ErrorCode.INVALID_INPUT,
            message=message,
            status_code=400,
            details=details,
        )


class MissingFieldError(MLPipelineError):
    """Error for missing required fields."""
    
    def __init__(self, field_name: str, message: str | None = None):
        msg = message or f"Missing required field: {field_name}"
        super().__init__(
            code=ErrorCode.MISSING_FIELD,
            message=msg,
            status_code=400,
            details={"field": field_name},
        )


class DatabaseError(MLPipelineError):
    """Base exception for database errors."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.DATABASE_CONNECTION_ERROR,
        cause: Exception | None = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=503,
            cause=cause,
        )


class QueryError(DatabaseError):
    """Error executing database query."""
    
    def __init__(self, query: str, cause: Exception | None = None):
        super().__init__(
            message=f"Database query failed: {query[:100]}...",
            code=ErrorCode.DATABASE_QUERY_ERROR,
            cause=cause,
        )


class ModelError(MLPipelineError):
    """Base exception for model-related errors."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.MODEL_PREDICTION_ERROR,
        cause: Exception | None = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=500,
            cause=cause,
        )


class ModelLoadError(ModelError):
    """Error loading model file."""
    
    def __init__(self, model_path: str, cause: Exception | None = None):
        super().__init__(
            message=f"Failed to load model from {model_path}",
            code=ErrorCode.MODEL_LOAD_ERROR,
            cause=cause,
        )


class PredictionError(ModelError):
    """Error during model prediction."""
    
    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.MODEL_PREDICTION_ERROR,
            cause=cause,
        )


class AuthenticationError(MLPipelineError):
    """Authentication/authorization error."""
    
    def __init__(self, message: str, code: ErrorCode = ErrorCode.INVALID_API_KEY):
        super().__init__(
            code=code,
            message=message,
            status_code=401,
        )


class RateLimitError(MLPipelineError):
    """Rate limit exceeded error."""
    
    def __init__(self, limit: int, window_seconds: int):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            status_code=429,
            details={"limit": limit, "window_seconds": window_seconds},
        )


class CircuitBreakerError(MLPipelineError):
    """Circuit breaker is open."""
    
    def __init__(self, service_name: str):
        super().__init__(
            code=ErrorCode.CIRCUIT_BREAKER_OPEN,
            message=f"Service '{service_name}' is temporarily unavailable",
            status_code=503,
            details={"service": service_name},
        )


class TimeoutError(MLPipelineError):
    """Request timeout error."""
    
    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            code=ErrorCode.TIMEOUT_ERROR,
            message=f"Operation '{operation}' timed out after {timeout_seconds}s",
            status_code=504,
            details={"operation": operation, "timeout_seconds": timeout_seconds},
        )


def handle_error(exc: Exception, request_id: str = "") -> APIError:
    """
    Convert exception to structured API error response.
    O(1) - constant time error mapping.
    """
    if isinstance(exc, MLPipelineError):
        return APIError(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            request_id=request_id,
        )
    
    # Fallback for unexpected errors
    logger.error(f"Unhandled exception: {exc}", exc_info=exc)
    return APIError(
        code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        status_code=500,
        details={"error_type": type(exc).__name__},
        request_id=request_id,
    )
