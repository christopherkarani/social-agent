# tests/test_basic_error_handling.py
"""
Basic tests to verify error handling and circuit breaker functionality
"""
import pytest
import time
from unittest.mock import Mock

from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError
from src.utils.error_handler import ErrorHandler, ErrorContext, get_error_handler


def test_circuit_breaker_basic_functionality():
    """Test basic circuit breaker functionality"""
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
    cb = CircuitBreaker("test", config)
    
    # Test successful calls
    result = cb.call(lambda: "success")
    assert result == "success"
    
    # Test failure tracking
    try:
        cb.call(lambda: exec('raise Exception("test error")'))
    except Exception:
        pass
    
    try:
        cb.call(lambda: exec('raise Exception("test error")'))
    except Exception:
        pass
    
    # After 2 failures, circuit should open
    stats = cb.get_stats()
    assert stats['failed_requests'] == 2


def test_error_handler_basic_functionality():
    """Test basic error handler functionality"""
    error_handler = ErrorHandler()
    context = ErrorContext(component="test", operation="test_op")
    
    # Test error handling
    test_error = Exception("Test error")
    record = error_handler.handle_error(test_error, context, attempt_recovery=False)
    
    assert record is not None
    assert record.error_message == "Test error"
    assert record.context.component == "test"
    
    # Test statistics
    stats = error_handler.get_error_stats()
    assert stats['total_errors'] >= 1


def test_fallback_mechanisms():
    """Test that fallback mechanisms work"""
    from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
    from src.config.agent_config import AgentConfig
    
    config = AgentConfig(
        perplexity_api_key="test",
        bluesky_username="test",
        bluesky_password="test"
    )
    
    mock_llm = Mock()
    agent = BlueskyCryptoAgent(mock_llm, config)
    
    # Test fallback news data
    fallback_data = agent._get_fallback_news_data("test query")
    assert fallback_data['success'] is True
    assert fallback_data['fallback'] is True
    assert len(fallback_data['news_items']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])