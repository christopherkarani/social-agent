# tests/test_mock_services.py
"""
Mock services for external API testing
Provides mock implementations of external services for testing
"""
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, MagicMock

from src.models.data_models import NewsItem, GeneratedContent, ContentType


class MockPerplexityAPI:
    """Mock implementation of Perplexity API for testing"""
    
    def __init__(self, simulate_failures: bool = False, failure_rate: float = 0.1):
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
        self.call_count = 0
        self.rate_limit_calls = 0
        self.max_calls_per_minute = 60
    
    def search_news(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Mock news search with realistic responses"""
        self.call_count += 1
        self.rate_limit_calls += 1
        
        # Simulate rate limiting
        if self.rate_limit_calls > self.max_calls_per_minute:
            raise Exception("Rate limit exceeded")
        
        # Simulate random failures
        if self.simulate_failures and random.random() < self.failure_rate:
            raise Exception("API temporarily unavailable")
        
        # Simulate network delay
        time.sleep(0.1)
        
        # Generate mock news based on query
        mock_news = self._generate_mock_news(query, max_results)
        
        return {
            "choices": [{
                "message": {
                    "content": self._format_news_content(mock_news)
                }
            }],
            "citations": self._generate_citations(mock_news)
        }
    
    def _generate_mock_news(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Generate realistic mock news items"""
        crypto_topics = {
            "bitcoin": ["Bitcoin", "BTC", "Mining", "Halving"],
            "ethereum": ["Ethereum", "ETH", "Smart Contracts", "DeFi"],
            "defi": ["DeFi", "Yield Farming", "Liquidity", "DEX"],
            "nft": ["NFTs", "Digital Art", "Collectibles", "Marketplace"],
            "crypto": ["Cryptocurrency", "Blockchain", "Trading", "Market"]
        }
        
        # Determine relevant topics based on query
        query_lower = query.lower()
        relevant_topics = []
        for key, topics in crypto_topics.items():
            if key in query_lower:
                relevant_topics.extend(topics)
        
        if not relevant_topics:
            relevant_topics = crypto_topics["crypto"]
        
        # Generate mock news items
        headlines = [
            f"{relevant_topics[0]} Reaches New Milestone in Market Development",
            f"Major Institution Adopts {relevant_topics[0]} for Payment Solutions",
            f"{relevant_topics[0]} Network Upgrade Shows Promising Results",
            f"Regulatory Clarity Boosts {relevant_topics[0]} Adoption Rates",
            f"{relevant_topics[0]} Trading Volume Hits Record High This Week"
        ]
        
        summaries = [
            f"Recent developments in {relevant_topics[0]} show significant progress in institutional adoption and technical improvements.",
            f"Market analysis indicates strong fundamentals for {relevant_topics[0]} with increasing developer activity and user engagement.",
            f"Technical indicators suggest {relevant_topics[0]} is positioned for continued growth amid favorable market conditions.",
            f"Industry experts highlight {relevant_topics[0]} innovations as key drivers for the next phase of cryptocurrency evolution.",
            f"Latest {relevant_topics[0]} metrics demonstrate robust network health and growing ecosystem participation."
        ]
        
        mock_news = []
        for i in range(min(max_results, len(headlines))):
            mock_news.append({
                "headline": headlines[i],
                "summary": summaries[i],
                "source": f"CryptoNews{i+1}",
                "timestamp": datetime.now().isoformat(),
                "topics": relevant_topics[:3],
                "relevance_score": 0.7 + (i * 0.05),
                "url": f"https://example.com/news/{i+1}"
            })
        
        return mock_news
    
    def _format_news_content(self, news_items: List[Dict[str, Any]]) -> str:
        """Format news items as structured content"""
        content_parts = []
        for item in news_items:
            content_parts.append(f"**{item['headline']}**")
            content_parts.append(item['summary'])
            content_parts.append("")  # Empty line separator
        
        return "\n".join(content_parts)
    
    def _generate_citations(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate mock citations"""
        citations = []
        for item in news_items:
            citations.append({
                "title": item['source'],
                "url": item['url']
            })
        return citations
    
    def reset_rate_limit(self):
        """Reset rate limit counter (simulate time passing)"""
        self.rate_limit_calls = 0


class MockBlueskySocialAPI:
    """Mock implementation of Bluesky Social API for testing"""
    
    def __init__(self, simulate_failures: bool = False, failure_rate: float = 0.1):
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
        self.authenticated_users = {}
        self.posts = []
        self.post_counter = 1000
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Mock authentication"""
        if self.simulate_failures and random.random() < self.failure_rate:
            raise Exception("Authentication server unavailable")
        
        # Simulate authentication validation
        if not username or not password:
            raise Exception("Invalid credentials")
        
        if username == "invalid_user":
            raise Exception("User not found")
        
        if password == "wrong_password":
            raise Exception("Invalid password")
        
        # Create mock session
        session_token = f"session_{username}_{int(time.time())}"
        self.authenticated_users[username] = {
            "session_token": session_token,
            "authenticated_at": datetime.now(),
            "did": f"did:plc:{username}123"
        }
        
        return {
            "accessJwt": session_token,
            "refreshJwt": f"refresh_{session_token}",
            "handle": username,
            "did": self.authenticated_users[username]["did"]
        }
    
    def send_post(self, username: str, content: str) -> Dict[str, Any]:
        """Mock post creation"""
        if username not in self.authenticated_users:
            raise Exception("User not authenticated")
        
        if self.simulate_failures and random.random() < self.failure_rate:
            raise Exception("Post service temporarily unavailable")
        
        # Validate content
        if len(content) > 300:
            raise Exception("Post exceeds character limit")
        
        if not content.strip():
            raise Exception("Post content cannot be empty")
        
        # Create mock post
        post_id = f"post_{self.post_counter}"
        self.post_counter += 1
        
        post_data = {
            "uri": f"at://{self.authenticated_users[username]['did']}/app.bsky.feed.post/{post_id}",
            "cid": f"cid_{post_id}",
            "content": content,
            "author": username,
            "created_at": datetime.now().isoformat(),
            "likes": 0,
            "reposts": 0,
            "replies": 0
        }
        
        self.posts.append(post_data)
        
        return {
            "uri": post_data["uri"],
            "cid": post_data["cid"]
        }
    
    def get_posts(self, username: str) -> List[Dict[str, Any]]:
        """Get posts for a user"""
        return [post for post in self.posts if post["author"] == username]
    
    def clear_posts(self):
        """Clear all posts (for testing)"""
        self.posts = []
    
    def simulate_network_error(self):
        """Force a network error for testing"""
        raise Exception("Network connection failed")


class MockContentGenerationAPI:
    """Mock implementation of content generation API for testing"""
    
    def __init__(self, simulate_failures: bool = False, failure_rate: float = 0.1):
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
        self.generation_templates = {
            "news": [
                "🚀 {headline} - This could be a game-changer for the crypto market! {hashtags}",
                "📈 Breaking: {headline}. What are your thoughts on this development? {hashtags}",
                "💡 Insight: {headline}. The implications for crypto adoption are huge! {hashtags}",
                "🔥 Hot take: {headline}. This is why I'm bullish on crypto long-term! {hashtags}"
            ],
            "analysis": [
                "📊 Technical analysis: {headline}. The charts are looking promising! {hashtags}",
                "🎯 Market insight: {headline}. Smart money is paying attention! {hashtags}",
                "💎 Deep dive: {headline}. This is what institutional adoption looks like! {hashtags}"
            ],
            "opinion": [
                "🤔 My take: {headline}. The crypto space keeps evolving! {hashtags}",
                "💭 Thoughts: {headline}. What do you think this means for the future? {hashtags}"
            ]
        }
    
    def generate_content(self, news_data: Dict[str, Any], content_type: str = "news", 
                        target_engagement: float = 0.7) -> Dict[str, Any]:
        """Mock content generation"""
        if self.simulate_failures and random.random() < self.failure_rate:
            raise Exception("Content generation service unavailable")
        
        # Simulate processing time
        time.sleep(0.2)
        
        # Extract news information
        news_items = news_data.get("news_items", [])
        if not news_items:
            raise Exception("No news items provided for content generation")
        
        # Select primary news item
        primary_news = news_items[0]
        headline = primary_news.get("headline", "Crypto Market Update")
        topics = primary_news.get("topics", ["Cryptocurrency"])
        
        # Generate hashtags
        hashtags = []
        for topic in topics[:3]:  # Limit to 3 hashtags
            hashtag = f"#{topic.replace(' ', '').replace('-', '').lower()}"
            if hashtag not in hashtags:
                hashtags.append(hashtag)
        
        # Select template based on content type
        templates = self.generation_templates.get(content_type, self.generation_templates["news"])
        template = random.choice(templates)
        
        # Generate content
        hashtag_text = " ".join(hashtags)
        generated_text = template.format(headline=headline[:100], hashtags=hashtag_text)
        
        # Ensure content fits within character limit
        if len(generated_text) > 280:  # Leave room for hashtags
            # Truncate headline and regenerate
            short_headline = headline[:50] + "..."
            generated_text = template.format(headline=short_headline, hashtags=hashtag_text)
        
        # Calculate engagement score based on content quality
        engagement_score = self._calculate_engagement_score(generated_text, hashtags)
        
        return {
            "success": True,
            "content": {
                "text": generated_text,
                "hashtags": hashtags,
                "engagement_score": engagement_score,
                "content_type": content_type,
                "source_news": primary_news,
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "template_used": template,
                    "generation_method": "mock_api"
                }
            }
        }
    
    def _calculate_engagement_score(self, text: str, hashtags: List[str]) -> float:
        """Calculate mock engagement score"""
        score = 0.5  # Base score
        
        # Boost for emojis
        emoji_count = sum(1 for char in text if ord(char) > 127)
        score += min(emoji_count * 0.05, 0.2)
        
        # Boost for hashtags
        score += min(len(hashtags) * 0.1, 0.2)
        
        # Boost for engagement words
        engagement_words = ["breaking", "hot", "bullish", "game-changer", "huge", "promising"]
        word_matches = sum(1 for word in engagement_words if word in text.lower())
        score += min(word_matches * 0.05, 0.15)
        
        # Penalty for spam indicators
        spam_words = ["buy now", "guaranteed", "moon", "lambo"]
        spam_matches = sum(1 for word in spam_words if word in text.lower())
        score -= spam_matches * 0.1
        
        return max(0.1, min(1.0, score))


class MockServiceFactory:
    """Factory for creating mock services with consistent configuration"""
    
    @staticmethod
    def create_perplexity_mock(simulate_failures: bool = False, failure_rate: float = 0.1) -> MockPerplexityAPI:
        """Create a mock Perplexity API instance"""
        return MockPerplexityAPI(simulate_failures=simulate_failures, failure_rate=failure_rate)
    
    @staticmethod
    def create_bluesky_mock(simulate_failures: bool = False, failure_rate: float = 0.1) -> MockBlueskySocialAPI:
        """Create a mock Bluesky API instance"""
        return MockBlueskySocialAPI(simulate_failures=simulate_failures, failure_rate=failure_rate)
    
    @staticmethod
    def create_content_generation_mock(simulate_failures: bool = False, failure_rate: float = 0.1) -> MockContentGenerationAPI:
        """Create a mock content generation API instance"""
        return MockContentGenerationAPI(simulate_failures=simulate_failures, failure_rate=failure_rate)
    
    @staticmethod
    def create_test_suite_mocks(simulate_failures: bool = False) -> Dict[str, Any]:
        """Create a complete set of mocks for test suite"""
        return {
            "perplexity": MockServiceFactory.create_perplexity_mock(simulate_failures=simulate_failures),
            "bluesky": MockServiceFactory.create_bluesky_mock(simulate_failures=simulate_failures),
            "content_generation": MockServiceFactory.create_content_generation_mock(simulate_failures=simulate_failures)
        }


# Test fixtures and utilities
class MockTestData:
    """Provides consistent test data for mock services"""
    
    @staticmethod
    def get_sample_news_query() -> str:
        return "latest Bitcoin and Ethereum news"
    
    @staticmethod
    def get_sample_news_response() -> Dict[str, Any]:
        return {
            "success": True,
            "count": 3,
            "news_items": [
                {
                    "headline": "Bitcoin Adoption Accelerates Among Fortune 500 Companies",
                    "summary": "Major corporations continue to add Bitcoin to their treasury reserves, signaling growing institutional confidence in cryptocurrency as a store of value.",
                    "source": "CryptoInstitutional",
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": 0.92,
                    "topics": ["Bitcoin", "Institutional", "Adoption"],
                    "url": "https://example.com/bitcoin-fortune500"
                },
                {
                    "headline": "Ethereum Layer 2 Solutions See Record Transaction Volume",
                    "summary": "Ethereum scaling solutions process unprecedented transaction volumes as DeFi and NFT activity continues to grow across the ecosystem.",
                    "source": "EthereumDaily",
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": 0.88,
                    "topics": ["Ethereum", "Layer2", "DeFi", "Scaling"],
                    "url": "https://example.com/ethereum-l2-volume"
                },
                {
                    "headline": "Central Bank Digital Currency Pilots Expand Globally",
                    "summary": "Multiple central banks advance CBDC development programs, exploring digital currency implementations for national payment systems.",
                    "source": "CBDCWatch",
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": 0.75,
                    "topics": ["CBDC", "Central Banks", "Digital Currency"],
                    "url": "https://example.com/cbdc-pilots"
                }
            ]
        }
    
    @staticmethod
    def get_sample_generated_content() -> Dict[str, Any]:
        return {
            "success": True,
            "content": {
                "text": "🚀 Bitcoin Adoption Accelerates Among Fortune 500 Companies - This could be a game-changer for the crypto market! #bitcoin #institutional #adoption",
                "hashtags": ["#bitcoin", "#institutional", "#adoption"],
                "engagement_score": 0.85,
                "content_type": "news",
                "source_news": MockTestData.get_sample_news_response()["news_items"][0],
                "created_at": datetime.now().isoformat()
            }
        }
    
    @staticmethod
    def get_sample_post_result() -> Dict[str, Any]:
        return {
            "success": True,
            "post_id": "at://did:plc:test123/app.bsky.feed.post/sample456",
            "cid": "cid_sample456",
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0
        }

class TestMockServices:
    """Test the mock services functionality"""
    
    def test_mock_perplexity_api(self):
        """Test MockPerplexityAPI functionality"""
        mock_api = MockPerplexityAPI()
        
        # Test successful news search
        result = mock_api.search_news("bitcoin news", max_results=5)
        
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        assert "content" in result["choices"][0]["message"]
        assert "citations" in result
        
        # Test call counting
        assert mock_api.call_count == 1
    
    def test_mock_perplexity_api_with_failures(self):
        """Test MockPerplexityAPI with simulated failures"""
        mock_api = MockPerplexityAPI(simulate_failures=True, failure_rate=1.0)  # Always fail
        
        # Should raise exception
        try:
            mock_api.search_news("bitcoin news")
            assert False, "Expected exception was not raised"
        except Exception as e:
            assert "API temporarily unavailable" in str(e)
    
    def test_mock_bluesky_api(self):
        """Test MockBlueskySocialAPI functionality"""
        mock_api = MockBlueskySocialAPI()
        
        # Test authentication
        auth_result = mock_api.login("test_user", "test_password")
        
        assert "accessJwt" in auth_result
        assert "handle" in auth_result
        assert auth_result["handle"] == "test_user"
        
        # Test posting
        post_result = mock_api.send_post("test_user", "Test post content")
        
        assert "uri" in post_result
        assert "cid" in post_result
        
        # Verify post was stored
        posts = mock_api.get_posts("test_user")
        assert len(posts) == 1
        assert posts[0]["content"] == "Test post content"
    
    def test_mock_bluesky_api_authentication_failures(self):
        """Test MockBlueskySocialAPI authentication failures"""
        mock_api = MockBlueskySocialAPI()
        
        # Test invalid credentials
        try:
            mock_api.login("invalid_user", "wrong_password")
            assert False, "Expected exception was not raised"
        except Exception as e:
            assert "User not found" in str(e)
        
        # Test posting without authentication
        try:
            mock_api.send_post("unauthenticated_user", "Test content")
            assert False, "Expected exception was not raised"
        except Exception as e:
            assert "User not authenticated" in str(e)
    
    def test_mock_content_generation_api(self):
        """Test MockContentGenerationAPI functionality"""
        mock_api = MockContentGenerationAPI()
        
        # Create sample news data
        news_data = {
            "news_items": [
                {
                    "headline": "Bitcoin Reaches New High",
                    "summary": "Bitcoin price increases significantly",
                    "topics": ["Bitcoin", "Price"]
                }
            ]
        }
        
        # Test content generation
        result = mock_api.generate_content(news_data, content_type="news")
        
        assert result["success"] is True
        assert "content" in result
        
        content = result["content"]
        assert "text" in content
        assert "hashtags" in content
        assert "engagement_score" in content
        assert content["content_type"] == "news"
        
        # Verify content quality
        assert len(content["text"]) > 0
        assert len(content["hashtags"]) > 0
        assert 0 <= content["engagement_score"] <= 1
    
    def test_mock_service_factory(self):
        """Test MockServiceFactory functionality"""
        # Test individual service creation
        perplexity_mock = MockServiceFactory.create_perplexity_mock()
        assert isinstance(perplexity_mock, MockPerplexityAPI)
        
        bluesky_mock = MockServiceFactory.create_bluesky_mock()
        assert isinstance(bluesky_mock, MockBlueskySocialAPI)
        
        content_mock = MockServiceFactory.create_content_generation_mock()
        assert isinstance(content_mock, MockContentGenerationAPI)
        
        # Test test suite creation
        test_mocks = MockServiceFactory.create_test_suite_mocks()
        
        assert "perplexity" in test_mocks
        assert "bluesky" in test_mocks
        assert "content_generation" in test_mocks
        
        assert isinstance(test_mocks["perplexity"], MockPerplexityAPI)
        assert isinstance(test_mocks["bluesky"], MockBlueskySocialAPI)
        assert isinstance(test_mocks["content_generation"], MockContentGenerationAPI)


class TestMockTestData:
    """Test the MockTestData functionality"""
    
    def test_sample_data_structure(self):
        """Test sample data structure"""
        # Test news response
        news_response = MockTestData.get_sample_news_response()
        
        assert news_response["success"] is True
        assert "count" in news_response
        assert "news_items" in news_response
        assert len(news_response["news_items"]) > 0
        
        # Verify news item structure
        news_item = news_response["news_items"][0]
        required_fields = ["headline", "summary", "source", "timestamp", "relevance_score", "topics"]
        for field in required_fields:
            assert field in news_item
        
        # Test generated content
        content_data = MockTestData.get_sample_generated_content()
        
        assert content_data["success"] is True
        assert "content" in content_data
        
        content = content_data["content"]
        content_fields = ["text", "hashtags", "engagement_score", "content_type", "source_news"]
        for field in content_fields:
            assert field in content
        
        # Test post result
        post_result = MockTestData.get_sample_post_result()
        
        assert post_result["success"] is True
        assert "post_id" in post_result
        assert "timestamp" in post_result
    
    def test_sample_queries(self):
        """Test sample query generation"""
        query = MockTestData.get_sample_news_query()
        
        assert isinstance(query, str)
        assert len(query) > 0
        assert "bitcoin" in query.lower() or "ethereum" in query.lower()