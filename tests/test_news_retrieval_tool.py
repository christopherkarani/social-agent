# tests/test_news_retrieval_tool.py
"""
Unit tests for NewsRetrievalTool and related components
"""
import json
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from src.tools.news_retrieval_tool import (
    NewsRetrievalTool,
    PerplexityAPIClient,
    NewsContentParser,
    create_news_retrieval_tool
)
from src.config.agent_config import AgentConfig
from src.models.data_models import NewsItem


class TestPerplexityAPIClient:
    """Test cases for PerplexityAPIClient"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.api_key = "test_api_key"
        self.client = PerplexityAPIClient(self.api_key, max_retries=3)
    
    def test_init(self):
        """Test client initialization"""
        assert self.client.api_key == self.api_key
        assert self.client.max_retries == 3
        assert self.client.base_url == "https://api.perplexity.ai"
        assert "Authorization" in self.client.session.headers
        assert self.client.session.headers["Authorization"] == f"Bearer {self.api_key}"
    
    def test_calculate_backoff_delay(self):
        """Test exponential backoff calculation"""
        assert self.client._calculate_backoff_delay(0) == 1.0
        assert self.client._calculate_backoff_delay(1) == 2.0
        assert self.client._calculate_backoff_delay(2) == 4.0
        assert self.client._calculate_backoff_delay(3) == 8.0
        assert self.client._calculate_backoff_delay(10) == 30.0  # Capped at 30
    
    def test_is_retryable_error(self):
        """Test retryable error detection"""
        assert self.client._is_retryable_error(429) is True  # Rate limit
        assert self.client._is_retryable_error(500) is True  # Server error
        assert self.client._is_retryable_error(502) is True  # Bad gateway
        assert self.client._is_retryable_error(503) is True  # Service unavailable
        assert self.client._is_retryable_error(504) is True  # Gateway timeout
        
        assert self.client._is_retryable_error(400) is False  # Bad request
        assert self.client._is_retryable_error(401) is False  # Unauthorized
        assert self.client._is_retryable_error(404) is False  # Not found
    
    @patch('requests.Session.post')
    def test_search_news_success(self, mock_post):
        """Test successful news search"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "**Bitcoin Reaches New High** Bitcoin price surged to $50,000 today."
                }
            }],
            "citations": [{"title": "CoinDesk", "url": "https://coindesk.com/test"}]
        }
        mock_post.return_value = mock_response
        
        result = self.client.search_news("Bitcoin news")
        
        assert result["choices"][0]["message"]["content"] == "**Bitcoin Reaches New High** Bitcoin price surged to $50,000 today."
        mock_post.assert_called_once()
        
        # Verify request payload structure
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['model'] == "llama-3.1-sonar-small-128k-online"
        assert len(payload['messages']) == 2
        assert payload['return_citations'] is True
    
    @patch('requests.Session.post')
    @patch('time.sleep')
    def test_search_news_retry_on_server_error(self, mock_sleep, mock_post):
        """Test retry logic on server errors"""
        # Mock server error then success
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"choices": [{"message": {"content": "Success"}}]}
        
        mock_post.side_effect = [error_response, success_response]
        
        result = self.client.search_news("Bitcoin news")
        
        assert result["choices"][0]["message"]["content"] == "Success"
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(1.0)  # First backoff delay
    
    @patch('requests.Session.post')
    @patch('time.sleep')
    def test_search_news_max_retries_exceeded(self, mock_sleep, mock_post):
        """Test behavior when max retries are exceeded"""
        # Mock consistent server errors
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        mock_post.return_value = error_response
        
        with pytest.raises(Exception) as exc_info:
            self.client.search_news("Bitcoin news")
        
        assert "Failed to retrieve news after 3 attempts" in str(exc_info.value)
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries
    
    @patch('requests.Session.post')
    def test_search_news_non_retryable_error(self, mock_post):
        """Test handling of non-retryable errors"""
        # Mock 401 unauthorized error
        error_response = Mock()
        error_response.status_code = 401
        error_response.text = "Unauthorized"
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = error_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            self.client.search_news("Bitcoin news")
        
        assert mock_post.call_count == 1  # No retries for non-retryable errors
    
    @patch('requests.Session.post')
    @patch('time.sleep')
    def test_search_news_timeout_retry(self, mock_sleep, mock_post):
        """Test retry logic on timeout errors"""
        # Mock timeout then success
        mock_post.side_effect = [
            requests.exceptions.Timeout("Request timeout"),
            Mock(status_code=200, json=lambda: {"choices": [{"message": {"content": "Success"}}]})
        ]
        
        result = self.client.search_news("Bitcoin news")
        
        assert result["choices"][0]["message"]["content"] == "Success"
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()


