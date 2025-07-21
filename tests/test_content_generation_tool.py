# tests/test_content_generation_tool.py
"""
Unit tests for ContentGenerationTool
"""
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.tools.content_generation_tool import (
    ContentGenerationTool,
    ViralContentStrategies,
    ContentOptimizer,
    create_content_generation_tool
)
from src.models.data_models import NewsItem, GeneratedContent, ContentType
from src.config.agent_config import AgentConfig


class TestViralContentStrategies:
    """Test cases for ViralContentStrategies class"""
    
    def test_get_engagement_hook_breaking_news(self):
        """Test engagement hook selection for breaking news"""
        hook = ViralContentStrategies.get_engagement_hook("breaking_news")
        assert hook == "🚨 BREAKING:"
    
    def test_get_engagement_hook_analysis(self):
        """Test engagement hook selection for analysis"""
        hook = ViralContentStrategies.get_engagement_hook("analysis")
        assert hook == "💡 INSIGHT:"
    
    def test_get_engagement_hook_opinion(self):
        """Test engagement hook selection for opinion"""
        hook = ViralContentStrategies.get_engagement_hook("opinion")
        assert hook == "🔥 HOT TAKE:"
    
    def test_get_engagement_hook_bullish_sentiment(self):
        """Test engagement hook selection for bullish sentiment"""
        hook = ViralContentStrategies.get_engagement_hook("news", "bullish")
        assert hook == "📈 BULLISH:"
    
    def test_get_engagement_hook_bearish_sentiment(self):
        """Test engagement hook selection for bearish sentiment"""
        hook = ViralContentStrategies.get_engagement_hook("news", "bearish")
        assert hook == "📉 BEARISH:"
    
    def test_get_relevant_hashtags_bitcoin(self):
        """Test hashtag generation for Bitcoin topics"""
        topics = ["Bitcoin", "BTC"]
        hashtags = ViralContentStrategies.get_relevant_hashtags(topics)
        
        assert len(hashtags) <= 3
        assert any("Bitcoin" in tag or "BTC" in tag for tag in hashtags)
    
    def test_get_relevant_hashtags_ethereum(self):
        """Test hashtag generation for Ethereum topics"""
        topics = ["Ethereum", "ETH"]
        hashtags = ViralContentStrategies.get_relevant_hashtags(topics)
        
        assert len(hashtags) <= 3
        assert any("Ethereum" in tag or "ETH" in tag for tag in hashtags)
    
    def test_get_relevant_hashtags_defi(self):
        """Test hashtag generation for DeFi topics"""
        topics = ["DeFi", "Decentralized Finance"]
        hashtags = ViralContentStrategies.get_relevant_hashtags(topics)
        
        assert len(hashtags) <= 3
        assert any("DeFi" in tag for tag in hashtags)
    
    def test_get_relevant_hashtags_general(self):
        """Test hashtag generation for general topics"""
        topics = ["Unknown Topic"]
        hashtags = ViralContentStrategies.get_relevant_hashtags(topics)
        
        assert len(hashtags) >= 1
        assert any(tag in ["#Crypto", "#Blockchain", "#Web3"] for tag in hashtags)
    
    def test_get_relevant_hashtags_max_limit(self):
        """Test hashtag generation respects max limit"""
        topics = ["Bitcoin", "Ethereum", "DeFi", "NFT", "Trading"]
        hashtags = ViralContentStrategies.get_relevant_hashtags(topics, max_hashtags=2)
        
        assert len(hashtags) <= 2


