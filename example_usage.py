#!/usr/bin/env python3
"""
Example usage of the Bluesky Crypto Agent components
"""
import os
from datetime import datetime
from unittest.mock import Mock

from src.config.agent_config import AgentConfig
from src.models.data_models import NewsItem, GeneratedContent, ContentType
from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.services.content_filter import ContentFilter


def main():
    """Demonstrate the Bluesky crypto agent components"""
    print("🚀 Bluesky Crypto Agent - Component Demo")
    print("=" * 50)
    
    # 1. Configuration Management
    print("\n1. Configuration Management:")
    print("-" * 30)
    
    # Create configuration from environment variables (with defaults)
    config = AgentConfig.from_env()
    print(f"✅ Configuration loaded with {len(config.content_themes)} themes")
    print(f"   Posting interval: {config.posting_interval_minutes} minutes")
    print(f"   Content themes: {', '.join(config.content_themes[:3])}...")
    
    # Validate configuration
    is_valid = config.validate()
    print(f"   Configuration valid: {'✅' if is_valid else '❌'}")
    if not is_valid:
        print("   ⚠️  Missing API keys - set PERPLEXITY_API_KEY, BLUESKY_USERNAME, BLUESKY_PASSWORD")
    
    # 2. Data Models
    print("\n2. Data Models:")
    print("-" * 30)
    
    # Create a sample news item
    news_item = NewsItem(
        headline="Bitcoin Reaches New All-Time High Above $100,000",
        summary="Bitcoin has surged past $100,000 for the first time in history, driven by institutional adoption and regulatory clarity.",
        source="CryptoDaily",
        timestamp=datetime.now(),
        relevance_score=0.95,
        topics=["Bitcoin", "Price", "ATH", "Institutional"],
        url="https://example.com/bitcoin-100k"
    )
    print(f"✅ NewsItem created: {news_item.headline[:50]}...")
    print(f"   Relevance score: {news_item.relevance_score}")
    print(f"   Topics: {', '.join(news_item.topics)}")
    
    # Create generated content
    generated_content = GeneratedContent(
        text="🚨 BREAKING: Bitcoin just smashed through $100K! This is the moment we've all been waiting for. The institutional wave is real and it's just getting started. #Bitcoin #100K #Crypto #BullRun",
        hashtags=["#Bitcoin", "#100K", "#Crypto", "#BullRun"],
        engagement_score=0.92,
        content_type=ContentType.NEWS,
        source_news=news_item
    )
    print(f"✅ GeneratedContent created: {generated_content.character_count} characters")
    print(f"   Engagement score: {generated_content.engagement_score}")
    print(f"   Content type: {generated_content.content_type.value}")
    
    # 3. Content Filtering
    print("\n3. Content Filtering:")
    print("-" * 30)
    
    content_filter = ContentFilter()
    
    # Test content filtering
    filter_result, filter_details = content_filter.filter_content(generated_content)
    print(f"✅ Content filter passed: {'✅' if filter_result else '❌'}")
    print(f"   Quality score: {filter_details['scores'].get('quality', 0):.2f}")
    print(f"   Similarity score: {filter_details['scores'].get('similarity', 0):.2f}")
    
    # Add to history and test duplicate detection
    if filter_result:
        content_filter.add_to_history(generated_content)
        print(f"   Content added to history")
        
        # Test duplicate detection with same content
        duplicate_result, duplicate_details = content_filter.filter_content(generated_content)
        print(f"   Duplicate check: {'❌ Duplicate' if not duplicate_result else '✅ Original'}")
    
    # Show history stats
    history_stats = content_filter.get_history_stats()
    print(f"   History stats: {history_stats['total_items']} items, avg engagement: {history_stats['avg_engagement_score']}")
    
    # 4. Agent Initialization
    print("\n4. Agent Initialization:")
    print("-" * 30)
    
    # Create mock LLM for demo
    mock_llm = Mock()
    mock_llm.name = "MockLLM"
    
    # Initialize agent
    agent = BlueskyCryptoAgent(llm=mock_llm, config=config)
    print(f"✅ BlueskyCryptoAgent initialized")
    print(f"   Content history size: {len(agent.content_history)}")
    print(f"   Configuration themes: {len(agent.config.content_themes)}")
    
    # Add content to agent history
    agent.add_to_history(generated_content)
    print(f"   Content added to history: {len(agent.content_history)} items")
    
    # 5. Configuration Export
    print("\n5. Configuration Export:")
    print("-" * 30)
    
    config_dict = config.to_dict()
    print("✅ Configuration exported to dictionary:")
    for key, value in config_dict.items():
        if key in ['perplexity_api_key', 'bluesky_password']:
            continue  # Skip sensitive data
        if isinstance(value, list):
            print(f"   {key}: [{len(value)} items]")
        else:
            print(f"   {key}: {value}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed successfully!")
    print("\nNext steps:")
    print("- Set environment variables for API keys")
    print("- Run tests: python -m pytest tests/ -v")
    print("- Implement remaining tasks from the specification")


if __name__ == "__main__":
    main()