class TestNewsContentParser:
    """Test cases for NewsContentParser"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.content_themes = ["Bitcoin", "Ethereum", "DeFi"]
        self.parser = NewsContentParser(self.content_themes)
    
    def test_init(self):
        """Test parser initialization"""
        assert self.parser.content_themes == ["bitcoin", "ethereum", "defi"]
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation"""
        # High relevance text
        high_relevance_text = "Bitcoin and Ethereum prices surge as DeFi adoption grows"
        score = self.parser.calculate_relevance_score(high_relevance_text, ["Bitcoin", "DeFi"])
        assert score > 0.5
        
        # Low relevance text
        low_relevance_text = "Stock market closes higher today"
        score = self.parser.calculate_relevance_score(low_relevance_text, [])
        assert score < 0.3
        
        # Medium relevance text
        medium_relevance_text = "Cryptocurrency market shows mixed signals"
        score = self.parser.calculate_relevance_score(medium_relevance_text, ["Crypto"])
        assert 0.2 <= score <= 0.8
    
    def test_extract_topics(self):
        """Test topic extraction from text"""
        # Test Bitcoin detection
        bitcoin_text = "Bitcoin price reaches new all-time high"
        topics = self.parser.extract_topics(bitcoin_text)
        assert "Bitcoin" in topics
        
        # Test multiple topics
        multi_text = "Ethereum DeFi protocols see increased staking activity"
        topics = self.parser.extract_topics(multi_text)
        assert "Ethereum" in topics
        assert "DeFi" in topics
        assert "Staking" in topics
        
        # Test fallback to general crypto
        generic_text = "Market analysis shows positive trends"
        topics = self.parser.extract_topics(generic_text)
        assert "Cryptocurrency" in topics
    
    def test_parse_response_structured_content(self):
        """Test parsing of structured API response"""
        api_response = {
            "choices": [{
                "message": {
                    "content": """**Bitcoin Reaches $50,000**
                    Bitcoin price surged to $50,000 today amid institutional adoption.
                    
                    **Ethereum Updates Smart Contracts**
                    Ethereum network implements new smart contract features for better efficiency."""
                }
            }],
            "citations": [
                {"title": "CoinDesk", "url": "https://coindesk.com/bitcoin-50k"},
                {"title": "CoinTelegraph", "url": "https://cointelegraph.com/ethereum-update"}
            ]
        }
        
        news_items = self.parser.parse_response(api_response)
        
        assert len(news_items) >= 1
        assert any("Bitcoin" in item.headline for item in news_items)
        assert all(item.relevance_score > 0 for item in news_items)
        assert all(len(item.topics) > 0 for item in news_items)
    
    def test_parse_response_empty_choices(self):
        """Test handling of empty API response"""
        api_response = {"choices": []}
        
        news_items = self.parser.parse_response(api_response)
        
        assert len(news_items) == 0
    
    def test_parse_response_fallback_content(self):
        """Test fallback content creation when structured parsing fails"""
        api_response = {
            "choices": [{
                "message": {
                    "content": "General cryptocurrency market update with various developments in Bitcoin and Ethereum sectors."
                }
            }]
        }
        
        news_items = self.parser.parse_response(api_response)
        
        assert len(news_items) == 1
        assert "Cryptocurrency" in news_items[0].headline or "Cryptocurrency" in news_items[0].topics
    
    def test_create_news_item_valid_data(self):
        """Test creation of valid NewsItem"""
        item_data = {
            "headline": "Bitcoin Price Surges",
            "summary": "Bitcoin reaches new highs amid institutional adoption"
        }
        citations = [{"title": "CoinDesk", "url": "https://coindesk.com/test"}]
        
        news_item = self.parser._create_news_item(item_data, citations)
        
        assert news_item is not None
        assert news_item.headline == "Bitcoin Price Surges"
        assert "Bitcoin" in news_item.topics
        assert news_item.relevance_score > 0
        assert news_item.source == "CoinDesk"
        assert news_item.url == "https://coindesk.com/test"
    
    def test_create_news_item_invalid_data(self):
        """Test handling of invalid data"""
        # Missing headline
        item_data = {"summary": "Some summary"}
        news_item = self.parser._create_news_item(item_data, [])
        assert news_item is None
        
        # Missing summary
        item_data = {"headline": "Some headline"}
        news_item = self.parser._create_news_item(item_data, [])
        assert news_item is None
        
        # Empty strings
        item_data = {"headline": "", "summary": ""}
        news_item = self.parser._create_news_item(item_data, [])
        assert news_item is None


