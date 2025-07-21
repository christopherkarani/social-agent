# tests/test_integration.py
"""
Integration tests for the Bluesky crypto agent components
"""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.config.agent_config import AgentConfig
from src.models.data_models import NewsItem, GeneratedContent, ContentType
from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.services.content_filter import ContentFilter


class TestIntegration:
    """Integration tests for component interaction"""
    
    def test_agent_initialization_with_config(self):
        """Test that the agent can be initialized with a valid configuration"""
        config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_pass"
        )
        
        # Mock LLM for testing
        mock_llm = Mock()
        
        agent = BlueskyCryptoAgent(llm=mock_llm, config=config)
        
        assert agent.config == config
        assert agent.content_history == []
        assert isinstance(agent.content_filter, ContentFilter)
    
    def test_content_filter_with_generated_content(self):
        """Test content filter with generated content objects"""
        content_filter = ContentFilter()
        
        # Create sample news item
        news_item = NewsItem(
            headline="Bitcoin Surges",
            summary="Bitcoin price increases significantly",
            source="CryptoNews",
            timestamp=datetime.now(),
            relevance_score=0.9,
            topics=["Bitcoin", "Price"]
        )
        
        # Create generated content (longer text to pass quality check)
        content = GeneratedContent(
            text="Bitcoin is going to the moon! 🚀 This is amazing news for crypto investors and the entire ecosystem. #Bitcoin #Crypto",
            hashtags=["#Bitcoin", "#Crypto"],
            engagement_score=0.8,
            content_type=ContentType.NEWS,
            source_news=news_item
        )
        
        # Create better quality content (original content has "moon" which is a negative quality indicator)
        better_content = GeneratedContent(
            text="Bitcoin technical analysis shows strong development trends and increasing institutional adoption across the cryptocurrency ecosystem. #Bitcoin #Crypto",
            hashtags=["#Bitcoin", "#Crypto"],
            engagement_score=0.8,
            content_type=ContentType.ANALYSIS,
            source_news=news_item
        )
        
        # Test comprehensive content filtering
        approved, details = content_filter.filter_content(better_content)
        content = better_content
        
        assert approved is True
        assert details['scores']['quality'] > 0.6
        
        # Test duplicate detection (should be False for first content)
        is_duplicate, similarity = content_filter._check_duplicates(content.text)
        assert is_duplicate is False
        
        # Add to history
        content_filter.add_to_history(content)
        
        # Test duplicate detection (should be True for same content)
        is_duplicate, similarity = content_filter._check_duplicates(content.text)
        assert is_duplicate is True
    
    def test_agent_content_history_management(self):
        """Test that agent properly manages content history"""
        config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_pass"
        )
        
        mock_llm = Mock()
        agent = BlueskyCryptoAgent(llm=mock_llm, config=config)
        
        # Create sample content
        news_item = NewsItem(
            headline="Ethereum Update",
            summary="Ethereum network upgrade completed",
            source="EthNews",
            timestamp=datetime.now(),
            relevance_score=0.85,
            topics=["Ethereum", "Upgrade"]
        )
        
        content = GeneratedContent(
            text="Ethereum upgrade is live! Great news for the ecosystem. #Ethereum #DeFi",
            hashtags=["#Ethereum", "#DeFi"],
            engagement_score=0.9,
            content_type=ContentType.NEWS,
            source_news=news_item
        )
        
        # Add content to history
        agent.add_to_history(content)
        
        assert len(agent.content_history) == 1
        assert agent.content_history[0] == content
    
    def test_config_validation_integration(self):
        """Test configuration validation in context of agent usage"""
        # Test valid configuration
        valid_config = AgentConfig(
            perplexity_api_key="valid_key",
            bluesky_username="valid_user",
            bluesky_password="valid_pass",
            content_themes=["Bitcoin", "Ethereum", "DeFi"]
        )
        
        assert valid_config.validate() is True
        
        # Test that agent can be created with valid config
        mock_llm = Mock()
        agent = BlueskyCryptoAgent(llm=mock_llm, config=valid_config)
        assert agent.config.content_themes == ["Bitcoin", "Ethereum", "DeFi"]
        
        # Test invalid configuration
        invalid_config = AgentConfig(
            # Missing required API keys
            content_themes=[]  # Empty themes
        )
        
        assert invalid_config.validate() is False