class TestContentOptimizer:
    """Test cases for ContentOptimizer class"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return AgentConfig(
            max_post_length=300,
            min_engagement_score=0.7
        )
    
    @pytest.fixture
    def optimizer(self, config):
        """Create ContentOptimizer instance"""
        return ContentOptimizer(config)
    
    def test_calculate_engagement_score_with_hook(self, optimizer):
        """Test engagement score calculation with engagement hook"""
        content = "🚨 BREAKING: Bitcoin hits new high!"
        hashtags = ["#Bitcoin", "#BTC"]
        topics = ["Bitcoin"]
        
        score = optimizer.calculate_engagement_score(content, hashtags, topics)
        assert score > 0.2  # Should get points for hook
    
    def test_calculate_engagement_score_with_emojis(self, optimizer):
        """Test engagement score calculation with emojis"""
        content = "🚀 Bitcoin is mooning! 🌙 What do you think? 🤔"
        hashtags = ["#Bitcoin"]
        topics = ["Bitcoin"]
        
        score = optimizer.calculate_engagement_score(content, hashtags, topics)
        assert score > 0.3  # Should get points for emojis and question
    
    def test_calculate_engagement_score_with_question(self, optimizer):
        """Test engagement score calculation with question"""
        content = "Bitcoin price is rising. What are your thoughts?"
        hashtags = ["#Bitcoin"]
        topics = ["Bitcoin"]
        
        score = optimizer.calculate_engagement_score(content, hashtags, topics)
        assert score > 0.15  # Should get points for question
    
    def test_calculate_engagement_score_with_urgency(self, optimizer):
        """Test engagement score calculation with urgency words"""
        content = "BREAKING: Massive Bitcoin surge happening now!"
        hashtags = ["#Bitcoin"]
        topics = ["Bitcoin"]
        
        score = optimizer.calculate_engagement_score(content, hashtags, topics)
        assert score > 0.1  # Should get points for urgency
    
    def test_calculate_engagement_score_optimal_length(self, optimizer):
        """Test engagement score calculation with optimal length"""
        content = "Bitcoin price analysis: The recent surge indicates strong market sentiment and institutional adoption continues."
        hashtags = ["#Bitcoin"]
        topics = ["Bitcoin"]
        
        score = optimizer.calculate_engagement_score(content, hashtags, topics)
        assert score > 0.0  # Should get some points for optimal length
    
    def test_optimize_content_length_within_limit(self, optimizer):
        """Test content length optimization when within limit"""
        content = "Short content"
        hashtags = ["#Bitcoin", "#Crypto"]
        
        optimized_content, optimized_hashtags = optimizer.optimize_content_length(content, hashtags)
        
        assert optimized_content == content
        assert optimized_hashtags == hashtags
    
    def test_optimize_content_length_exceeds_limit(self, optimizer):
        """Test content length optimization when exceeding limit"""
        # Create content that exceeds 300 characters
        long_content = "This is a very long piece of content that definitely exceeds the maximum character limit for social media posts and needs to be truncated intelligently while preserving the most important information and maintaining readability for the audience who will be reading this post on their social media feeds."
        hashtags = ["#Bitcoin", "#Crypto", "#News"]
        
        optimized_content, optimized_hashtags = optimizer.optimize_content_length(long_content, hashtags)
        
        total_length = len(optimized_content) + len(" ".join(optimized_hashtags)) + 1
        assert total_length <= 300
        assert optimized_content.endswith("...")
    
    def test_optimize_content_length_reduce_hashtags(self, optimizer):
        """Test content length optimization reduces hashtags when needed"""
        content = "Medium length content that should fit but hashtags might make it too long for the character limit"
        hashtags = ["#Bitcoin", "#Ethereum", "#DeFi", "#NFT", "#Trading", "#Crypto", "#Blockchain"]
        
        optimized_content, optimized_hashtags = optimizer.optimize_content_length(content, hashtags)
        
        total_length = len(optimized_content) + len(" ".join(optimized_hashtags)) + 1
        assert total_length <= 300
        assert len(optimized_hashtags) <= len(hashtags)
    
    def test_smart_truncate_at_sentence_boundary(self, optimizer):
        """Test smart truncation at sentence boundaries"""
        content = "First sentence is short. Second sentence is much longer and contains more detailed information about the topic."
        max_length = 50
        
        truncated = optimizer._smart_truncate(content, max_length)
        
        assert len(truncated) <= max_length
        assert truncated.endswith("...")
        assert "First sentence is short" in truncated
    
    def test_smart_truncate_at_word_boundary(self, optimizer):
        """Test smart truncation at word boundaries"""
        content = "This is a single sentence without periods that needs to be truncated at word boundaries"
        max_length = 50
        
        truncated = optimizer._smart_truncate(content, max_length)
        
        assert len(truncated) <= max_length
        assert truncated.endswith("...")
        assert not truncated.replace("...", "").endswith(" ")  # No trailing space


class TestContentGenerationTool:
    """Test cases for ContentGenerationTool class"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return AgentConfig(
            max_post_length=300,
            min_engagement_score=0.7,
            content_themes=["Bitcoin", "Ethereum", "DeFi"]
        )
    
    @pytest.fixture
    def tool(self, config):
        """Create ContentGenerationTool instance"""
        return ContentGenerationTool(config)
    
    @pytest.fixture
    def sample_news_item(self):
        """Create sample news item for testing"""
        return NewsItem(
            headline="Bitcoin Surges to New All-Time High",
            summary="Bitcoin has reached a new all-time high of $75,000 amid institutional adoption and positive market sentiment.",
            source="CoinDesk",
            timestamp=datetime.now(),
            relevance_score=0.9,
            topics=["Bitcoin", "Trading", "Market"],
            url="https://example.com/news"
        )
    
    @pytest.fixture
    def sample_news_data(self, sample_news_item):
        """Create sample news data JSON"""
        return json.dumps({
            "success": True,
            "count": 1,
            "news_items": [sample_news_item.to_dict()]
        })
    
    def test_tool_initialization(self, tool, config):
        """Test tool initialization"""
        assert tool.name == "viral_content_generator"
        assert tool.config == config
        assert tool.optimizer is not None
        assert tool.strategies is not None
    
    def test_parse_news_data_valid_format(self, tool, sample_news_data):
        """Test parsing valid news data"""
        news_items = tool._parse_news_data(sample_news_data)
        
        assert len(news_items) == 1
        assert isinstance(news_items[0], NewsItem)
        assert news_items[0].headline == "Bitcoin Surges to New All-Time High"
    
    def test_parse_news_data_list_format(self, tool, sample_news_item):
        """Test parsing news data in list format"""
        news_data = json.dumps([sample_news_item.to_dict()])
        news_items = tool._parse_news_data(news_data)
        
        assert len(news_items) == 1
        assert isinstance(news_items[0], NewsItem)
    
    def test_parse_news_data_invalid_json(self, tool):
        """Test parsing invalid JSON"""
        invalid_json = "invalid json string"
        news_items = tool._parse_news_data(invalid_json)
        
        assert news_items == []
    
    def test_parse_news_data_empty_data(self, tool):
        """Test parsing empty news data"""
        empty_data = json.dumps({"success": True, "news_items": []})
        news_items = tool._parse_news_data(empty_data)
        
        assert news_items == []
    
    def test_analyze_sentiment_bullish(self, tool):
        """Test sentiment analysis for bullish content"""
        text = "Bitcoin surge rally bull market gains rise pump moon"
        sentiment = tool._analyze_sentiment(text)
        
        assert sentiment == "bullish"
    
    def test_analyze_sentiment_bearish(self, tool):
        """Test sentiment analysis for bearish content"""
        text = "Bitcoin crash dump bear market fall decline drop"
        sentiment = tool._analyze_sentiment(text)
        
        assert sentiment == "bearish"
    
    def test_analyze_sentiment_neutral(self, tool):
        """Test sentiment analysis for neutral content"""
        text = "Bitcoin price remains stable with moderate trading volume"
        sentiment = tool._analyze_sentiment(text)
        
        assert sentiment == "neutral"
    
    def test_extract_key_insight(self, tool):
        """Test key insight extraction"""
        summary = "Bitcoin has reached new highs. This indicates strong market sentiment. Institutional adoption continues to grow."
        insight = tool._extract_key_insight(summary)
        
        assert insight == "Bitcoin has reached new highs"
    
    def test_extract_key_insight_long_text(self, tool):
        """Test key insight extraction from long text"""
        long_summary = "A" * 150  # 150 character string
        insight = tool._extract_key_insight(long_summary)
        
        assert len(insight) <= 103  # 100 + "..."
        assert insight.endswith("...")
    
    def test_generate_news_content(self, tool, sample_news_item):
        """Test news content generation"""
        content = tool._generate_content_text(sample_news_item, "news")
        
        assert len(content) > 0
        assert any(hook.replace(":", "").strip() in content for hook in ViralContentStrategies.ENGAGEMENT_HOOKS)
    
    def test_generate_analysis_content(self, tool, sample_news_item):
        """Test analysis content generation"""
        content = tool._generate_content_text(sample_news_item, "analysis")
        
        assert len(content) > 0
        assert "💡 INSIGHT:" in content or "INSIGHT" in content
    
    def test_generate_opinion_content(self, tool, sample_news_item):
        """Test opinion content generation"""
        content = tool._generate_content_text(sample_news_item, "opinion")
        
        assert len(content) > 0
        assert "🔥 HOT TAKE:" in content or "HOT TAKE" in content
    
    def test_generate_market_update_content(self, tool, sample_news_item):
        """Test market update content generation"""
        content = tool._generate_content_text(sample_news_item, "market_update")
        
        assert len(content) > 0
        assert any(topic in content for topic in sample_news_item.topics)
    
    def test_run_successful_generation(self, tool, sample_news_data):
        """Test successful content generation"""
        result = tool._run(sample_news_data, "news", 0.7)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert "content" in result_data
        assert result_data["content"] is not None
        
        content = result_data["content"]
        assert "text" in content
        assert "hashtags" in content
        assert "engagement_score" in content
        assert len(content["text"]) <= 300
    
    def test_run_with_different_content_types(self, tool, sample_news_data):
        """Test content generation with different content types"""
        content_types = ["news", "analysis", "opinion", "market_update"]
        
        for content_type in content_types:
            result = tool._run(sample_news_data, content_type, 0.7)
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["content"]["content_type"] == content_type
    
    def test_run_with_high_target_engagement(self, tool, sample_news_data):
        """Test content generation with high target engagement"""
        result = tool._run(sample_news_data, "news", 0.9)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        # Should still generate content even if target is high
        assert result_data["content"] is not None
    
    def test_run_with_invalid_news_data(self, tool):
        """Test content generation with invalid news data"""
        invalid_data = "invalid json"
        result = tool._run(invalid_data, "news", 0.7)
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "error" in result_data
    
    def test_run_with_empty_news_data(self, tool):
        """Test content generation with empty news data"""
        empty_data = json.dumps({"success": True, "news_items": []})
        result = tool._run(empty_data, "news", 0.7)
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "error" in result_data
    
    def test_content_length_validation(self, tool, sample_news_data):
        """Test that generated content respects length limits"""
        result = tool._run(sample_news_data, "news", 0.7)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        content = result_data["content"]
        
        # Check total length including hashtags
        text_length = len(content["text"])
        hashtag_length = len(" ".join(content["hashtags"]))
        total_length = text_length + hashtag_length + (1 if content["hashtags"] else 0)
        
        assert total_length <= 300
    
    def test_hashtag_generation_quality(self, tool, sample_news_data):
        """Test quality of generated hashtags"""
        result = tool._run(sample_news_data, "news", 0.7)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        hashtags = result_data["content"]["hashtags"]
        
        assert len(hashtags) > 0
        assert len(hashtags) <= 3
        assert all(tag.startswith("#") for tag in hashtags)
        assert any("Bitcoin" in tag or "BTC" in tag for tag in hashtags)  # Should be relevant to news
    
    def test_engagement_score_calculation(self, tool, sample_news_data):
        """Test engagement score calculation"""
        result = tool._run(sample_news_data, "news", 0.7)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        engagement_score = result_data["content"]["engagement_score"]
        
        assert 0.0 <= engagement_score <= 1.0
        assert isinstance(engagement_score, float)
    
    def test_multiple_variations_generation(self, tool, sample_news_data):
        """Test that multiple variations are generated and best is selected"""
        result = tool._run(sample_news_data, "news", 0.7)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert "alternatives" in result_data
        
        # Should have generated alternatives (even if empty list)
        assert isinstance(result_data["alternatives"], list)


