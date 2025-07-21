# src/utils/circuit_breaker.py
"""
Circuit Breaker Pattern Implementation for External API Calls
Provides automatic failure detection and recovery mechanisms
"""
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds to wait before trying again
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: int = 30  # Request timeout in seconds
    
    # Failure conditions
    failure_exceptions: tuple = (Exception,)
    failure_status_codes: tuple = (500, 502, 503, 504, 429)


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeouts: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls
    
    Automatically opens when failure threshold is reached,
    and attempts recovery after timeout period.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.last_failure_time = None
        self.lock = threading.RLock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: When circuit is open
            Original exceptions: When circuit is closed/half-open
        """
        with self.lock:
            self.stats.total_requests += 1
            
            # Check if circuit should transition to half-open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._half_open_circuit()
            
            # Block calls when circuit is open
            if self.state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker '{self.name}' is OPEN, blocking call")
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
        
        # Execute the function
        start_time = time.time()
        try:
            # Apply timeout if configured
            if hasattr(func, '__name__') and 'timeout' in kwargs:
                result = func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            
            # Record success
            with self.lock:
                self._record_success(execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Record failure
            with self.lock:
                self._record_failure(e, execution_time)
            
            # Re-raise the original exception
            raise
    
    def _record_success(self, execution_time: float):
        """Record a successful call"""
        self.stats.successful_requests += 1
        self.stats.current_consecutive_failures = 0
        self.stats.current_consecutive_successes += 1
        self.stats.last_success_time = datetime.now()
        
        logger.debug(f"Circuit breaker '{self.name}' recorded success (time: {execution_time:.2f}s)")
        
        # If in half-open state, check if we should close
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.current_consecutive_successes >= self.config.success_threshold:
                self._close_circuit()
    
    def _record_failure(self, exception: Exception, execution_time: float):
        """Record a failed call"""
        self.stats.failed_requests += 1
        self.stats.current_consecutive_successes = 0
        self.stats.current_consecutive_failures += 1
        self.stats.last_failure_time = datetime.now()
        self.last_failure_time = time.time()
        
        # Check if it's a timeout
        if execution_time >= self.config.timeout:
            self.stats.timeouts += 1
        
        logger.warning(f"Circuit breaker '{self.name}' recorded failure: {type(exception).__name__}: {str(exception)}")
        
        # Check if we should open the circuit
        if self.state == CircuitState.CLOSED and self.stats.current_consecutive_failures >= self.config.failure_threshold:
            self._open_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            self._open_circuit()
    
    def _open_circuit(self):
        """Open the circuit breaker"""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.stats.circuit_opened_count += 1
            logger.error(f"Circuit breaker '{self.name}' OPENED after {self.stats.current_consecutive_failures} consecutive failures")
    
    def _half_open_circuit(self):
        """Transition to half-open state"""
        self.state = CircuitState.HALF_OPEN
        self.stats.current_consecutive_successes = 0
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")
    
    def _close_circuit(self):
        """Close the circuit breaker"""
        self.state = CircuitState.CLOSED
        self.stats.current_consecutive_failures = 0
        logger.info(f"Circuit breaker '{self.name}' CLOSED after {self.stats.current_consecutive_successes} consecutive successes")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        with self.lock:
            stats_dict = {
                'name': self.name,
                'state': self.state.value,
                'total_requests': self.stats.total_requests,
                'successful_requests': self.stats.successful_requests,
                'failed_requests': self.stats.failed_requests,
                'success_rate': (self.stats.successful_requests / max(self.stats.total_requests, 1)) * 100,
                'timeouts': self.stats.timeouts,
                'circuit_opened_count': self.stats.circuit_opened_count,
                'current_consecutive_failures': self.stats.current_consecutive_failures,
                'current_consecutive_successes': self.stats.current_consecutive_successes,
                'last_failure_time': self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
                'last_success_time': self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'recovery_timeout': self.config.recovery_timeout,
                    'success_threshold': self.config.success_threshold,
                    'timeout': self.config.timeout
                }
            }
            
            return stats_dict
    
    def reset(self):
        """Manually reset the circuit breaker"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.stats.current_consecutive_failures = 0
            self.stats.current_consecutive_successes = 0
            self.last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def force_open(self):
        """Manually open the circuit breaker"""
        with self.lock:
            self._open_circuit()
            logger.info(f"Circuit breaker '{self.name}' manually opened")


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers
    Provides centralized configuration and monitoring
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.lock = threading.RLock()
    
    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """
        Get or create a circuit breaker
        
        Args:
            name: Circuit breaker name
            config: Configuration (uses default if None)
            
        Returns:
            CircuitBreaker instance
        """
        with self.lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(name, config)
                logger.info(f"Created new circuit breaker: {name}")
            
            return self.circuit_breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        with self.lock:
            return {name: cb.get_stats() for name, cb in self.circuit_breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers"""
        with self.lock:
            for cb in self.circuit_breakers.values():
                cb.reset()
            logger.info("All circuit breakers reset")
    
    def get_unhealthy_circuits(self) -> Dict[str, CircuitBreaker]:
        """Get circuit breakers that are open or have high failure rates"""
        unhealthy = {}
        
        with self.lock:
            for name, cb in self.circuit_breakers.items():
                stats = cb.get_stats()
                
                # Consider unhealthy if open or high failure rate
                if (cb.get_state() == CircuitState.OPEN or 
                    (stats['total_requests'] > 10 and stats['success_rate'] < 50)):
                    unhealthy[name] = cb
        
        return unhealthy


# Global circuit breaker manager instance
_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager"""
    return _circuit_breaker_manager


def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """
    Decorator to add circuit breaker protection to a function
    
    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        cb = get_circuit_breaker_manager().get_circuit_breaker(name, config)
        return cb(func)
    
    return decorator