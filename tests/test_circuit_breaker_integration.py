# tests/test_circuit_breaker_integration.py
"""
Integration tests for circuit breaker patterns in external API calls
Tests circuit breaker behavior with real API integration patterns
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import requests
from datetime import datetime

from src.utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError,
    get_circuit_breaker_manager, circuit_breaker, CircuitState
)
from src.tools.news_retrieval_tool import PerplexityAPIClient, NewsRetrievalTool
from src.tools.bluesky_social_tool import BlueskySocialTool
from src.config.agent_config import AgentConfig


class TestPerplexityAPICircuitBreaker:
    """Test circuit breaker integration with Perplexity API"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = AgentConfig(
            perplexity_api_key="test_key",
            max_retries=2
        )
        get_circuit_breaker_manager().circuit_breakers.clear()
    
    @patch('src.tools.news_retrieval_tool.requests.Session.post')
    def test_perplexity_circuit_breaker_opens_on_failures(self, mock_post):
        """Test that circuit breaker opens after consecutive API failures"""
        # Mock consecutive failures
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response
        
        client = PerplexityAPIClient("test_key", max_retries=1)
        
        # Make multiple failing requests
        for i in range(3):
            with pytest.raises(Exception):
                client.search_news("test query")
        
        # Check circuit breaker state
        cb_manager = get_circuit_breaker_manager()
        perplexity_cb = cb_manager.get_circuit_breaker("perplexity_api")
        assert perplexity_cb.get_state() == CircuitState.OPEN
    
    @patch('src.tools.news_retrieval_tool.requests.Session.post')
    def test_perplexity_circuit_breaker_recovery(self, mock_post):
        """Test circuit breaker recovery after timeout"""
        # Configure circuit breaker with short timeout for testing
        cb_manager = get_circuit_breaker_manager()
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # Very short for testing
            success_threshold=1
        )
        perplexity_cb = cb_manager.get_circuit_breaker("perplexity_api", config)
        
        # Mock initial failures
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        # Mock successful response
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Test news content"}}],
            "citations": []
        }
        
        # First, cause failures to open circuit
        mock_post.return_value = mock_response_fail
        client = PerplexityAPIClient("test_key", max_retries=1)
        
        for i in range(2):
            with pytest.raises(Exception):
                client.search_news("test query")
        
        assert perplexity_cb.get_state() == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Mock successful response for recovery
        mock_post.return_value = mock_response_success
        
        # Should succeed and close circuit
        result = client.search_news("test query")
        assert result is not None
        assert perplexity_cb.get_state() == CircuitState.CLOSED
    
    @patch('src.tools.news_retrieval_tool.requests.Session.post')
    def test_perplexity_circuit_breaker_prevents_calls_when_open(self, mock_post):
        """Test that circuit breaker prevents API calls when open"""
        # Force circuit breaker to open state
        cb_manager = get_circuit_breaker_manager()
        perplexity_cb = cb_manager.get_circuit_breaker("perplexity_api")
        perplexity_cb.force_open()
        
        client = PerplexityAPIClient("test_key")
        
        # Should raise CircuitBreakerError without making HTTP request
        with pytest.raises(CircuitBreakerError):
            client.search_news("test query")
        
        # Verify no HTTP request was made
        mock_post.assert_not_called()


