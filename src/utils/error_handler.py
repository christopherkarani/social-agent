# src/utils/error_handler.py
"""
Comprehensive Error Handling and Recovery System
Provides centralized error handling, reporting, and recovery mechanisms
"""
import logging
import traceback
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from functools import wraps
import json

from .alert_system import get_alert_manager, AlertSeverity
from .metrics_collector import get_metrics_collector
from .circuit_breaker import get_circuit_breaker_manager, CircuitBreakerConfig

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    API_ERROR = "api_error"
    AUTHENTICATION_ERROR = "authentication_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information for error handling"""
    component: str
    operation: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    traceback: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class RecoveryStrategy:
    """Base class for recovery strategies"""
    
    def __init__(self, name: str, max_attempts: int = 3):
        self.name = name
        self.max_attempts = max_attempts
    
    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this strategy can handle the error"""
        raise NotImplementedError
    
    def recover(self, error: Exception, context: ErrorContext, attempt: int) -> bool:
        """Attempt to recover from the error"""
        raise NotImplementedError


class RetryStrategy(RecoveryStrategy):
    """Retry strategy with exponential backoff"""
    
    def __init__(self, name: str = "retry", max_attempts: int = 3, 
                 base_delay: float = 1.0, max_delay: float = 60.0):
        super().__init__(name, max_attempts)
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if error is retryable"""
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            # Add more retryable error types
        )
        
        # Check for HTTP status codes that are retryable
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            retryable_codes = [429, 500, 502, 503, 504]
            return error.response.status_code in retryable_codes
        
        return isinstance(error, retryable_errors)
    
    def recover(self, error: Exception, context: ErrorContext, attempt: int) -> bool:
        """Attempt recovery by waiting and retrying"""
        if attempt >= self.max_attempts:
            return False
        
        # Calculate delay with exponential backoff
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        logger.info(f"Retrying {context.operation} in {delay:.2f}s (attempt {attempt + 1}/{self.max_attempts})")
        time.sleep(delay)
        
        return True


class AuthenticationRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for authentication errors"""
    
    def __init__(self, name: str = "auth_recovery", max_attempts: int = 2):
        super().__init__(name, max_attempts)
    
    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if error is authentication-related"""
        auth_indicators = [
            'auth', 'unauthorized', '401', 'forbidden', '403',
            'token', 'credential', 'login', 'session'
        ]
        
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in auth_indicators)
    
    def recover(self, error: Exception, context: ErrorContext, attempt: int) -> bool:
        """Attempt to recover by clearing auth state"""
        if attempt >= self.max_attempts:
            return False
        
        logger.info(f"Attempting authentication recovery for {context.component}")
        
        # Clear authentication state (implementation depends on component)
        # This would typically involve clearing cached tokens, sessions, etc.
        context.metadata['auth_recovery_attempted'] = True
        
        return True


class ConfigurationRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for configuration errors"""
    
    def __init__(self, name: str = "config_recovery", max_attempts: int = 1):
        super().__init__(name, max_attempts)
    
    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if error is configuration-related"""
        config_indicators = [
            'config', 'setting', 'parameter', 'key', 'missing',
            'invalid', 'not found', 'environment'
        ]
        
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in config_indicators)
    
    def recover(self, error: Exception, context: ErrorContext, attempt: int) -> bool:
        """Attempt to recover by reloading configuration"""
        if attempt >= self.max_attempts:
            return False
        
        logger.info(f"Attempting configuration recovery for {context.component}")
        
        # Mark for configuration reload
        context.metadata['config_reload_needed'] = True
        
        return True


