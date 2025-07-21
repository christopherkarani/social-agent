# Comprehensive Error Handling and Recovery System

This document describes the comprehensive error handling and recovery mechanisms implemented in the Bluesky Crypto Agent system.

## Overview

The system implements multiple layers of error handling and recovery:

1. **Circuit Breaker Pattern** - Prevents cascading failures by temporarily blocking calls to failing services
2. **Enhanced Error Reporting** - Centralized error classification, tracking, and notification
3. **Automatic Recovery Mechanisms** - Multiple strategies for recovering from different types of errors
4. **Fallback Systems** - Graceful degradation when primary systems fail

## Circuit Breaker Pattern

### Implementation

The circuit breaker pattern is implemented in `src/utils/circuit_breaker.py` and provides:

- **Three States**: Closed (normal), Open (failing), Half-Open (testing recovery)
- **Configurable Thresholds**: Failure count, recovery timeout, success count for closing
- **Automatic State Management**: Transitions between states based on success/failure patterns
- **Statistics Tracking**: Comprehensive metrics for monitoring and debugging

### Usage

```python
from src.utils.circuit_breaker import circuit_breaker, CircuitBreakerConfig

# As a decorator
@circuit_breaker("api_service")
def api_call():
    # Your API call here
    pass

# With custom configuration
config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=3
)

@circuit_breaker("custom_service", config)
def custom_api_call():
    # Your API call here
    pass
```

### Integration Points

Circuit breakers are integrated at key external service interaction points:

- **Perplexity API** (`perplexity_api`) - News retrieval service
- **Bluesky Authentication** (`bluesky_auth`) - Authentication with Bluesky
- **Bluesky Posting** (`bluesky_post`) - Content posting to Bluesky

## Enhanced Error Reporting

### Error Classification

Errors are automatically classified into categories:

- `API_ERROR` - External API failures
- `AUTHENTICATION_ERROR` - Authentication and authorization issues
- `NETWORK_ERROR` - Network connectivity problems
- `TIMEOUT_ERROR` - Request timeout issues
- `VALIDATION_ERROR` - Data validation failures
- `CONFIGURATION_ERROR` - Configuration and setup issues
- `SYSTEM_ERROR` - System-level errors
- `UNKNOWN_ERROR` - Unclassified errors

### Severity Levels

Errors are assigned severity levels:

- `CRITICAL` - System-threatening errors (MemoryError, SystemExit)
- `HIGH` - Service-impacting errors (System, Configuration)
- `MEDIUM` - Feature-impacting errors (API, Authentication)
- `LOW` - Minor errors with minimal impact

### Usage

```python
from src.utils.error_handler import handle_errors, ErrorContext

# As a decorator
@handle_errors("component_name", "operation_name")
def risky_operation():
    # Your code here
    pass

# Manual error handling
from src.utils.error_handler import get_error_handler

error_handler = get_error_handler()
context = ErrorContext(component="my_component", operation="my_operation")
error_record = error_handler.handle_error(exception, context, attempt_recovery=True)
```

## Automatic Recovery Mechanisms

### Recovery Strategies

The system implements multiple recovery strategies:

#### 1. Retry Strategy
- **Purpose**: Retry operations that may succeed on subsequent attempts
- **Configuration**: Exponential backoff with configurable delays
- **Applicable To**: Network errors, temporary API failures, timeouts

#### 2. Authentication Recovery Strategy
- **Purpose**: Clear authentication state and force re-authentication
- **Configuration**: Limited retry attempts to prevent account lockout
- **Applicable To**: 401/403 errors, token expiration, credential issues

#### 3. Configuration Recovery Strategy
- **Purpose**: Reload configuration and retry operations
- **Configuration**: Single attempt to prevent infinite loops
- **Applicable To**: Missing configuration, invalid parameters

### Custom Recovery Strategies

You can implement custom recovery strategies:

```python
from src.utils.error_handler import RecoveryStrategy

class CustomRecoveryStrategy(RecoveryStrategy):
    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        # Determine if this strategy can handle the error
        return "custom_error" in str(error).lower()
    
    def recover(self, error: Exception, context: ErrorContext, attempt: int) -> bool:
        # Implement recovery logic
        # Return True if recovery should be attempted, False if exhausted
        return attempt < self.max_attempts

# Add to error handler
get_error_handler().add_recovery_strategy(CustomRecoveryStrategy("custom_recovery"))
```

## Fallback Systems

### News Retrieval Fallback

When the Perplexity API fails, the system provides fallback news data:

```python
def _get_fallback_news_data(self, query: str) -> Dict[str, Any]:
    # Returns generic cryptocurrency news items
    # Ensures the workflow can continue even with API failures
```

### Content Generation Fallback

When content generation fails, the system creates fallback content:

