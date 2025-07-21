# tests/test_bluesky_crypto_agent.py
"""
Unit tests for BlueskyCryptoAgent class
"""
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.models.data_models import NewsItem, GeneratedContent, PostResult, ContentType
from src.config.agent_config import AgentConfig


class TestBlueskyCryptoAgent(unittest.TestCase):
    """Test cases for BlueskyCryptoAgent"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock LLM
        self.mock_llm = Mock()
        
        # Create test configuration
        self.config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_pass",
            min_engagement_score=0.7,
            duplicate_threshold=0.8,
            max_retries=2,
            max_post_length=300
        )
        
        # Create test news item
        self.test_news = NewsItem(
            headline="Bitcoin Reaches New High",
            summary="Bitcoin price surged to new all-time high amid institutional adoption",
            source="CoinDesk",
            timestamp=datetime.now(),
            relevance_score=0.9,
            topics=["Bitcoin", "Price"],
            url="https://example.com/news"
        )
        
        # Create test generated content
        self.test_content = GeneratedContent(
            text="🚨 BREAKING: Bitcoin hits new ATH! Institutional adoption driving the surge",
            hashtags=["#Bitcoin", "#BTC", "#Crypto"],
            engagement_score=0.85,
            content_type=ContentType.NEWS,
            source_news=self.test_news,
            metadata={"test": True}
        )
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_initialization(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test agent initialization"""
        # Create agent
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Verify initialization
        self.assertEqual(agent.config, self.config)
        self.assertEqual(agent.llm, self.mock_llm)
        self.assertIsInstance(agent.content_history, list)
        self.assertEqual(len(agent.content_history), 0)
        
        # Verify tools were created
        mock_news_tool.assert_called_once_with(self.config)
        mock_content_tool.assert_called_once_with(self.config)
        mock_social_tool.assert_called_once_with(max_retries=self.config.max_retries)
        
        # Verify workflow stats initialization
        expected_stats = {
            'total_executions': 0,
            'successful_posts': 0,
            'failed_posts': 0,
            'filtered_content': 0,
            'last_execution': None,
            'last_success': None
        }
        self.assertEqual(agent.workflow_stats, expected_stats)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_initialization_tool_failure(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test agent initialization with tool creation failure"""
        # Make news tool creation fail
        mock_news_tool.side_effect = Exception("API key invalid")
        
        # Verify exception is raised
        with self.assertRaises(Exception) as context:
            BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # The original exception is re-raised, so check for the original message
        self.assertIn("API key invalid", str(context.exception))
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    async def test_execute_workflow_success(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test successful workflow execution"""
        # Setup mocks
        mock_news_instance = Mock()
        mock_news_instance._arun = AsyncMock(return_value=json.dumps({
            "success": True,
            "news_items": [self.test_news.to_dict()]
        }))
        mock_news_tool.return_value = mock_news_instance
        
        mock_content_instance = Mock()
        mock_content_instance._arun = AsyncMock(return_value=json.dumps({
            "success": True,
            "content": self.test_content.to_dict()
        }))
        mock_content_tool.return_value = mock_content_instance
        
        mock_social_instance = Mock()
        mock_social_instance._arun = AsyncMock(return_value={
            "success": True,
            "post_id": "test_post_123",
            "retry_count": 0
        })
        mock_social_tool.return_value = mock_social_instance
        
        # Create agent and execute workflow
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock content filter to approve content
        agent.content_filter.filter_content = Mock(return_value=(True, {"reasons": ["Approved"]}))
        
        result = await agent.execute_workflow("Bitcoin news")
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.post_id, "test_post_123")
        self.assertIsNotNone(result.content)
        
        # Verify workflow stats updated
        self.assertEqual(agent.workflow_stats['total_executions'], 1)
        self.assertEqual(agent.workflow_stats['successful_posts'], 1)
        self.assertEqual(agent.workflow_stats['failed_posts'], 0)
        
        # Verify content added to history
        self.assertEqual(len(agent.content_history), 1)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    async def test_execute_workflow_news_failure(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test workflow execution with news retrieval failure"""
        # Setup mock to fail news retrieval
        mock_news_instance = Mock()
        mock_news_instance._arun = AsyncMock(return_value=json.dumps({
            "success": False,
            "error": "API rate limit exceeded"
        }))
        mock_news_tool.return_value = mock_news_instance
        
        # Create agent and execute workflow
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        result = await agent.execute_workflow("Bitcoin news")
        
        # Verify failure result
        self.assertFalse(result.success)
        self.assertIn("Failed to retrieve news data", result.error_message)
        
        # Verify workflow stats updated
        self.assertEqual(agent.workflow_stats['total_executions'], 1)
        self.assertEqual(agent.workflow_stats['successful_posts'], 0)
        self.assertEqual(agent.workflow_stats['failed_posts'], 1)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    async def test_execute_workflow_content_filtered(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test workflow execution with content filtering rejection"""
        # Setup successful news and content generation
        mock_news_instance = Mock()
        mock_news_instance._arun = AsyncMock(return_value=json.dumps({
            "success": True,
            "news_items": [self.test_news.to_dict()]
        }))
        mock_news_tool.return_value = mock_news_instance
        
        mock_content_instance = Mock()
        mock_content_instance._arun = AsyncMock(return_value=json.dumps({
            "success": True,
            "content": self.test_content.to_dict()
        }))
        mock_content_tool.return_value = mock_content_instance
        
        # Create agent
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock content filter to reject content
        agent.content_filter.filter_content = Mock(return_value=(False, {
            "reasons": ["Quality score too low: 0.5 < 0.7"]
        }))
        
        result = await agent.execute_workflow("Bitcoin news")
        
        # Verify failure result
        self.assertFalse(result.success)
        self.assertIn("Content filtered out", result.error_message)
        
        # Verify workflow stats updated
        self.assertEqual(agent.workflow_stats['filtered_content'], 1)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    async def test_execute_workflow_posting_failure(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test workflow execution with Bluesky posting failure"""
        # Setup successful news and content generation
        mock_news_instance = Mock()
        mock_news_instance._arun = AsyncMock(return_value=json.dumps({
            "success": True,
            "news_items": [self.test_news.to_dict()]
        }))
        mock_news_tool.return_value = mock_news_instance
        
        mock_content_instance = Mock()
        mock_content_instance._arun = AsyncMock(return_value=json.dumps({
            "success": True,
            "content": self.test_content.to_dict()
        }))
        mock_content_tool.return_value = mock_content_instance
        
        # Setup social tool to fail
        mock_social_instance = Mock()
        mock_social_instance._arun = AsyncMock(return_value={
            "success": False,
            "error_message": "Authentication failed",
            "retry_count": 2
        })
        mock_social_tool.return_value = mock_social_instance
        
        # Create agent
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock content filter to approve content
        agent.content_filter.filter_content = Mock(return_value=(True, {"reasons": ["Approved"]}))
        
        result = await agent.execute_workflow("Bitcoin news")
        
        # Verify failure result
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Authentication failed")
        self.assertEqual(result.retry_count, 2)
        
        # Verify workflow stats updated
        self.assertEqual(agent.workflow_stats['failed_posts'], 1)
        
        # Verify content still added to history
        self.assertEqual(len(agent.content_history), 1)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_add_to_history(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test adding content to history"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock content filter add_to_history method
        agent.content_filter.add_to_history = Mock()
        
        # Add content to history
        agent.add_to_history(self.test_content)
        
        # Verify content added
        self.assertEqual(len(agent.content_history), 1)
        self.assertEqual(agent.content_history[0], self.test_content)
        
        # Verify content filter was called
        agent.content_filter.add_to_history.assert_called_once_with(self.test_content)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_add_to_history_max_size(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test history size limit enforcement"""
        # Set small max history size
        self.config.max_history_size = 2
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock content filter
        agent.content_filter.add_to_history = Mock()
        
        # Add multiple items
        for i in range(5):
            content = GeneratedContent(
                text=f"Test content {i}",
                hashtags=[],
                engagement_score=0.5,
                content_type=ContentType.NEWS,
                source_news=self.test_news
            )
            agent.add_to_history(content)
        
        # Verify only last 2 items kept
        self.assertEqual(len(agent.content_history), 2)
        self.assertEqual(agent.content_history[0].text, "Test content 3")
        self.assertEqual(agent.content_history[1].text, "Test content 4")
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_get_workflow_stats(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test workflow statistics retrieval"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Mock content filter stats
        agent.content_filter.get_history_stats = Mock(return_value={
            'total_items': 5,
            'avg_engagement_score': 0.75
        })
        
        # Update some stats
        agent.workflow_stats['total_executions'] = 10
        agent.workflow_stats['successful_posts'] = 8
        agent.workflow_stats['failed_posts'] = 2
        
        # Add some content to history
        agent.content_history = [self.test_content, self.test_content]
        
        stats = agent.get_workflow_stats()
        
        # Verify stats
        self.assertEqual(stats['total_executions'], 10)
        self.assertEqual(stats['successful_posts'], 8)
        self.assertEqual(stats['failed_posts'], 2)
        self.assertEqual(stats['success_rate'], 0.8)
        self.assertEqual(stats['content_history_size'], 2)
        self.assertIn('content_filter_stats', stats)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_get_recent_content(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test recent content retrieval"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Add multiple content items
        contents = []
        for i in range(5):
            content = GeneratedContent(
                text=f"Test content {i}",
                hashtags=[f"#test{i}"],
                engagement_score=0.5 + i * 0.1,
                content_type=ContentType.NEWS,
                source_news=self.test_news
            )
            contents.append(content)
            agent.content_history.append(content)
        
        # Get recent content (limit 3)
        recent = agent.get_recent_content(limit=3)
        
        # Verify results (should be reversed order - most recent first)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0]['text'], "Test content 4")
        self.assertEqual(recent[1]['text'], "Test content 3")
        self.assertEqual(recent[2]['text'], "Test content 2")
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_clear_history(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test history clearing"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Add content to history
        agent.content_history = [self.test_content, self.test_content]
        
        # Mock content filter collections
        agent.content_filter.recent_posts = Mock()
        agent.content_filter.content_hashes = Mock()
        
        # Clear history
        agent.clear_history()
        
        # Verify history cleared
        self.assertEqual(len(agent.content_history), 0)
        agent.content_filter.recent_posts.clear.assert_called_once()
        agent.content_filter.content_hashes.clear.assert_called_once()
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_parse_generated_content_success(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test successful content parsing"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Create test content data
        content_data = self.test_content.to_dict()
        
        # Parse content
        parsed = agent._parse_generated_content(content_data)
        
        # Verify parsing
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.text, self.test_content.text)
        self.assertEqual(parsed.hashtags, self.test_content.hashtags)
        self.assertEqual(parsed.engagement_score, self.test_content.engagement_score)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_parse_generated_content_failure(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test content parsing failure"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        # Create invalid content data
        content_data = {"invalid": "data"}
        
        # Parse content
        parsed = agent._parse_generated_content(content_data)
        
        # Verify parsing failed
        self.assertIsNone(parsed)
    
    @patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool')
    @patch('src.agents.bluesky_crypto_agent.create_content_generation_tool')
    @patch('src.agents.bluesky_crypto_agent.BlueskySocialTool')
    def test_create_error_result(self, mock_social_tool, mock_content_tool, mock_news_tool):
        """Test error result creation"""
        agent = BlueskyCryptoAgent(self.mock_llm, self.config)
        
        start_time = datetime.now()
        error_msg = "Test error message"
        
        # Create error result without content
        result = agent._create_error_result(error_msg, start_time)
        
        # Verify error result
        self.assertFalse(result.success)
        self.assertIsNone(result.post_id)
        self.assertEqual(result.error_message, error_msg)
        self.assertIsNotNone(result.content)
        self.assertEqual(result.content.text, "Workflow execution failed")
        
        # Create error result with content
        result_with_content = agent._create_error_result(error_msg, start_time, self.test_content)
        
        # Verify error result with content
        self.assertFalse(result_with_content.success)
        self.assertEqual(result_with_content.content, self.test_content)


if __name__ == '__main__':
    # Run async tests
    def run_async_test(coro):
        """Helper to run async test methods"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    # Patch async test methods to run with asyncio
    original_test_methods = []
    for name in dir(TestBlueskyCryptoAgent):
        if name.startswith('test_') and 'async' in name:
            method = getattr(TestBlueskyCryptoAgent, name)
            if asyncio.iscoroutinefunction(method):
                original_test_methods.append((name, method))
                # Replace with sync wrapper
                setattr(TestBlueskyCryptoAgent, name, 
                       lambda self, m=method: run_async_test(m(self)))
    
    unittest.main()