class TestContentGenerationToolFactory:
    """Test cases for factory function"""
    
    def test_create_content_generation_tool(self):
        """Test factory function creates tool correctly"""
        config = AgentConfig(max_post_length=300)
        tool = create_content_generation_tool(config)
        
        assert isinstance(tool, ContentGenerationTool)
        assert tool.config == config
        assert tool.name == "viral_content_generator"


class TestContentGenerationToolIntegration:
    """Integration tests for ContentGenerationTool"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return AgentConfig(
            max_post_length=300,
            min_engagement_score=0.7,
            content_themes=["Bitcoin", "Ethereum", "DeFi", "NFT"]
        )
    
    @pytest.fixture
    def tool(self, config):
        """Create ContentGenerationTool instance"""
        return ContentGenerationTool(config)
    
    def test_end_to_end_content_generation(self, tool):
        """Test complete end-to-end content generation workflow"""
        # Create realistic news data
        news_item = NewsItem(
            headline="Ethereum 2.0 Staking Rewards Reach Record High",
            summary="Ethereum 2.0 validators are earning record-high staking rewards as network activity surges. The annual percentage yield has increased to 8.5%, attracting more institutional investors to participate in staking.",
            source="The Block",
            timestamp=datetime.now(),
            relevance_score=0.85,
            topics=["Ethereum", "Staking", "DeFi"],
            url="https://example.com/eth-staking"
        )
        
        news_data = json.dumps({
            "success": True,
            "count": 1,
            "news_items": [news_item.to_dict()]
        })
        
        # Generate content
        result = tool._run(news_data, "analysis", 0.8)
        result_data = json.loads(result)
        
        # Verify complete workflow
        assert result_data["success"] is True
        
        content = result_data["content"]
        assert content["text"]
        assert content["hashtags"]
        assert content["engagement_score"] > 0
        assert content["content_type"] == "analysis"
        
        # Verify content quality
        text = content["text"]
        assert len(text) <= 300
        assert any(keyword in text.lower() for keyword in ["ethereum", "staking", "eth"])
        
        # Verify hashtags are relevant
        hashtags = content["hashtags"]
        assert any("Ethereum" in tag or "ETH" in tag for tag in hashtags)
        
        # Verify metadata
        assert "metadata" in content
        assert content["metadata"]["generation_strategy"] == "analysis"