class TestBlueskySocialCircuitBreaker:
    """Test circuit breaker integration with Bluesky Social API"""
    
    def setup_method(self):
        """Setup test environment"""
        get_circuit_breaker_manager().circuit_breakers.clear()
    
    @patch('src.tools.bluesky_social_tool.Client')
    def test_bluesky_auth_circuit_breaker(self, mock_client_class):
        """Test circuit breaker for Bluesky authentication"""
        # Mock client to fail authentication
        mock_client = Mock()
        mock_client.login.side_effect = Exception("Authentication failed")
        mock_client_class.return_value = mock_client
        
        tool = BlueskySocialTool(max_retries=1)
        
        # Make multiple failing authentication attempts
        for i in range(3):
            with pytest.raises(Exception):
                tool._authenticate("test_user", "test_pass")
        
        # Check circuit breaker state
        cb_manager = get_circuit_breaker_manager()
        auth_cb = cb_manager.get_circuit_breaker("bluesky_auth")
        assert auth_cb.get_state() == CircuitState.OPEN
    
    @patch('src.tools.bluesky_social_tool.Client')
    def test_bluesky_post_circuit_breaker(self, mock_client_class):
        """Test circuit breaker for Bluesky posting"""
        # Mock client with failing post method
        mock_client = Mock()
        mock_client.send_post.side_effect = Exception("Posting failed")
        mock_client_class.return_value = mock_client
        
        tool = BlueskySocialTool(max_retries=1)
        tool.client = mock_client  # Set authenticated client
        
        # Make multiple failing post attempts
        for i in range(3):
            with pytest.raises(Exception):
                tool._create_post("test content")
        
        # Check circuit breaker state
        cb_manager = get_circuit_breaker_manager()
        post_cb = cb_manager.get_circuit_breaker("bluesky_post")
        assert post_cb.get_state() == CircuitState.OPEN
    
    @patch('src.tools.bluesky_social_tool.Client')
    def test_bluesky_circuit_breaker_recovery(self, mock_client_class):
        """Test circuit breaker recovery for Bluesky posting"""
        # Configure circuit breaker with short timeout
        cb_manager = get_circuit_breaker_manager()
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=1
        )
        post_cb = cb_manager.get_circuit_breaker("bluesky_post", config)
        
        # Mock client that fails initially then succeeds
        mock_client = Mock()
        
        # First, cause failures
        mock_client.send_post.side_effect = Exception("Posting failed")
        mock_client_class.return_value = mock_client
        
        tool = BlueskySocialTool(max_retries=1)
        tool.client = mock_client
        
        for i in range(2):
            with pytest.raises(Exception):
                tool._create_post("test content")
        
        assert post_cb.get_state() == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Mock successful posting
        mock_post_result = Mock()
        mock_post_result.uri = "test_uri"
        mock_post_result.cid = "test_cid"
        mock_client.send_post.side_effect = None
        mock_client.send_post.return_value = mock_post_result
        
        # Should succeed and close circuit
        result = tool._create_post("test content")
        assert result['uri'] == "test_uri"
        assert post_cb.get_state() == CircuitState.CLOSED


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics and monitoring"""
    
    def setup_method(self):
        """Setup test environment"""
        get_circuit_breaker_manager().circuit_breakers.clear()
    
    def test_circuit_breaker_statistics_tracking(self):
        """Test that circuit breaker tracks statistics correctly"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test_stats", config)
        
        # Make some successful calls
        for i in range(5):
            result = cb.call(lambda: "success")
            assert result == "success"
        
        # Make some failing calls
        for i in range(2):
            with pytest.raises(Exception):
                cb.call(lambda: self._failing_function())
        
        # Check statistics
        stats = cb.get_stats()
        assert stats['total_requests'] == 7
        assert stats['successful_requests'] == 5
        assert stats['failed_requests'] == 2
        assert stats['success_rate'] == (5/7) * 100
        assert stats['current_consecutive_failures'] == 2
        assert stats['current_consecutive_successes'] == 0
    
    def test_circuit_breaker_manager_statistics(self):
        """Test circuit breaker manager statistics aggregation"""
        manager = get_circuit_breaker_manager()
        
        # Create multiple circuit breakers
        cb1 = manager.get_circuit_breaker("service1")
        cb2 = manager.get_circuit_breaker("service2")
        
        # Make some calls
        cb1.call(lambda: "success")
        with pytest.raises(Exception):
            cb2.call(lambda: self._failing_function())
        
        # Get all statistics
        all_stats = manager.get_all_stats()
        assert "service1" in all_stats
        assert "service2" in all_stats
        assert all_stats["service1"]["successful_requests"] == 1
        assert all_stats["service2"]["failed_requests"] == 1
    
    def test_unhealthy_circuit_detection(self):
        """Test detection of unhealthy circuits"""
        manager = get_circuit_breaker_manager()
        
        # Create healthy circuit
        healthy_cb = manager.get_circuit_breaker("healthy_service")
        for i in range(10):
            healthy_cb.call(lambda: "success")
        
        # Create unhealthy circuit
        unhealthy_cb = manager.get_circuit_breaker("unhealthy_service")
        unhealthy_cb.force_open()  # Force to open state
        
        # Get unhealthy circuits
        unhealthy = manager.get_unhealthy_circuits()
        assert "unhealthy_service" in unhealthy
        assert "healthy_service" not in unhealthy
    
    def _failing_function(self):
        """Helper function that always fails"""
        raise Exception("Simulated failure")