```python
def _get_fallback_content_data(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
    # Creates simple, safe content based on available news data
    # Ensures posts can still be generated during failures
```

### Posting Fallback

When Bluesky posting fails, the system:
- Records the failure with detailed error information
- Attempts recovery through authentication refresh
- Provides detailed error reporting for manual intervention

## Monitoring and Alerting

### Metrics Collection

The system automatically collects metrics for:
- Error counts by type, severity, and component
- Circuit breaker state changes and statistics
- Recovery attempt success/failure rates
- System health indicators

### Alert Triggers

Alerts are automatically triggered for:
- **Critical Errors**: Immediate notification for system-threatening issues
- **High Severity Errors**: Rapid notification for service-impacting problems
- **Circuit Breaker Opens**: Notification when services become unavailable
- **Recovery Failures**: Notification when automatic recovery fails

### Health Monitoring

The system provides health monitoring through:

```python
# Circuit breaker health
from src.utils.circuit_breaker import get_circuit_breaker_manager
manager = get_circuit_breaker_manager()
unhealthy_circuits = manager.get_unhealthy_circuits()
all_stats = manager.get_all_stats()

# Error statistics
from src.utils.error_handler import get_error_handler
error_handler = get_error_handler()
error_stats = error_handler.get_error_stats()
```

## Integration with Main Workflow

The error handling system is fully integrated into the main workflow:

### News Retrieval
- Circuit breaker protection for Perplexity API
- Automatic fallback to generic news data
- Error classification and recovery attempts

### Content Generation
- Validation of generated content
- Fallback content creation on failures
- Quality threshold enforcement

### Content Posting
- Circuit breaker protection for Bluesky API
- Authentication recovery mechanisms
- Detailed error reporting and retry logic

## Configuration

### Circuit Breaker Configuration

```python
from src.utils.circuit_breaker import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,        # Failures before opening
    recovery_timeout=60,        # Seconds before attempting recovery
    success_threshold=3,        # Successes needed to close
    timeout=30,                 # Request timeout
    failure_status_codes=(429, 500, 502, 503, 504)
)
```

### Error Handler Configuration

The error handler uses sensible defaults but can be customized:

```python
from src.utils.error_handler import ErrorHandler, RetryStrategy

error_handler = ErrorHandler()

# Add custom retry strategy
custom_retry = RetryStrategy(
    name="custom_retry",
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0
)
error_handler.add_recovery_strategy(custom_retry)
```

## Testing

Comprehensive tests are provided in:
- `tests/test_error_handling_integration.py` - Integration tests for error scenarios
- `tests/test_circuit_breaker_integration.py` - Circuit breaker pattern tests
- `tests/test_basic_error_handling.py` - Basic functionality tests

### Running Tests

```bash
# Run all error handling tests
python -m pytest tests/test_*error* -v

# Run specific test categories
python -m pytest tests/test_circuit_breaker_integration.py -v
python -m pytest tests/test_error_handling_integration.py -v
```

## Best Practices

### 1. Use Circuit Breakers for External Services
Always wrap external service calls with circuit breakers to prevent cascading failures.

### 2. Implement Fallback Mechanisms
Provide fallback data or alternative workflows when primary systems fail.

### 3. Monitor Error Patterns
Regularly review error statistics to identify systemic issues.

### 4. Test Error Scenarios
Include error scenarios in your testing to ensure graceful degradation.

### 5. Configure Appropriate Thresholds
Set circuit breaker and retry thresholds based on your service requirements.

## Troubleshooting

### Circuit Breaker Stuck Open
- Check service health and connectivity
- Review error logs for root cause
- Manually reset circuit breaker if needed: `circuit_breaker.reset()`

### High Error Rates
- Review error statistics: `get_error_handler().get_error_stats()`
- Check for configuration issues
- Verify external service availability

### Recovery Failures
- Review recovery strategy configuration
- Check for authentication or permission issues
- Verify network connectivity and service endpoints

## Future Enhancements

Potential improvements to the error handling system:

1. **Machine Learning-Based Recovery** - Use ML to predict optimal recovery strategies
2. **Distributed Circuit Breakers** - Share circuit breaker state across multiple instances
3. **Advanced Metrics** - More sophisticated health scoring and prediction
4. **Custom Alert Channels** - Integration with external monitoring systems
5. **Automated Remediation** - Self-healing capabilities for common issues

## Conclusion

The comprehensive error handling and recovery system provides robust protection against failures while maintaining system availability. The combination of circuit breakers, automatic recovery, and fallback mechanisms ensures that the Bluesky Crypto Agent can continue operating even when individual components fail.

Regular monitoring of the error handling metrics and periodic review of error patterns will help maintain system reliability and identify areas for improvement.