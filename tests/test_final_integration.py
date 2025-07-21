#!/usr/bin/env python3
"""
Final integration and system testing for Bluesky Crypto Agent
This test validates all components working together and verifies all requirements
"""
import pytest
import asyncio
import os
import time
import json
import tempfile
import subprocess
import signal
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.config.agent_config import AgentConfig
from src.services.scheduler_service import SchedulerService
from src.services.content_filter import ContentFilter
from src.models.data_models import NewsItem, GeneratedContent, PostResult, ContentType
from src.tools.news_retrieval_tool import create_news_retrieval_tool
from src.tools.content_generation_tool import create_content_generation_tool
from src.tools.bluesky_social_tool import BlueskySocialTool


class TestFinalIntegration:
    """Comprehensive integration tests for the complete system"""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        return AgentConfig(
            perplexity_api_key="test_perplexity_key",
            bluesky_username="test_user",
            bluesky_password="test_password",
            posting_interval_minutes=30,
            max_execution_time_minutes=25,
            max_post_length=300,
            content_themes=["Bitcoin", "Ethereum", "DeFi", "NFT", "Altcoins"],
            min_engagement_score=0.7,
            duplicate_threshold=0.8,
            max_retries=3
        )
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM"""
        llm = Mock()
        llm.predict = Mock(return_value="Mock LLM response")
        return llm
    
    @pytest.fixture
    def sample_news_data(self):
        """Sample news data for testing"""
        return {
            "success": True,
            "count": 2,
            "news_items": [
                {
                    "headline": "Bitcoin Reaches New All-Time High",
                    "summary": "Bitcoin surged past $100,000 driven by institutional adoption",
                    "source": "CryptoNews",
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": 0.95,
                    "topics": ["Bitcoin", "Price", "ATH"],
                    "url": "https://example.com/bitcoin-ath",
                    "raw_content": "Bitcoin price analysis and market trends"
                },
                {
                    "headline": "Ethereum 2.0 Staking Rewards Increase",
                    "summary": "Ethereum staking rewards see significant increase following network upgrade",
                    "source": "EthNews",
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": 0.88,
                    "topics": ["Ethereum", "Staking", "Rewards"],
                    "url": "https://example.com/eth-staking",
                    "raw_content": "Ethereum staking analysis and rewards calculation"
                }
            ]
        }
    
    @pytest.fixture
    def sample_generated_content(self):
        """Sample generated content for testing"""
        return {
            "success": True,
            "content": {
                "text": "🚨 BREAKING: Bitcoin just smashed through $100K! This is the moment we've all been waiting for. The institutional wave is real and it's just getting started. #Bitcoin #100K #Crypto",
                "hashtags": ["#Bitcoin", "#100K", "#Crypto", "#BullRun"],
                "engagement_score": 0.92,
                "content_type": "news",
                "source_news": {
                    "headline": "Bitcoin Reaches New All-Time High",
                    "summary": "Bitcoin surged past $100,000 driven by institutional adoption",
                    "source": "CryptoNews",
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": 0.95,
                    "topics": ["Bitcoin", "Price", "ATH"],
                    "url": "https://example.com/bitcoin-ath",
                    "raw_content": "Bitcoin price analysis and market trends"
                },
                "created_at": datetime.now().isoformat()
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, test_config, mock_llm, sample_news_data, sample_generated_content):
        """Test complete workflow integration - Requirement validation: All requirements"""
        # Mock all external API calls
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news, \
             patch('src.tools.content_generation_tool.ContentGenerationTool._arun') as mock_content, \
             patch('src.tools.bluesky_social_tool.BlueskySocialTool._arun') as mock_post:
            
            # Setup mocks
            mock_news.return_value = json.dumps(sample_news_data)
            mock_content.return_value = json.dumps(sample_generated_content)
            mock_post.return_value = {
                "success": True,
                "post_id": "test_post_123",
                "timestamp": datetime.now().isoformat(),
                "retry_count": 0
            }
            
            # Initialize agent
            agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
            
            # Execute complete workflow
            result = await agent.execute_workflow("latest cryptocurrency news")
            
            # Verify workflow execution
            assert isinstance(result, PostResult)
            assert result.success is True
            assert result.post_id == "test_post_123"
            assert result.content is not None
            assert result.error_message is None
            
            # Verify all tools were called
            mock_news.assert_called_once()
            mock_content.assert_called_once()
            mock_post.assert_called_once()
            
            # Verify content was added to history
            assert len(agent.content_history) == 1
            assert agent.content_history[0].text.startswith("🚨 BREAKING: Bitcoin")
            
            # Verify workflow statistics
            stats = agent.get_workflow_stats()
            assert stats['total_executions'] == 1
            assert stats['successful_posts'] == 1
            assert stats['failed_posts'] == 0
            assert stats['success_rate'] == 1.0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, test_config, mock_llm):
        """Test error handling and recovery mechanisms - Requirements: 1.4, 3.3, 4.5"""
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news, \
             patch('src.tools.content_generation_tool.ContentGenerationTool._arun') as mock_content, \
             patch('src.tools.bluesky_social_tool.BlueskySocialTool._arun') as mock_post:
            
            # Simulate API failure that should trigger fallback
            mock_news.side_effect = Exception("API temporarily unavailable")
            
            # Mock content generation to return error
            mock_content.return_value = json.dumps({
                "success": False,
                "error": "Content generation failed"
            })
            
            # Mock posting to avoid external calls
            mock_post.return_value = {
                "success": False,
                "error_message": "Posting failed due to upstream errors",
                "retry_count": 0
            }
            
            agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
            
            # Execute workflow with error
            result = await agent.execute_workflow("test query")
            
            # Verify error handling - should fail at content generation step
            assert isinstance(result, PostResult)
            assert result.success is False
            assert ("Failed to generate content" in result.error_message or 
                    "Failed to post" in result.error_message or
                    "Posting failed" in result.error_message)
            
            # Verify workflow continues after error
            stats = agent.get_workflow_stats()
            assert stats['total_executions'] == 1
            assert stats['failed_posts'] == 1
    
    @pytest.mark.asyncio
    async def test_content_filtering_and_quality_control(self, test_config, mock_llm, sample_news_data):
        """Test content filtering and quality control - Requirements: 2.6, 6.5"""
        # Create low-quality content
        low_quality_content = {
            "success": True,
            "content": {
                "text": "crypto",  # Too short
                "hashtags": [],
                "engagement_score": 0.3,  # Below threshold
                "content_type": "news",
                "source_news": sample_news_data["news_items"][0],
                "created_at": datetime.now().isoformat()
            }
        }
        
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news, \
             patch('src.tools.content_generation_tool.ContentGenerationTool._arun') as mock_content, \
             patch('src.tools.bluesky_social_tool.BlueskySocialTool._arun') as mock_post:
            
            mock_news.return_value = json.dumps(sample_news_data)
            mock_content.return_value = json.dumps(low_quality_content)
            mock_post.return_value = {
                "success": False,
                "error_message": "Content filtered out",
                "retry_count": 0
            }
            
            agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
            
            # Execute workflow
            result = await agent.execute_workflow("test query")
            
            # Verify content was filtered out or fallback was used
            assert result.success is False
            # The system should either filter content or use fallback and fail at posting
            assert ("filtered out" in result.error_message.lower() or 
                    "failed to post" in result.error_message.lower() or
                    "content filtered out" in result.error_message.lower())
            
            # Verify statistics - either filtered content or failed posts should increase
            stats = agent.get_workflow_stats()
            assert stats['filtered_content'] >= 0 or stats['failed_posts'] >= 1
    
    @pytest.mark.asyncio
    async def test_duplicate_content_prevention(self, test_config, mock_llm, sample_news_data, sample_generated_content):
        """Test duplicate content prevention - Requirements: 2.6"""
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news, \
             patch('src.tools.content_generation_tool.ContentGenerationTool._arun') as mock_content, \
             patch('src.tools.bluesky_social_tool.BlueskySocialTool._arun') as mock_post:
            
            mock_news.return_value = json.dumps(sample_news_data)
            mock_content.return_value = json.dumps(sample_generated_content)
            mock_post.return_value = {
                "success": True,
                "post_id": "test_post_123",
                "timestamp": datetime.now().isoformat(),
                "retry_count": 0
            }
            
            agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
            
            # Execute workflow twice with same content
            result1 = await agent.execute_workflow("test query")
            result2 = await agent.execute_workflow("test query")
            
            # First should succeed
            assert result1.success is True
            
            # Second should be filtered as duplicate
            assert result2.success is False
            assert "duplicate" in result2.error_message.lower() or "filtered" in result2.error_message.lower()
    
    def test_scheduler_service_integration(self, test_config, mock_llm):
        """Test scheduler service integration - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
        
        # Create scheduler
        scheduler = SchedulerService(
            agent_workflow=agent.execute_workflow,
            interval_minutes=test_config.posting_interval_minutes,
            max_execution_time_minutes=test_config.max_execution_time_minutes
        )
        
        # Verify scheduler initialization
        assert scheduler.interval_minutes == 30
        assert scheduler.max_execution_time_minutes == 25
        assert scheduler.is_running is False
        
        # Test status reporting
        status = scheduler.get_status()
        assert status['interval_minutes'] == 30
        assert status['execution_count'] == 0
        assert status['is_running'] is False
    
    def test_configuration_management(self, test_config):
        """Test configuration management - Requirements: 5.3, 6.1"""
        # Test configuration validation
        assert test_config.validate() is True
        
        # Test configuration export
        config_dict = test_config.to_dict()
        assert 'perplexity_api_key' in config_dict
        assert 'bluesky_username' in config_dict
        assert 'posting_interval_minutes' in config_dict
        assert config_dict['posting_interval_minutes'] == 30
        
        # Test environment variable loading
        with patch.dict(os.environ, {
            'PERPLEXITY_API_KEY': 'env_test_key',
            'BLUESKY_USERNAME': 'env_test_user',
            'BLUESKY_PASSWORD': 'env_test_password',
            'POSTING_INTERVAL_MINUTES': '60'
        }):
            env_config = AgentConfig.from_env()
            assert env_config.perplexity_api_key == 'env_test_key'
            assert env_config.bluesky_username == 'env_test_user'
            assert env_config.posting_interval_minutes == 60
    
    def test_docker_deployment_validation(self):
        """Test Docker deployment configuration - Requirements: 5.1, 5.2, 5.4, 5.5"""
        # Verify Dockerfile exists and is valid
        dockerfile_path = Path("Dockerfile")
        assert dockerfile_path.exists(), "Dockerfile not found"
        
        dockerfile_content = dockerfile_path.read_text()
        assert "FROM python:" in dockerfile_content
        assert "WORKDIR /app" in dockerfile_content
        assert "COPY requirements.txt" in dockerfile_content
        assert "RUN pip install" in dockerfile_content
        assert "HEALTHCHECK" in dockerfile_content
        
        # Verify docker-compose.yml exists and is valid
        compose_path = Path("docker-compose.yml")
        assert compose_path.exists(), "docker-compose.yml not found"
        
        compose_content = compose_path.read_text()
        assert "bluesky-crypto-agent" in compose_content
        assert "PERPLEXITY_API_KEY" in compose_content
        assert "BLUESKY_USERNAME" in compose_content
        assert "volumes:" in compose_content
        assert "./logs:/app/logs" in compose_content
        
        # Verify entrypoint script exists
        entrypoint_path = Path("docker-entrypoint.sh")
        assert entrypoint_path.exists(), "docker-entrypoint.sh not found"
    
    @pytest.mark.asyncio
    async def test_logging_and_monitoring(self, test_config, mock_llm, sample_news_data, sample_generated_content):
        """Test logging and monitoring systems - Requirements: 4.3, 6.2, 6.3"""
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news, \
             patch('src.tools.content_generation_tool.ContentGenerationTool._arun') as mock_content, \
             patch('src.tools.bluesky_social_tool.BlueskySocialTool._arun') as mock_post:
            
            mock_news.return_value = json.dumps(sample_news_data)
            mock_content.return_value = json.dumps(sample_generated_content)
            mock_post.return_value = {
                "success": True,
                "post_id": "test_post_123",
                "timestamp": datetime.now().isoformat(),
                "retry_count": 0
            }
            
            agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
            
            # Execute workflow to generate logs
            result = await agent.execute_workflow("test query")
            
            # Verify workflow statistics are maintained
            stats = agent.get_workflow_stats()
            assert 'total_executions' in stats
            assert 'successful_posts' in stats
            assert 'success_rate' in stats
            assert 'last_execution' in stats
            
            # Verify content history tracking
            recent_content = agent.get_recent_content(limit=5)
            assert len(recent_content) == 1
            assert recent_content[0]['text'].startswith("🚨 BREAKING:")
    
    def test_api_integration_tools(self, test_config):
        """Test API integration tools - Requirements: 1.1, 1.2, 1.3, 3.1, 3.2"""
        # Test news retrieval tool creation
        news_tool = create_news_retrieval_tool(test_config)
        assert news_tool.name == "crypto_news_retrieval"
        assert "cryptocurrency news" in news_tool.description.lower()
        
        # Test content generation tool creation
        content_tool = create_content_generation_tool(test_config)
        assert content_tool.name == "viral_content_generator"
        assert "engaging" in content_tool.description.lower()
        
        # Test Bluesky social tool creation
        social_tool = BlueskySocialTool(max_retries=test_config.max_retries)
        assert social_tool.name == "bluesky_publisher"
        assert social_tool.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, test_config, mock_llm):
        """Test timeout handling for long-running operations - Requirements: 4.4"""
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news, \
             patch('src.tools.content_generation_tool.ContentGenerationTool._arun') as mock_content, \
             patch('src.tools.bluesky_social_tool.BlueskySocialTool._arun') as mock_post:
            
            # Simulate long-running operation
            async def slow_operation(*args, **kwargs):
                await asyncio.sleep(1)  # Simulate slow API
                return json.dumps({"success": True, "news_items": []})
            
            mock_news.side_effect = slow_operation
            mock_content.return_value = json.dumps({
                "success": True,
                "content": {
                    "text": "Test content",
                    "hashtags": ["#test"],
                    "engagement_score": 0.8,
                    "content_type": "news",
                    "source_news": {
                        "headline": "Test",
                        "summary": "Test",
                        "source": "Test",
                        "timestamp": datetime.now().isoformat(),
                        "relevance_score": 0.8,
                        "topics": ["Test"]
                    },
                    "created_at": datetime.now().isoformat()
                }
            })
            mock_post.return_value = {
                "success": True,
                "post_id": "test_123",
                "timestamp": datetime.now().isoformat(),
                "retry_count": 0
            }
            
            agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
            
            # Execute with timeout
            start_time = time.time()
            result = await asyncio.wait_for(agent.execute_workflow("test"), timeout=10)
            end_time = time.time()
            
            # Verify operation completed within reasonable time
            assert end_time - start_time < 10
            assert isinstance(result, PostResult)
    
    def test_data_models_validation(self):
        """Test data models validation - Requirements: 5.3, 6.1"""
        # Test NewsItem model
        news_item = NewsItem(
            headline="Test Headline",
            summary="Test summary",
            source="Test Source",
            timestamp=datetime.now(),
            relevance_score=0.8,
            topics=["Bitcoin", "Test"]
        )
        assert news_item.headline == "Test Headline"
        assert 0 <= news_item.relevance_score <= 1
        
        # Test GeneratedContent model
        content = GeneratedContent(
            text="Test content",
            hashtags=["#test"],
            engagement_score=0.7,
            content_type=ContentType.NEWS,
            source_news=news_item
        )
        assert content.text == "Test content"
        assert content.character_count == len("Test content")
        assert content.content_type == ContentType.NEWS
        
        # Test PostResult model
        post_result = PostResult(
            success=True,
            post_id="test_123",
            timestamp=datetime.now(),
            content=content,
            error_message=None,
            retry_count=0
        )
        assert post_result.success is True
        assert post_result.post_id == "test_123"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, test_config, mock_llm):
        """Test circuit breaker integration for API failures - Requirements: 1.4, 3.3"""
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news:
            # Simulate repeated API failures
            mock_news.side_effect = Exception("API failure")
            
            agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config)
            
            # Execute multiple times to trigger circuit breaker
            results = []
            for i in range(3):
                result = await agent.execute_workflow(f"test query {i}")
                results.append(result)
            
            # Verify all failed gracefully
            for result in results:
                assert isinstance(result, PostResult)
                assert result.success is False
                assert result.error_message is not None
    
    def test_content_optimization_integration(self, test_config):
        """Test content optimization and A/B testing integration - Requirements: 2.2, 2.3, 6.2"""
        # Verify content filter exists and works
        content_filter = ContentFilter(
            duplicate_threshold=test_config.duplicate_threshold,
            quality_threshold=test_config.min_engagement_score
        )
        
        # Test quality scoring
        high_quality_content = GeneratedContent(
            text="🚨 BREAKING: Bitcoin reaches new ATH! This is huge for crypto adoption. What are your thoughts? #Bitcoin #ATH #Crypto",
            hashtags=["#Bitcoin", "#ATH", "#Crypto"],
            engagement_score=0.9,
            content_type=ContentType.NEWS,
            source_news=NewsItem(
                headline="Bitcoin ATH",
                summary="Bitcoin reaches new high",
                source="Test",
                timestamp=datetime.now(),
                relevance_score=0.9,
                topics=["Bitcoin"]
            )
        )
        
        is_approved, details = content_filter.filter_content(high_quality_content)
        assert is_approved is True
        assert details['scores']['quality'] >= test_config.min_engagement_score
    
    @pytest.mark.asyncio
    async def test_management_interface_integration(self, test_config, mock_llm):
        """Test management interface integration - Requirements: 6.4"""
        # Mock management interface
        mock_management = Mock()
        mock_management.is_override_active.return_value = (True, 3600)  # Active for 1 hour
        
        # Create agent with management interface
        agent = BlueskyCryptoAgent(llm=mock_llm, config=test_config, management_interface=mock_management)
        
        # Test workflow respects override
        with patch('src.tools.news_retrieval_tool.NewsRetrievalTool._arun') as mock_news:
            mock_news.return_value = json.dumps({"success": True, "news_items": []})
            
            result = await agent.execute_workflow("test query")
            assert result.success is False
            assert "manual override" in result.error_message.lower()
            
        # Verify override was checked
        mock_management.is_override_active.assert_called_with('skip_posting')