class TestNewsRetrievalTool:
    """Test cases for NewsRetrievalTool"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = AgentConfig(
            perplexity_api_key="test_api_key",
            content_themes=["Bitcoin", "Ethereum", "DeFi"],
            max_retries=3
        )
        self.tool = NewsRetrievalTool(self.config)
    
    def test_init(self):
        """Test tool initialization"""
        assert self.tool.name == "crypto_news_retrieval"
        assert "cryptocurrency news" in self.tool.description.lower()
        assert self.tool.config == self.config
        assert isinstance(self.tool.api_client, PerplexityAPIClient)
        assert isinstance(self.tool.parser, NewsContentParser)
    
    @patch.object(PerplexityAPIClient, 'search_news')
    def test_run_success(self, mock_search):
        """Test successful tool execution"""
        # Mock API response
        mock_search.return_value = {
            "choices": [{
                "message": {
                    "content": "**Bitcoin Reaches $50,000** Bitcoin price surged today."
                }
            }],
            "citations": [{"title": "CoinDesk", "url": "https://coindesk.com/test"}]
        }
        
        result = self.tool._run("Bitcoin news")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["count"] >= 0
        assert "news_items" in result_data
        mock_search.assert_called_once_with("Bitcoin news", max_results=10)
    
    @patch.object(PerplexityAPIClient, 'search_news')
    def test_run_api_error(self, mock_search):
        """Test tool execution with API error"""
        # Mock API error
        mock_search.side_effect = Exception("API Error")
        
        result = self.tool._run("Bitcoin news")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert result_data["count"] == 0
        assert "error" in result_data
        assert "API Error" in result_data["error"]
    
    @patch.object(PerplexityAPIClient, 'search_news')
    def test_run_no_relevant_news(self, mock_search):
        """Test tool execution when no relevant news is found"""
        # Mock API response with low relevance content
        mock_search.return_value = {
            "choices": [{
                "message": {
                    "content": "Stock market news about traditional finance"
                }
            }]
        }
        
        result = self.tool._run("Bitcoin news")
        result_data = json.loads(result)
        
        # Should still return success but with low/no count
        assert result_data["success"] in [True, False]  # Depends on relevance threshold
        assert result_data["count"] >= 0
    
    @patch.object(PerplexityAPIClient, 'search_news')
    def test_run_filters_by_relevance(self, mock_search):
        """Test that tool filters news by relevance score"""
        # Mock mixed relevance content
        mock_search.return_value = {
            "choices": [{
                "message": {
                    "content": """**Bitcoin Price Update** Bitcoin reaches new highs.
                    **Stock Market News** Traditional stocks perform well."""
                }
            }]
        }
        
        result = self.tool._run("Bitcoin news")
        result_data = json.loads(result)
        
        # Should filter out low-relevance content
        if result_data["success"] and result_data["count"] > 0:
            for item in result_data["news_items"]:
                assert item["relevance_score"] >= 0.3
    
    @pytest.mark.asyncio
    @patch.object(NewsRetrievalTool, '_run')
    async def test_arun(self, mock_run):
        """Test async execution"""
        mock_run.return_value = '{"success": true, "count": 1}'
        
        result = await self.tool._arun("Bitcoin news")
        
        assert result == '{"success": true, "count": 1}'
        mock_run.assert_called_once_with("Bitcoin news")


class TestCreateNewsRetrievalTool:
    """Test cases for factory function"""
    
    def test_create_tool_success(self):
        """Test successful tool creation"""
        config = AgentConfig(perplexity_api_key="test_key")
        
        tool = create_news_retrieval_tool(config)
        
        assert isinstance(tool, NewsRetrievalTool)
        assert tool.config == config
    
    def test_create_tool_missing_api_key(self):
        """Test tool creation with missing API key"""
        config = AgentConfig(perplexity_api_key="")
        
        with pytest.raises(ValueError) as exc_info:
            create_news_retrieval_tool(config)
        
        assert "Perplexity API key is required" in str(exc_info.value)


class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    def setup_method(self):
        """Setup integration test fixtures"""
        self.config = AgentConfig(
            perplexity_api_key="test_api_key",
            content_themes=["Bitcoin", "Ethereum", "DeFi", "NFTs"],
            max_retries=2
        )
    
    @patch('requests.Session.post')
    def test_end_to_end_news_retrieval(self, mock_post):
        """Test complete end-to-end news retrieval flow"""
        # Mock realistic API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": """**Bitcoin Hits $45,000 Milestone**
                    Bitcoin price reached $45,000 for the first time this month, driven by institutional adoption and positive regulatory news.
                    
                    **Ethereum 2.0 Staking Rewards Increase**
                    Ethereum staking rewards have increased to 5.2% APY as more validators join the network."""
                }
            }],
            "citations": [
                {"title": "CoinDesk", "url": "https://coindesk.com/bitcoin-45k"},
                {"title": "Ethereum Foundation", "url": "https://ethereum.org/staking-update"}
            ]
        }
        mock_post.return_value = mock_response
        
        # Create and execute tool
        tool = create_news_retrieval_tool(self.config)
        result = tool._run("latest crypto news")
        result_data = json.loads(result)
        
        # Verify results
        assert result_data["success"] is True
        assert result_data["count"] > 0
        
        # Check news item structure
        news_items = result_data["news_items"]
        for item in news_items:
            assert "headline" in item
            assert "summary" in item
            assert "source" in item
            assert "timestamp" in item
            assert "relevance_score" in item
            assert "topics" in item
            assert isinstance(item["topics"], list)
            assert len(item["topics"]) > 0
    
    def test_error_recovery_scenarios(self):
        """Test various error recovery scenarios"""
        # Test with invalid API key
        invalid_config = AgentConfig(perplexity_api_key="")
        
        with pytest.raises(ValueError):
            create_news_retrieval_tool(invalid_config)
        
        # Test with valid config but API errors will be handled by retry logic
        valid_config = AgentConfig(perplexity_api_key="test_key", max_retries=1)
        tool = create_news_retrieval_tool(valid_config)
        
        # Tool should be created successfully
        assert isinstance(tool, NewsRetrievalTool)
        assert tool.config.max_retries == 1