class TestCircuitBreakerWithRealAPIPatterns:
    """Test circuit breaker with realistic API failure patterns"""
    
    def setup_method(self):
        """Setup test environment"""
        get_circuit_breaker_manager().circuit_breakers.clear()
    
    def test_rate_limiting_scenario(self):
        """Test circuit breaker with rate limiting (429) responses"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            failure_status_codes=(429, 500, 502, 503, 504)
        )
        
        @circuit_breaker("rate_limited_api", config)
        def api_call():
            # Simulate rate limiting response
            response = Mock()
            response.status_code = 429
            error = requests.exceptions.HTTPError("429 Too Many Requests")
            error.response = response
            raise error
        
        # Make calls that hit rate limit
        for i in range(3):
            with pytest.raises(requests.exceptions.HTTPError):
                api_call()
        
        # Circuit should be open now
        with pytest.raises(CircuitBreakerError):
            api_call()
    
    def test_intermittent_failure_scenario(self):
        """Test circuit breaker with intermittent failures"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1,
            success_threshold=2
        )
        
        call_count = 0
        
        @circuit_breaker("intermittent_api", config)
        def intermittent_api_call():
            nonlocal call_count
            call_count += 1
            # Fail every 3rd call
            if call_count % 3 == 0:
                raise Exception("Intermittent failure")
            return f"success_{call_count}"
        
        # Make calls with intermittent failures
        results = []
        exceptions = []
        
        for i in range(10):
            try:
                result = intermittent_api_call()
                results.append(result)
            except (Exception, CircuitBreakerError) as e:
                exceptions.append(e)
        
        # Should have some successes and some failures
        assert len(results) > 0
        assert len(exceptions) > 0
    
    def test_timeout_scenario(self):
        """Test circuit breaker with timeout scenarios"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout=0.1  # Very short timeout for testing
        )
        
        @circuit_breaker("timeout_api", config)
        def slow_api_call():
            time.sleep(0.2)  # Longer than timeout
            return "success"
        
        # Make calls that timeout
        for i in range(2):
            with pytest.raises(Exception):
                slow_api_call()
        
        # Circuit should be open
        with pytest.raises(CircuitBreakerError):
            slow_api_call()
    
    def test_cascading_failure_prevention(self):
        """Test that circuit breaker prevents cascading failures"""
        # Create dependent services
        service_a_cb = get_circuit_breaker_manager().get_circuit_breaker("service_a")
        service_b_cb = get_circuit_breaker_manager().get_circuit_breaker("service_b")
        
        @circuit_breaker("service_a")
        def service_a_call():
            raise Exception("Service A is down")
        
        @circuit_breaker("service_b")
        def service_b_call():
            # Service B depends on Service A
            service_a_call()
            return "Service B success"
        
        # Make calls that fail due to Service A
        for i in range(3):
            with pytest.raises(Exception):
                service_b_call()
        
        # Both circuits should be open
        assert service_a_cb.get_state() == CircuitState.OPEN
        assert service_b_cb.get_state() == CircuitState.OPEN
        
        # Further calls should be blocked by circuit breakers
        with pytest.raises(CircuitBreakerError):
            service_b_call()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])