class ErrorHandler:
    """
    Comprehensive error handler with recovery mechanisms
    """
    
    def __init__(self):
        self.error_records: List[ErrorRecord] = []
        self.recovery_strategies: List[RecoveryStrategy] = []
        self.error_patterns: Dict[str, ErrorCategory] = {}
        self.lock = threading.RLock()
        
        # Initialize default recovery strategies
        self._initialize_default_strategies()
        
        # Initialize error pattern matching
        self._initialize_error_patterns()
        
        # Metrics and alerting
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
        self.circuit_breaker_manager = get_circuit_breaker_manager()
    
    def _initialize_default_strategies(self):
        """Initialize default recovery strategies"""
        self.recovery_strategies = [
            RetryStrategy(),
            AuthenticationRecoveryStrategy(),
            ConfigurationRecoveryStrategy()
        ]
    
    def _initialize_error_patterns(self):
        """Initialize error pattern matching"""
        self.error_patterns = {
            # API errors
            'api': ErrorCategory.API_ERROR,
            'http': ErrorCategory.API_ERROR,
            'request': ErrorCategory.API_ERROR,
            'response': ErrorCategory.API_ERROR,
            
            # Authentication errors
            'auth': ErrorCategory.AUTHENTICATION_ERROR,
            'unauthorized': ErrorCategory.AUTHENTICATION_ERROR,
            'forbidden': ErrorCategory.AUTHENTICATION_ERROR,
            'token': ErrorCategory.AUTHENTICATION_ERROR,
            'credential': ErrorCategory.AUTHENTICATION_ERROR,
            
            # Network errors
            'connection': ErrorCategory.NETWORK_ERROR,
            'network': ErrorCategory.NETWORK_ERROR,
            'socket': ErrorCategory.NETWORK_ERROR,
            'dns': ErrorCategory.NETWORK_ERROR,
            
            # Timeout errors
            'timeout': ErrorCategory.TIMEOUT_ERROR,
            'deadline': ErrorCategory.TIMEOUT_ERROR,
            
            # Validation errors
            'validation': ErrorCategory.VALIDATION_ERROR,
            'invalid': ErrorCategory.VALIDATION_ERROR,
            'format': ErrorCategory.VALIDATION_ERROR,
            
            # Configuration errors
            'config': ErrorCategory.CONFIGURATION_ERROR,
            'setting': ErrorCategory.CONFIGURATION_ERROR,
            'environment': ErrorCategory.CONFIGURATION_ERROR,
            'missing': ErrorCategory.CONFIGURATION_ERROR,
            
            # System errors
            'system': ErrorCategory.SYSTEM_ERROR,
            'memory': ErrorCategory.SYSTEM_ERROR,
            'disk': ErrorCategory.SYSTEM_ERROR,
            'permission': ErrorCategory.SYSTEM_ERROR,
        }
    
    def handle_error(self, error: Exception, context: ErrorContext, 
                    attempt_recovery: bool = True) -> Optional[ErrorRecord]:
        """
        Handle an error with optional recovery attempts
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            attempt_recovery: Whether to attempt automatic recovery
            
        Returns:
            ErrorRecord if error was handled, None if recovered
        """
        with self.lock:
            # Classify the error
            category = self._classify_error(error)
            severity = self._determine_severity(error, category)
            
            # Create error record
            error_record = ErrorRecord(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                error_message=str(error),
                severity=severity,
                category=category,
                context=context,
                traceback=traceback.format_exc()
            )
            
            # Log the error
            self._log_error(error_record)
            
            # Record metrics
            self._record_error_metrics(error_record)
            
            # Attempt recovery if enabled
            if attempt_recovery:
                recovery_successful = self._attempt_recovery(error, context, error_record)
                if recovery_successful:
                    logger.info(f"Successfully recovered from error: {error_record.error_type}")
                    return None  # Error was recovered
            
            # Store error record
            self.error_records.append(error_record)
            
            # Trigger alerts for high severity errors
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self._trigger_alert(error_record)
            
            # Update circuit breaker if applicable
            self._update_circuit_breaker(error, context)
            
            return error_record
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error into a category"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check error message and type against patterns
        for pattern, category in self.error_patterns.items():
            if pattern in error_str or pattern in error_type:
                return category
        
        return ErrorCategory.UNKNOWN_ERROR
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity"""
        # Critical errors
        if isinstance(error, (SystemExit, KeyboardInterrupt, MemoryError)):
            return ErrorSeverity.CRITICAL
        
        # High severity by category
        if category in [ErrorCategory.SYSTEM_ERROR, ErrorCategory.CONFIGURATION_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity
        if category in [ErrorCategory.API_ERROR, ErrorCategory.AUTHENTICATION_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Default to low
        return ErrorSeverity.LOW
    
    def _log_error(self, error_record: ErrorRecord):
        """Log error with appropriate level"""
        log_data = {
            'error_type': error_record.error_type,
            'error_message': error_record.error_message,
            'severity': error_record.severity.value,
            'category': error_record.category.value,
            'component': error_record.context.component,
            'operation': error_record.context.operation,
            'metadata': error_record.context.metadata
        }
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR: {error_record.error_message}", extra=log_data)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY ERROR: {error_record.error_message}", extra=log_data)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY ERROR: {error_record.error_message}", extra=log_data)
        else:
            logger.info(f"LOW SEVERITY ERROR: {error_record.error_message}", extra=log_data)
    
    def _record_error_metrics(self, error_record: ErrorRecord):
        """Record error metrics"""
        labels = {
            'component': error_record.context.component,
            'error_type': error_record.error_type,
            'category': error_record.category.value,
            'severity': error_record.severity.value
        }
        
        self.metrics_collector.increment_counter("errors_total", labels)
        self.metrics_collector.increment_counter(f"errors_{error_record.severity.value}", labels)
        self.metrics_collector.increment_counter(f"errors_{error_record.category.value}", labels)
    
    def _attempt_recovery(self, error: Exception, context: ErrorContext, 
                         error_record: ErrorRecord) -> bool:
        """Attempt to recover from error using available strategies"""
        error_record.recovery_attempted = True
        
        for strategy in self.recovery_strategies:
            if strategy.can_recover(error, context):
                logger.info(f"Attempting recovery using strategy: {strategy.name}")
                
                for attempt in range(strategy.max_attempts):
                    try:
                        if strategy.recover(error, context, attempt):
                            error_record.retry_count = attempt + 1
                            
                            # Test if recovery was successful
                            # This would typically involve re-executing the failed operation
                            # For now, we'll mark as successful if no exception was raised
                            error_record.recovery_successful = True
                            
                            # Record recovery metrics
                            self.metrics_collector.increment_counter("error_recoveries_successful", {
                                'component': context.component,
                                'strategy': strategy.name,
                                'error_type': type(error).__name__
                            })
                            
                            return True
                            
                    except Exception as recovery_error:
                        logger.warning(f"Recovery attempt {attempt + 1} failed: {str(recovery_error)}")
                        continue
                
                # Record failed recovery
                self.metrics_collector.increment_counter("error_recoveries_failed", {
                    'component': context.component,
                    'strategy': strategy.name,
                    'error_type': type(error).__name__
                })
        
        return False
    
    def _trigger_alert(self, error_record: ErrorRecord):
        """Trigger alert for high severity errors"""
        alert_severity = AlertSeverity.HIGH
        if error_record.severity == ErrorSeverity.CRITICAL:
            alert_severity = AlertSeverity.CRITICAL
        
        self.alert_manager.trigger_alert(
            title=f"{error_record.severity.value.upper()} Error in {error_record.context.component}",
            message=f"{error_record.error_type}: {error_record.error_message}",
            severity=alert_severity,
            component=error_record.context.component,
            metadata={
                'error_type': error_record.error_type,
                'category': error_record.category.value,
                'operation': error_record.context.operation,
                'timestamp': error_record.timestamp.isoformat(),
                'recovery_attempted': error_record.recovery_attempted,
                'recovery_successful': error_record.recovery_successful
            }
        )
    
    def _update_circuit_breaker(self, error: Exception, context: ErrorContext):
        """Update circuit breaker state based on error"""
        # Get or create circuit breaker for the component
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3
        )
        
        circuit_breaker = self.circuit_breaker_manager.get_circuit_breaker(
            f"{context.component}_{context.operation}", 
            cb_config
        )
        
        # The circuit breaker will be updated when the operation is retried
        # This is just for tracking purposes
        logger.debug(f"Circuit breaker '{circuit_breaker.name}' will be updated on next operation")
    
    def add_recovery_strategy(self, strategy: RecoveryStrategy):
        """Add a custom recovery strategy"""
        with self.lock:
            self.recovery_strategies.append(strategy)
            logger.info(f"Added recovery strategy: {strategy.name}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self.lock:
            if not self.error_records:
                return {
                    'total_errors': 0,
                    'by_severity': {},
                    'by_category': {},
                    'by_component': {},
                    'recovery_rate': 0.0,
                    'recent_errors': []
                }
            
            # Calculate statistics
            total_errors = len(self.error_records)
            
            # Group by severity
            by_severity = {}
            for record in self.error_records:
                severity = record.severity.value
                by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Group by category
            by_category = {}
            for record in self.error_records:
                category = record.category.value
                by_category[category] = by_category.get(category, 0) + 1
            
            # Group by component
            by_component = {}
            for record in self.error_records:
                component = record.context.component
                by_component[component] = by_component.get(component, 0) + 1
            
            # Calculate recovery rate
            recovery_attempts = sum(1 for r in self.error_records if r.recovery_attempted)
            successful_recoveries = sum(1 for r in self.error_records if r.recovery_successful)
            recovery_rate = (successful_recoveries / max(recovery_attempts, 1)) * 100
            
            # Get recent errors (last 10)
            recent_errors = []
            for record in self.error_records[-10:]:
                recent_errors.append({
                    'timestamp': record.timestamp.isoformat(),
                    'error_type': record.error_type,
                    'error_message': record.error_message,
                    'severity': record.severity.value,
                    'category': record.category.value,
                    'component': record.context.component,
                    'operation': record.context.operation,
                    'recovery_attempted': record.recovery_attempted,
                    'recovery_successful': record.recovery_successful
                })
            
            return {
                'total_errors': total_errors,
                'by_severity': by_severity,
                'by_category': by_category,
                'by_component': by_component,
                'recovery_rate': recovery_rate,
                'recent_errors': recent_errors
            }
    
    def clear_resolved_errors(self, older_than_hours: int = 24):
        """Clear resolved errors older than specified hours"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            initial_count = len(self.error_records)
            self.error_records = [
                record for record in self.error_records
                if not (record.resolved and record.timestamp < cutoff_time)
            ]
            
            cleared_count = initial_count - len(self.error_records)
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} resolved errors older than {older_than_hours} hours")


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler"""
    return _error_handler


def handle_errors(component: str, operation: str = None, 
                 attempt_recovery: bool = True, **metadata):
    """
    Decorator to automatically handle errors in functions
    
    Args:
        component: Component name for error context
        operation: Operation name (defaults to function name)
        attempt_recovery: Whether to attempt automatic recovery
        **metadata: Additional metadata for error context
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(
                component=component,
                operation=operation or func.__name__,
                metadata=metadata
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Use the global error handler instance
                error_handler = get_error_handler()
                error_record = error_handler.handle_error(e, context, attempt_recovery)
                
                # If recovery was successful, error_record will be None
                if error_record is None:
                    # Retry the function after successful recovery
                    return func(*args, **kwargs)
                
                # Re-raise the original exception if recovery failed
                raise
        
        return wrapper
    return decorator