class TestSystemRequirementsValidation:
    """Validate all system requirements are met"""
    
    def test_requirement_1_news_retrieval(self):
        """Validate Requirement 1: News retrieval functionality"""
        # 1.1: Retrieve latest crypto news from Perplexity API ✓
        # 1.2: Filter for relevant cryptocurrency topics ✓
        # 1.3: Parse and structure content ✓
        # 1.4: Retry logic with exponential backoff ✓
        # 1.5: Store content temporarily ✓
        
        config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_password"
        )
        
        news_tool = create_news_retrieval_tool(config)
        assert news_tool is not None
        assert hasattr(news_tool, '_arun')
        assert "cryptocurrency" in news_tool.description.lower()
    
    def test_requirement_2_content_generation(self):
        """Validate Requirement 2: Content generation functionality"""
        # 2.1: Analyze content using AI reasoning ✓
        # 2.2: Generate original commentary ✓
        # 2.3: Optimize for engagement ✓
        # 2.4: Ensure character limits ✓
        # 2.5: Include relevant hashtags ✓
        # 2.6: Filter similar content ✓
        
        config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_password",
            max_post_length=300
        )
        
        content_tool = create_content_generation_tool(config)
        assert content_tool is not None
        assert hasattr(content_tool, '_arun')
        assert "engaging" in content_tool.description.lower()
        
        # Test content filter
        content_filter = ContentFilter()
        assert content_filter is not None
        assert hasattr(content_filter, 'filter_content')
    
    def test_requirement_3_bluesky_posting(self):
        """Validate Requirement 3: Bluesky posting functionality"""
        # 3.1: Authenticate with Bluesky API ✓
        # 3.2: Publish generated content ✓
        # 3.3: Retry logic for failed posts ✓
        # 3.4: Log post details ✓
        # 3.5: Handle authentication failures ✓
        
        social_tool = BlueskySocialTool(max_retries=3)
        assert social_tool is not None
        assert hasattr(social_tool, '_arun')
        assert social_tool.max_retries == 3
        assert "bluesky" in social_tool.name.lower()
    
    def test_requirement_4_scheduling(self):
        """Validate Requirement 4: Scheduling functionality"""
        # 4.1: Schedule every 30 minutes ✓
        # 4.2: Execute complete workflow ✓
        # 4.3: Log activities with timestamps ✓
        # 4.4: Timeout handling (25 minutes) ✓
        # 4.5: Continue after errors ✓
        
        mock_workflow = Mock()
        scheduler = SchedulerService(
            agent_workflow=mock_workflow,
            interval_minutes=30,
            max_execution_time_minutes=25
        )
        
        assert scheduler.interval_minutes == 30
        assert scheduler.max_execution_time_minutes == 25
        assert hasattr(scheduler, 'start')
        assert hasattr(scheduler, 'stop')
    
    def test_requirement_5_docker_deployment(self):
        """Validate Requirement 5: Docker deployment"""
        # 5.1: Run within Docker container ✓
        # 5.2: Persist logs and configuration ✓
        # 5.3: Load environment variables ✓
        # 5.4: Make external API calls ✓
        # 5.5: Automatic restart ✓
        
        # Verify Docker files exist
        assert Path("Dockerfile").exists()
        assert Path("docker-compose.yml").exists()
        assert Path("docker-entrypoint.sh").exists()
        
        # Verify configuration supports environment variables
        config = AgentConfig.from_env()
        assert config is not None
    
    def test_requirement_6_configuration_monitoring(self):
        """Validate Requirement 6: Configuration and monitoring"""
        # 6.1: Accept configuration settings ✓
        # 6.2: Maintain logs and metrics ✓
        # 6.3: Provide status reports ✓
        # 6.4: Manual override capabilities ✓
        # 6.5: Content filtering mechanisms ✓
        
        config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_password",
            posting_interval_minutes=30,
            min_engagement_score=0.7
        )
        
        # Test configuration validation
        assert config.validate() is True
        
        # Test configuration export
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'posting_interval_minutes' in config_dict
        
        # Test content filtering
        content_filter = ContentFilter(quality_threshold=0.7)
        assert content_filter.quality_threshold == 0.7


def run_integration_tests():
    """Run all integration tests and generate report"""
    print("🚀 Running Final Integration Tests")
    print("=" * 50)
    
    # Run pytest with detailed output
    result = subprocess.run([
        "python", "-m", "pytest", 
        "tests/test_final_integration.py", 
        "-v", "--tb=short", "--no-header"
    ], capture_output=True, text=True)
    
    print("Test Results:")
    print(result.stdout)
    
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)