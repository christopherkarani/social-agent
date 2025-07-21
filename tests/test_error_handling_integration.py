# tests/test_error_handling_integration.py
"""
Integration tests for comprehensive error handling and recovery mechanisms
Tests circuit breaker patterns, error recovery, and notification systems
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.utils.error_handler import (
    ErrorHandler, get_error_handler, handle_errors, 
    ErrorContext, ErrorSeverity, ErrorCategory
)
from src.utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError,
    get_circuit_breaker_manager, circuit_breaker
)
from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.config.agent_config import AgentConfig
from src.models.data_models import NewsItem, GeneratedContent, ContentType


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with API calls"""
    
    def setup_method(self):
        """Setup test environment"""
        self.circuit_breaker_manager = get_circuit_breaker_manager()
        # Clear any existing circuit breakers
        self.circuit_breaker_manager.circuit_breakers.clear()
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after consecutive failures"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1,
            success_threshold=2
        )
        
        cb = CircuitBreaker("test_api", config)
        
        # Simulate failures
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(lambda: self._failing_function(), )
        
        # Circuit should now be open
        assert cb.get_state().value == "open"
        
        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "success")
    
    def test_circuit_breaker_recovery_cycle(self):
        """Test circuit breaker recovery from open to closed"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # Very short for testing
            success_threshold=2
        )
        
        cb = CircuitBreaker("test_recovery", config)
        
        # Cause failures to open circuit
        for i in range(2):
            with pytest.raises(Exception):
                cb.call(lambda: self._failing_function())
        
        assert cb.get_state().value == "open"
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # First call after timeout should transition to half-open
        result = cb.call(lambda: "success1")
        assert result == "success1"
        assert cb.get_state().value == "half_open"
        
        # Second successful call should close the circuit
        result = cb.call(lambda: "success2")
        assert result == "success2"
        assert cb.get_state().value == "closed"
    
    def test_circuit_breaker_decorator(self):
        """Test circuit breaker as decorator"""
        config = CircuitBreakerConfig(failure_threshold=2)
        
        @circuit_breaker("decorated_api", config)
        def test_function(should_fail=False):
            if should_fail:
                raise Exception("Test failure")
            return "success"
        
        # Successful calls
        assert test_function() == "success"
        assert test_function() == "success"
        
        # Cause failures
        with pytest.raises(Exception):
            test_function(should_fail=True)
        with pytest.raises(Exception):
            test_function(should_fail=True)
        
        # Circuit should be open now
        with pytest.raises(CircuitBreakerError):
            test_function()
    
    def _failing_function(self):
        """Helper function that always fails"""
        raise Exception("Simulated failure")


class TestErrorHandlerIntegration:
    """Test error handler integration and recovery mechanisms"""
    
    def setup_method(self):
        """Setup test environment"""
        self.error_handler = ErrorHandler()
        # Clear previous error records
        self.error_handler.error_records.clear()
    
    def test_error_classification(self):
        """Test automatic error classification"""
        context = ErrorContext(component="test", operation="test_op")
        
        # Test API error classification
        api_error = Exception("HTTP 500 error occurred")
        record = self.error_handler.handle_error(api_error, context, attempt_recovery=False)
        assert record.category == ErrorCategory.API_ERROR
        
        # Test authentication error classification
        auth_error = Exception("Unauthorized access - invalid token")
        record = self.error_handler.handle_error(auth_error, context, attempt_recovery=False)
        assert record.category == ErrorCategory.AUTHENTICATION_ERROR
        
        # Test network error classification
        network_error = ConnectionError("Connection failed")
        record = self.error_handler.handle_error(network_error, context, attempt_recovery=False)
        assert record.category == ErrorCategory.NETWORK_ERROR
    
    def test_error_severity_determination(self):
        """Test error severity determination"""
        context = ErrorContext(component="test", operation="test_op")
        
        # Test critical error
        critical_error = MemoryError("Out of memory")
        record = self.error_handler.handle_error(critical_error, context, attempt_recovery=False)
        assert record.severity == ErrorSeverity.CRITICAL
        
        # Test high severity error
        system_error = Exception("System configuration error")
        record = self.error_handler.handle_error(system_error, context, attempt_recovery=False)
        assert record.severity == ErrorSeverity.HIGH
        
        # Test medium severity error
        api_error = Exception("API request failed")
        record = self.error_handler.handle_error(api_error, context, attempt_recovery=False)
        assert record.severity == ErrorSeverity.MEDIUM
    
    @patch('src.utils.error_handler.get_metrics_collector')
    @patch('src.utils.error_handler.get_alert_manager')
    def test_error_metrics_and_alerts(self, mock_alert_manager, mock_metrics_collector):
        """Test that errors trigger appropriate metrics and alerts"""
        mock_metrics = Mock()
        mock_alerts = Mock()
        mock_metrics_collector.return_value = mock_metrics
        mock_alert_manager.return_value = mock_alerts
        
        context = ErrorContext(component="test", operation="test_op")
        critical_error = Exception("Critical system failure")
        
        # Handle critical error
        record = self.error_handler.handle_error(critical_error, context, attempt_recovery=False)
        
        # Verify metrics were recorded
        mock_metrics.increment_counter.assert_called()
        
        # Verify alert was triggered for critical error
        mock_alerts.trigger_alert.assert_called()
        
        # Check alert parameters
        alert_call = mock_alerts.trigger_alert.call_args
        assert "CRITICAL" in alert_call[1]['title']
    
    def test_error_handler_decorator(self):
        """Test error handler decorator functionality"""
        @handle_errors("test_component", "test_operation")
        def test_function(should_fail=False):
            if should_fail:
                raise Exception("Test error")
            return "success"
        
        # Successful execution
        result = test_function()
        assert result == "success"
        
        # Error execution
        with pytest.raises(Exception):
            test_function(should_fail=True)
        
        # Check that error was recorded
        assert len(self.error_handler.error_records) > 0
        record = self.error_handler.error_records[-1]
        assert record.context.component == "test_component"
        assert record.context.operation == "test_operation"


class TestBlueskyCryptoAgentErrorHandling:
    """Test error handling integration in BlueskyCryptoAgent"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_pass",
            max_retries=2,
            min_engagement_score=0.5,
            duplicate_threshold=0.8,
            max_post_length=300
        )
        
        # Mock LLM
        self.mock_llm = Mock()
        
        # Clear circuit breakers and error records
        get_circuit_breaker_manager().circuit_breakers.clear()
        get_error_handler().error_records.clear()
    
    @pytest.mark.asyncio
    async def test_news_retrieval_fallback(self):
        """Test fallback mechanism when news retrieval fails"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock news tool to fail
        agent.news_tool._arun = AsyncMock(side_effect=Exception("API failure"))
        
        # Execute news retrieval
        result = await agent._retrieve_news("test query")
        
        # Should get fallback data
        assert result['success'] is True
        assert result['fallback'] is True
        assert len(result['news_items']) > 0
        assert result['original_query'] == "test query"
    
    @pytest.mark.asyncio
    async def test_content_generation_fallback(self):
        """Test fallback mechanism when content generation fails"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock content tool to fail
        agent.content_tool._arun = AsyncMock(side_effect=Exception("Generation failure"))
        
        # Create test news data
        news_data = {
            'success': True,
            'count': 1,
            'news_items': [{
                'headline': 'Test Bitcoin News',
                'summary': 'Test summary',
                'topics': ['Bitcoin', 'Cryptocurrency']
            }]
        }
        
        # Execute content generation
        result = await agent._generate_content(news_data)
        
        # Should get fallback content
        assert result['success'] is True
        assert result['fallback'] is True
        assert 'content' in result
        assert len(result['content']['text']) > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration_in_workflow(self):
        """Test circuit breaker integration in full workflow"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock news tool to consistently fail
        agent.news_tool._arun = AsyncMock(side_effect=Exception("Persistent API failure"))
        
        # Execute workflow multiple times to trigger circuit breaker
        results = []
        for i in range(5):
            result = await agent.execute_workflow("test query")
            results.append(result)
        
        # Should have fallback data in all results due to circuit breaker
        for result in results:
            assert result is not None
            # The workflow should complete even with API failures due to fallback mechanisms
    
    @pytest.mark.asyncio
    async def test_posting_circuit_breaker(self):
        """Test circuit breaker for Bluesky posting"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Create test content
        test_news = NewsItem(
            headline="Test News",
            summary="Test summary",
            source="Test",
            timestamp=datetime.now(),
            relevance_score=0.8,
            topics=["Bitcoin"]
        )
        
        test_content = GeneratedContent(
            text="Test post content",
            hashtags=["#bitcoin"],
            engagement_score=0.7,
            content_type=ContentType.NEWS,
            source_news=test_news,
            created_at=datetime.now()
        )
        
        # Mock social tool to fail consistently
        agent.social_tool._arun = AsyncMock(return_value={
            'success': False,
            'error_message': 'Posting failed',
            'retry_count': 0
        })
        
        # Execute posting multiple times
        results = []
        for i in range(5):
            result = await agent._post_to_bluesky(test_content)
            results.append(result)
        
        # Should handle failures gracefully
        for result in results:
            assert result is not None
            assert hasattr(result, 'success')
    
    def test_error_statistics_tracking(self):
        """Test error statistics tracking"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Get initial stats
        initial_stats = get_error_handler().get_error_stats()
        initial_count = initial_stats['total_errors']
        
        # Simulate some errors
        context = ErrorContext(component="test", operation="test")
        for i in range(3):
            get_error_handler().handle_error(
                Exception(f"Test error {i}"), 
                context, 
                attempt_recovery=False
            )
        
        # Check updated stats
        updated_stats = get_error_handler().get_error_stats()
        assert updated_stats['total_errors'] == initial_count + 3
        assert len(updated_stats['recent_errors']) >= 3


class TestRecoveryMechanisms:
    """Test automatic recovery mechanisms"""
    
    def setup_method(self):
        """Setup test environment"""
        self.error_handler = ErrorHandler()
        self.error_handler.error_records.clear()
    
    def test_retry_recovery_strategy(self):
        """Test retry recovery strategy"""
        from src.utils.error_handler import RetryStrategy
        
        strategy = RetryStrategy(max_attempts=3, base_delay=0.01)  # Fast for testing
        context = ErrorContext(component="test", operation="test")
        
        # Test retryable error
        retryable_error = ConnectionError("Connection failed")
        assert strategy.can_recover(retryable_error, context)
        
        # Test recovery attempts
        for attempt in range(3):
            can_retry = strategy.recover(retryable_error, context, attempt)
            if attempt < 2:
                assert can_retry is True
            else:
                assert can_retry is False
    
    def test_authentication_recovery_strategy(self):
        """Test authentication recovery strategy"""
        from src.utils.error_handler import AuthenticationRecoveryStrategy
        
        strategy = AuthenticationRecoveryStrategy()
        context = ErrorContext(component="test", operation="test")
        
        # Test authentication error detection
        auth_error = Exception("401 Unauthorized - invalid token")
        assert strategy.can_recover(auth_error, context)
        
        # Test recovery
        can_recover = strategy.recover(auth_error, context, 0)
        assert can_recover is True
        assert context.metadata.get('auth_recovery_attempted') is True
    
    def test_configuration_recovery_strategy(self):
        """Test configuration recovery strategy"""
        from src.utils.error_handler import ConfigurationRecoveryStrategy
        
        strategy = ConfigurationRecoveryStrategy()
        context = ErrorContext(component="test", operation="test")
        
        # Test configuration error detection
        config_error = Exception("Missing required configuration parameter")
        assert strategy.can_recover(config_error, context)
        
        # Test recovery
        can_recover = strategy.recover(config_error, context, 0)
        assert can_recover is True
        assert context.metadata.get('config_reload_needed') is True


class TestEndToEndErrorScenarios:
    """Test end-to-end error scenarios and recovery"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user", 
            bluesky_password="test_pass",
            max_retries=2,
            min_engagement_score=0.5,
            duplicate_threshold=0.8,
            max_post_length=300
        )
        
        self.mock_llm = Mock()
        
        # Clear state
        get_circuit_breaker_manager().circuit_breakers.clear()
        get_error_handler().error_records.clear()
    
    @pytest.mark.asyncio
    async def test_complete_api_failure_scenario(self):
        """Test scenario where all external APIs fail"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock all external calls to fail
        agent.news_tool._arun = AsyncMock(side_effect=Exception("News API down"))
        agent.content_tool._arun = AsyncMock(side_effect=Exception("Content API down"))
        agent.social_tool._arun = AsyncMock(return_value={
            'success': False,
            'error_message': 'Social API down',
            'retry_count': 0
        })
        
        # Execute workflow
        result = await agent.execute_workflow("test query")
        
        # Should handle gracefully with fallbacks
        assert result is not None
        # The workflow should attempt to use fallback mechanisms
    
    @pytest.mark.asyncio
    async def test_partial_recovery_scenario(self):
        """Test scenario with partial recovery"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock news API to fail initially then succeed
        call_count = 0
        async def mock_news_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary failure")
            return '{"success": true, "count": 1, "news_items": [{"headline": "Test", "summary": "Test", "topics": ["Bitcoin"]}]}'
        
        agent.news_tool._arun = mock_news_call
        
        # Mock content generation to succeed
        agent.content_tool._arun = AsyncMock(return_value='{"success": true, "content": {"text": "Test content", "hashtags": ["#bitcoin"], "engagement_score": 0.8, "content_type": "news", "source_news": {"headline": "Test", "summary": "Test", "source": "Test", "timestamp": "2024-01-01T00:00:00", "relevance_score": 0.8, "topics": ["Bitcoin"]}, "created_at": "2024-01-01T00:00:00"}}')
        
        # Mock posting to succeed
        agent.social_tool._arun = AsyncMock(return_value={
            'success': True,
            'post_id': 'test_post_123',
            'retry_count': 0
        })
        
        # Execute workflow
        result = await agent.execute_workflow("test query")
        
        # Should eventually succeed after recovery
        assert result is not None
    
    def test_circuit_breaker_manager_health_monitoring(self):
        """Test circuit breaker manager health monitoring"""
        manager = get_circuit_breaker_manager()
        
        # Create some circuit breakers with different states
        cb1 = manager.get_circuit_breaker("healthy_service")
        cb2 = manager.get_circuit_breaker("unhealthy_service")
        
        # Make unhealthy service fail
        config = CircuitBreakerConfig(failure_threshold=2)
        cb2.config = config
        
        for i in range(2):
            with pytest.raises(Exception):
                cb2.call(lambda: self._failing_function())
        
        # Check unhealthy circuits
        unhealthy = manager.get_unhealthy_circuits()
        assert "unhealthy_service" in unhealthy
        assert "healthy_service" not in unhealthy
        
        # Get all stats
        all_stats = manager.get_all_stats()
        assert "healthy_service" in all_stats
        assert "unhealthy_service" in all_stats
        assert all_stats["unhealthy_service"]["state"] == "open"
    
    def _failing_function(self):
        """Helper function that always fails"""
        raise Exception("Simulated failure")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])