"""
Circuit breaker pattern and rate limiting implementation.
Provides fault tolerance and protection against overload.
"""

from __future__ import annotations

import time
from enum import Enum
from threading import Lock
from collections import deque
from typing import Any, Callable, Deque, Dict

from src.utils.errors import CircuitBreakerError, RateLimitError
from src.utils.logger import get_logger


logger = get_logger("resilience")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    Prevents cascading failures by stopping requests to failing services.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self._lock = Lock()
    
    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.
        O(1) state check + function execution time.
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerError(self.name)
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    logger.info(f"Circuit breaker '{self.name}' closed (recovered)")
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold and self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' opened ({self.failure_count} failures)")
    
    def _should_attempt_reset(self) -> bool:
        """Check if timeout has elapsed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.timeout_seconds
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state for monitoring."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
            }


class RateLimiter:
    """
    Token bucket rate limiter.
    Allows N requests per time window using efficient sliding window.
    """
    
    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Deque[float] = deque()
        self._lock = Lock()
    
    def allow_request(self) -> bool:
        """
        Check if request is allowed.
        O(k) where k = requests in window (typically small, O(1) amortized).
        """
        now = time.time()
        
        with self._lock:
            # Remove old requests outside the window
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Check if at limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        with self._lock:
            return {
                "requests_in_window": len(self.requests),
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "available_slots": max(0, self.max_requests - len(self.requests)),
            }


class PerKeyRateLimiter:
    """
    Per-key rate limiter for multi-user scenarios (e.g., API keys).
    Each key has its own rate limit bucket.
    """
    
    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.limiters: Dict[str, RateLimiter] = {}
        self._lock = Lock()
    
    def allow_request(self, key: str) -> bool:
        """
        Check if request for key is allowed.
        O(1) amortized - create limiter once per key.
        """
        with self._lock:
            if key not in self.limiters:
                self.limiters[key] = RateLimiter(
                    self.max_requests,
                    self.window_seconds,
                )
            
            if not self.limiters[key].allow_request():
                raise RateLimitError(self.max_requests, int(self.window_seconds))
        
        return True
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all keys."""
        with self._lock:
            return {
                key: limiter.get_stats()
                for key, limiter in self.limiters.items()
            }


# Global circuit breaker registry
circuit_breakers: Dict[str, CircuitBreaker] = {}
_breaker_lock = Lock()


def get_circuit_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.
    O(1) - cached lookup.
    """
    global circuit_breakers
    
    with _breaker_lock:
        if name not in circuit_breakers:
            circuit_breakers[name] = CircuitBreaker(name, **kwargs)
        return circuit_breakers[name]


def with_circuit_breaker(breaker_name: str):
    """
    Decorator for function-level circuit breaker.
    Usage: @with_circuit_breaker("database")
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(breaker_name)
        
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator
