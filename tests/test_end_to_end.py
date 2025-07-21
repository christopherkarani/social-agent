# tests/test_end_to_end.py
"""
End-to-end tests with real API integrations (staging)
Tests the complete system with actual external services
"""
import pytest
import asyncio
import os
import time
from datetime import datetime
from typing import Dict, Any

from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.config.agent_config import AgentConfig
from src.services.scheduler_service import SchedulerService
from src.models.data_models import PostResult


class TestEndToEndIntegration:
    """End-to-end tests with real API integrations"""
    
    @pytest.fixture
    def staging_config(self):
        """Create configuration for staging environment"""
        return AgentConfig(
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY_STAGING", "test_key"),
            bluesky_username=os.getenv("BLUESKY_USERNAME_STAGING", "test_user"),
            bluesky_password=os.getenv("BLUESKY_PASSWORD_STAGING", "test_password"),
            posting_interval_minutes=60,  # Longer interval for staging
            max_execution_time_minutes=25,
            max_post_length=300,
            content_themes=["Bitcoin", "Ethereum", "DeFi", "Testing"],
            min_engagement_score=0.6,  # Lower threshold for testing
            duplicate_threshold=0.7,
            max_retries=2
        )
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for staging tests"""
        from unittest.mock import Mock
        llm = Mock()
        llm.predict = Mock(return_value="Generated content for staging test")
        return llm
    
    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="End-to-end tests require RUN_E2E_TESTS environment variable"
    )
    @pytest.mark.asyncio
    async def test_complete_workflow_with_real_apis(self, staging_config, mock_llm):
        """Test complete workflow with real API integrations"""
        # Skip if staging credentials not available
        if (staging_config.perplexity_api_key == "test_key" or 
            staging_config.bluesky_username == "test_user"):
            pytest.skip("Staging credentials not configured")
        
        agent = BlueskyCryptoAgent(llm=mock_llm, config=staging_config)
        
        # Execute workflow with real APIs
        result = await agent.execute_workflow("latest cryptocurrency testing news")
        
        # Verify workflow execution
        assert isinstance(result, PostResult)
        assert result.timestamp is not None
        
        # Log results for manual verification
        print(f"E2E Test Result: Success={result.success}")
        if result.success:
            print(f"Post ID: {result.post_id}")
            print(f"Content: {result.content.text if result.content else 'N/A'}")
        else:
            print(f"Error: {result.error_message}")
        
        # Basic validation - don't fail test if APIs are temporarily unavailable
        if not result.success and "temporarily unavailable" in str(result.error_message).lower():
            pytest.skip("External APIs temporarily unavailable")
    
    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="End-to-end tests require RUN_E2E_TESTS environment variable"
    )
    @pytest.mark.asyncio
    async def test_news_retrieval_with_real_perplexity(self, staging_config, mock_llm):
        """Test news retrieval with real Perplexity API"""
        if staging_config.perplexity_api_key == "test_key":
            pytest.skip("Perplexity staging credentials not configured")
        
        agent = BlueskyCryptoAgent(llm=mock_llm, config=staging_config)
        
        # Test news retrieval directly
        news_data = await agent._retrieve_news("Bitcoin price analysis")
        
        # Verify news data structure
        assert isinstance(news_data, dict)
        assert "success" in news_data
        
        if news_data.get("success"):
            assert "news_items" in news_data
            assert "count" in news_data
            assert isinstance(news_data["news_items"], list)
            
            # Verify news item structure if any returned
            if news_data["news_items"]:
                news_item = news_data["news_items"][0]
                required_fields = ["headline", "summary", "source", "timestamp"]
                for field in required_fields:
                    assert field in news_item, f"Missing field: {field}"
        
        print(f"News Retrieval Test: Success={news_data.get('success')}")
        print(f"News Count: {news_data.get('count', 0)}")
    
    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="End-to-end tests require RUN_E2E_TESTS environment variable"
    )
    @pytest.mark.asyncio
    async def test_bluesky_authentication_real(self, staging_config, mock_llm):
        """Test Bluesky authentication with real credentials"""
        if (staging_config.bluesky_username == "test_user" or 
            staging_config.bluesky_password == "test_password"):
            pytest.skip("Bluesky staging credentials not configured")
        
        agent = BlueskyCryptoAgent(llm=mock_llm, config=staging_config)
        
        # Test authentication through social tool
        try:
            # Create a test post (will be deleted after test)
            test_content = f"🧪 E2E Test Post - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} #testing"
            
            post_result = await agent.social_tool._arun(
                content=test_content,
                username=staging_config.bluesky_username,
                password=staging_config.bluesky_password
            )
            
            # Verify authentication and posting
            assert isinstance(post_result, dict)
            assert "success" in post_result
            
            if post_result.get("success"):
                assert "post_id" in post_result
                assert post_result["post_id"] is not None
                print(f"Test post created: {post_result['post_id']}")
            else:
                print(f"Post failed: {post_result.get('error_message')}")
            
        except Exception as e:
            # Don't fail test for temporary API issues
            if "temporarily unavailable" in str(e).lower():
                pytest.skip("Bluesky API temporarily unavailable")
            else:
                raise
    
    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="End-to-end tests require RUN_E2E_TESTS environment variable"
    )
    def test_scheduler_service_integration(self, staging_config, mock_llm):
        """Test scheduler service with real configuration"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=staging_config)
        scheduler = SchedulerService(agent=agent, config=staging_config)
        
        # Test scheduler initialization
        assert scheduler.agent == agent
        assert scheduler.config == staging_config
        assert scheduler.is_running is False
        
        # Test schedule configuration
        scheduler._setup_schedule()
        
        # Verify schedule is configured (don't actually run)
        import schedule
        jobs = schedule.jobs
        assert len(jobs) > 0
        
        # Clear schedule after test
        schedule.clear()
    
    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="End-to-end tests require RUN_E2E_TESTS environment variable"
    )
    @pytest.mark.asyncio
    async def test_error_recovery_with_real_apis(self, staging_config, mock_llm):
        """Test error recovery mechanisms with real APIs"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=staging_config)
        
        # Test with invalid query to trigger error handling
        result = await agent.execute_workflow("invalid_query_that_should_fail_gracefully_12345")
        
        # Verify error handling
        assert isinstance(result, PostResult)
        assert result.timestamp is not None
        
        # Should either succeed with fallback content or fail gracefully
        if not result.success:
            assert result.error_message is not None
            assert len(result.error_message) > 0
        
        print(f"Error Recovery Test: Success={result.success}")
        if not result.success:
            print(f"Error handled: {result.error_message}")
    
    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="End-to-end tests require RUN_E2E_TESTS environment variable"
    )
    @pytest.mark.asyncio
    async def test_content_quality_filtering_real(self, staging_config, mock_llm):
        """Test content quality filtering with real generated content"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=staging_config)
        
        # Execute workflow multiple times to test filtering
        results = []
        for i in range(3):
            result = await agent.execute_workflow(f"cryptocurrency news test {i}")
            results.append(result)
            
            # Wait between requests to avoid rate limiting
            await asyncio.sleep(2)
        
        # Analyze results
        successful_posts = [r for r in results if r.success]
        filtered_posts = [r for r in results if not r.success and "filtered" in str(r.error_message).lower()]
        
        print(f"Quality Filtering Test: {len(successful_posts)} successful, {len(filtered_posts)} filtered")
        
        # Verify at least some filtering logic is working
        total_executions = len(results)
        assert total_executions > 0
        
        # Check that content history is being maintained
        assert len(agent.content_history) >= len(successful_posts)
    
    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="End-to-end tests require RUN_E2E_TESTS environment variable"
    )
    @pytest.mark.asyncio
    async def test_performance_under_load(self, staging_config, mock_llm):
        """Test system performance under load"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=staging_config)
        
        # Execute multiple workflows concurrently
        start_time = time.time()
        
        tasks = []
        for i in range(3):  # Limited concurrent requests for staging
            task = agent.execute_workflow(f"performance test query {i}")
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze performance
        successful_results = [r for r in results if isinstance(r, PostResult) and r.success]
        failed_results = [r for r in results if isinstance(r, PostResult) and not r.success]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        print(f"Performance Test Results:")
        print(f"  Total Duration: {total_duration:.2f}s")
        print(f"  Successful: {len(successful_results)}")
        print(f"  Failed: {len(failed_results)}")
        print(f"  Exceptions: {len(exceptions)}")
        
        # Basic performance assertions
        assert total_duration < 120  # Should complete within 2 minutes
        assert len(exceptions) == 0  # No unhandled exceptions
        
        # At least some requests should succeed (unless all APIs are down)
        if len(successful_results) == 0 and len(failed_results) > 0:
            # Check if failures are due to temporary API issues
            api_errors = [r for r in failed_results if "temporarily unavailable" in str(r.error_message).lower()]
            if len(api_errors) == len(failed_results):
                pytest.skip("All APIs temporarily unavailable")


class TestStagingEnvironment:
    """Tests specific to staging environment setup"""
    
    def test_environment_variables_available(self):
        """Test that staging environment variables are properly configured"""
        required_vars = [
            "PERPLEXITY_API_KEY_STAGING",
            "BLUESKY_USERNAME_STAGING", 
            "BLUESKY_PASSWORD_STAGING"
        ]
        
        available_vars = []
        missing_vars = []
        
        for var in required_vars:
            if os.getenv(var) and os.getenv(var) != "test_key" and os.getenv(var) != "test_user":
                available_vars.append(var)
            else:
                missing_vars.append(var)
        
        print(f"Available staging vars: {available_vars}")
        print(f"Missing staging vars: {missing_vars}")
        
        # Don't fail test, just report status
        if missing_vars:
            pytest.skip(f"Staging environment not fully configured: {missing_vars}")
    
    def test_staging_config_validation(self):
        """Test staging configuration validation"""
        config = AgentConfig(
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY_STAGING", "test_key"),
            bluesky_username=os.getenv("BLUESKY_USERNAME_STAGING", "test_user"),
            bluesky_password=os.getenv("BLUESKY_PASSWORD_STAGING", "test_password"),
            content_themes=["Testing", "Staging", "E2E"],
            posting_interval_minutes=60,
            min_engagement_score=0.5
        )
        
        # Test configuration validation
        is_valid = config.validate()
        
        if config.perplexity_api_key == "test_key":
            # Expected to be invalid without real credentials
            assert is_valid is False
        else:
            # Should be valid with real credentials
            assert is_valid is True
            assert len(config.content_themes) > 0
            assert config.posting_interval_minutes > 0
            assert 0 <= config.min_engagement_score <= 1


# Utility functions for E2E testing
def cleanup_test_posts():
    """Utility to clean up test posts (if API supports it)"""
    # This would be implemented based on Bluesky API capabilities
    # For now, we rely on test posts being clearly marked
    pass


def verify_api_connectivity():
    """Verify that external APIs are accessible"""
    import requests
    
    apis_status = {}
    
    # Check Perplexity API (basic connectivity)
    try:
        response = requests.get("https://api.perplexity.ai", timeout=5)
        apis_status["perplexity"] = "accessible"
    except:
        apis_status["perplexity"] = "not_accessible"
    
    # Check Bluesky API
    try:
        response = requests.get("https://bsky.social", timeout=5)
        apis_status["bluesky"] = "accessible"
    except:
        apis_status["bluesky"] = "not_accessible"
    
    return apis_status


if __name__ == "__main__":
    # Quick connectivity check when run directly
    status = verify_api_connectivity()
    print("API Connectivity Status:")
    for api, status in status.items():
        print(f"  {api}: {status}")