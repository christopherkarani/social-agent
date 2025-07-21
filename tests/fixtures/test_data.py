# tests/fixtures/test_data.py
"""
Test data and fixtures for consistent testing
Provides reusable test data across all test modules
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import asdict

from src.models.data_models import NewsItem, GeneratedContent, PostResult, ContentType, AgentConfig


class TestDataFactory:
    """Factory for creating consistent test data"""
    
    @staticmethod
    def create_news_item(
        headline: str = "Bitcoin Reaches New All-Time High",
        summary: str = "Bitcoin price surged to unprecedented levels amid institutional adoption.",
        source: str = "CryptoNews",
        relevance_score: float = 0.9,
        topics: List[str] = None,
        url: str = "https://example.com/bitcoin-ath"
    ) -> NewsItem:
        """Create a NewsItem with default or custom values"""
        if topics is None:
            topics = ["Bitcoin", "Price", "ATH"]
        
        return NewsItem(
            headline=headline,
            summary=summary,
            source=source,
            timestamp=datetime.now(),
            relevance_score=relevance_score,
            topics=topics,
            url=url,
            raw_content=f"{headline} {summary}"
        )
    
    @staticmethod
    def create_generated_content(
        text: str = "🚀 Bitcoin just hit a new all-time high! Institutional adoption is driving unprecedented growth. #Bitcoin #Crypto #ATH",
        hashtags: List[str] = None,
        engagement_score: float = 0.85,
        content_type: ContentType = ContentType.NEWS,
        source_news: NewsItem = None
    ) -> GeneratedContent:
        """Create a GeneratedContent with default or custom values"""
        if hashtags is None:
            hashtags = ["#Bitcoin", "#Crypto", "#ATH"]
        
        if source_news is None:
            source_news = TestDataFactory.create_news_item()
        
        return GeneratedContent(
            text=text,
            hashtags=hashtags,
            engagement_score=engagement_score,
            content_type=content_type,
            source_news=source_news,
            created_at=datetime.now()
        )
    
    @staticmethod
    def create_post_result(
        success: bool = True,
        post_id: str = "at://did:plc:test123/app.bsky.feed.post/test456",
        content: GeneratedContent = None,
        error_message: str = None,
        retry_count: int = 0
    ) -> PostResult:
        """Create a PostResult with default or custom values"""
        if content is None:
            content = TestDataFactory.create_generated_content()
        
        return PostResult(
            success=success,
            post_id=post_id if success else None,
            timestamp=datetime.now(),
            content=content,
            error_message=error_message,
            retry_count=retry_count
        )
    
    @staticmethod
    def create_agent_config(
        perplexity_api_key: str = "test_perplexity_key",
        bluesky_username: str = "test_user",
        bluesky_password: str = "test_password",
        content_themes: List[str] = None
    ) -> AgentConfig:
        """Create an AgentConfig with default or custom values"""
        if content_themes is None:
            content_themes = ["Bitcoin", "Ethereum", "DeFi"]
        
        return AgentConfig(
            perplexity_api_key=perplexity_api_key,
            bluesky_username=bluesky_username,
            bluesky_password=bluesky_password,
            posting_interval_minutes=30,
            max_execution_time_minutes=25,
            max_post_length=300,
            content_themes=content_themes,
            min_engagement_score=0.7,
            duplicate_threshold=0.8,
            max_retries=3
        )


class TestScenarios:
    """Pre-defined test scenarios for common testing patterns"""
    
    @staticmethod
    def get_successful_workflow_scenario() -> Dict[str, Any]:
        """Complete successful workflow scenario"""
        news_item = TestDataFactory.create_news_item()
        generated_content = TestDataFactory.create_generated_content(source_news=news_item)
        post_result = TestDataFactory.create_post_result(content=generated_content)
        
        return {
            "news_data": {
                "success": True,
                "count": 1,
                "news_items": [news_item.to_dict()]
            },
            "content_data": {
                "success": True,
                "content": {
                    "text": generated_content.text,
                    "hashtags": generated_content.hashtags,
                    "engagement_score": generated_content.engagement_score,
                    "content_type": generated_content.content_type.value,
                    "source_news": generated_content.source_news.to_dict(),
                    "created_at": generated_content.created_at.isoformat()
                }
            },
            "post_result": {
                "success": True,
                "post_id": post_result.post_id,
                "timestamp": post_result.timestamp.isoformat(),
                "retry_count": 0
            },
            "expected_result": post_result
        }
    
    @staticmethod
    def get_news_retrieval_failure_scenario() -> Dict[str, Any]:
        """News retrieval failure scenario"""
        return {
            "news_data": {
                "success": False,
                "count": 0,
                "news_items": [],
                "error": "API rate limit exceeded"
            },
            "expected_error": "Failed to retrieve news data"
        }
    
    @staticmethod
    def get_content_generation_failure_scenario() -> Dict[str, Any]:
        """Content generation failure scenario"""
        news_item = TestDataFactory.create_news_item()
        
        return {
            "news_data": {
                "success": True,
                "count": 1,
                "news_items": [news_item.to_dict()]
            },
            "content_data": {
                "success": False,
                "error": "Content generation model unavailable"
            },
            "expected_error": "Failed to generate content"
        }
    
    @staticmethod
    def get_content_filtering_scenario() -> Dict[str, Any]:
        """Content filtering scenario with low-quality content"""
        news_item = TestDataFactory.create_news_item()
        low_quality_content = TestDataFactory.create_generated_content(
            text="Buy crypto now! Moon! 🚀🚀🚀",  # Low quality content
            engagement_score=0.3,  # Below threshold
            source_news=news_item
        )
        
        return {
            "news_data": {
                "success": True,
                "count": 1,
                "news_items": [news_item.to_dict()]
            },
            "content_data": {
                "success": True,
                "content": {
                    "text": low_quality_content.text,
                    "hashtags": low_quality_content.hashtags,
                    "engagement_score": low_quality_content.engagement_score,
                    "content_type": low_quality_content.content_type.value,
                    "source_news": low_quality_content.source_news.to_dict(),
                    "created_at": low_quality_content.created_at.isoformat()
                }
            },
            "expected_error": "Content filtered out"
        }
    
    @staticmethod
    def get_posting_failure_scenario() -> Dict[str, Any]:
        """Posting failure scenario"""
        news_item = TestDataFactory.create_news_item()
        generated_content = TestDataFactory.create_generated_content(source_news=news_item)
        
        return {
            "news_data": {
                "success": True,
                "count": 1,
                "news_items": [news_item.to_dict()]
            },
            "content_data": {
                "success": True,
                "content": {
                    "text": generated_content.text,
                    "hashtags": generated_content.hashtags,
                    "engagement_score": generated_content.engagement_score,
                    "content_type": generated_content.content_type.value,
                    "source_news": generated_content.source_news.to_dict(),
                    "created_at": generated_content.created_at.isoformat()
                }
            },
            "post_result": {
                "success": False,
                "post_id": None,
                "error_message": "Authentication failed",
                "retry_count": 2
            },
            "expected_error": "Authentication failed"
        }


class CryptoNewsDatasets:
    """Realistic cryptocurrency news datasets for testing"""
    
    @staticmethod
    def get_bitcoin_news_dataset() -> List[Dict[str, Any]]:
        """Bitcoin-focused news dataset"""
        return [
            {
                "headline": "Bitcoin Adoption Accelerates Among Fortune 500 Companies",
                "summary": "Major corporations continue to add Bitcoin to their treasury reserves, signaling growing institutional confidence in cryptocurrency as a store of value.",
                "source": "CryptoInstitutional",
                "timestamp": datetime.now().isoformat(),
                "relevance_score": 0.92,
                "topics": ["Bitcoin", "Institutional", "Adoption"],
                "url": "https://example.com/bitcoin-fortune500",
                "raw_content": "Bitcoin adoption Fortune 500 companies treasury reserves institutional confidence"
            },
            {
                "headline": "Bitcoin Mining Difficulty Reaches All-Time High",
                "summary": "Network security strengthens as mining difficulty adjustment reflects increased computational power securing the Bitcoin blockchain.",
                "source": "MiningNews",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "relevance_score": 0.78,
                "topics": ["Bitcoin", "Mining", "Network"],
                "url": "https://example.com/bitcoin-mining-difficulty",
                "raw_content": "Bitcoin mining difficulty all-time high network security computational power"
            },
            {
                "headline": "Bitcoin Lightning Network Capacity Surpasses 5000 BTC",
                "summary": "Layer 2 scaling solution demonstrates growing adoption with record capacity and channel count supporting instant payments.",
                "source": "LightningReport",
                "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
                "relevance_score": 0.85,
                "topics": ["Bitcoin", "Lightning", "Scaling"],
                "url": "https://example.com/lightning-capacity",
                "raw_content": "Bitcoin Lightning Network capacity 5000 BTC layer 2 scaling instant payments"
            }
        ]
    
    @staticmethod
    def get_ethereum_news_dataset() -> List[Dict[str, Any]]:
        """Ethereum-focused news dataset"""
        return [
            {
                "headline": "Ethereum Layer 2 Solutions See Record Transaction Volume",
                "summary": "Ethereum scaling solutions process unprecedented transaction volumes as DeFi and NFT activity continues to grow across the ecosystem.",
                "source": "EthereumDaily",
                "timestamp": datetime.now().isoformat(),
                "relevance_score": 0.88,
                "topics": ["Ethereum", "Layer2", "DeFi", "Scaling"],
                "url": "https://example.com/ethereum-l2-volume",
                "raw_content": "Ethereum Layer 2 solutions record transaction volume DeFi NFT activity ecosystem"
            },
            {
                "headline": "Ethereum Staking Rewards Increase Following Network Upgrade",
                "summary": "Validator rewards see improvement after successful implementation of network enhancements, boosting staking participation rates.",
                "source": "StakingNews",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "relevance_score": 0.82,
                "topics": ["Ethereum", "Staking", "Rewards", "Upgrade"],
                "url": "https://example.com/ethereum-staking-rewards",
                "raw_content": "Ethereum staking rewards increase network upgrade validator participation"
            },
            {
                "headline": "Major DeFi Protocol Launches on Ethereum Mainnet",
                "summary": "New decentralized finance protocol brings innovative yield farming strategies and liquidity solutions to the Ethereum ecosystem.",
                "source": "DeFiWatch",
                "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
                "relevance_score": 0.79,
                "topics": ["Ethereum", "DeFi", "Protocol", "Yield"],
                "url": "https://example.com/defi-protocol-launch",
                "raw_content": "DeFi protocol launches Ethereum mainnet yield farming liquidity solutions"
            }
        ]
    
    @staticmethod
    def get_mixed_crypto_news_dataset() -> List[Dict[str, Any]]:
        """Mixed cryptocurrency news dataset"""
        bitcoin_news = CryptoNewsDatasets.get_bitcoin_news_dataset()
        ethereum_news = CryptoNewsDatasets.get_ethereum_news_dataset()
        
        additional_news = [
            {
                "headline": "Central Bank Digital Currency Pilots Expand Globally",
                "summary": "Multiple central banks advance CBDC development programs, exploring digital currency implementations for national payment systems.",
                "source": "CBDCWatch",
                "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(),
                "relevance_score": 0.75,
                "topics": ["CBDC", "Central Banks", "Digital Currency"],
                "url": "https://example.com/cbdc-pilots",
                "raw_content": "Central Bank Digital Currency CBDC pilots global development programs"
            },
            {
                "headline": "NFT Marketplace Volume Rebounds After Market Correction",
                "summary": "Non-fungible token trading activity shows signs of recovery with increased collector interest and new platform features.",
                "source": "NFTMarket",
                "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
                "relevance_score": 0.71,
                "topics": ["NFT", "Marketplace", "Trading"],
                "url": "https://example.com/nft-volume-rebound",
                "raw_content": "NFT marketplace volume rebounds market correction trading activity recovery"
            }
        ]
        
        # Combine and sort by timestamp (newest first)
        all_news = bitcoin_news + ethereum_news + additional_news
        all_news.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return all_news


class ContentGenerationTemplates:
    """Templates for testing content generation scenarios"""
    
    @staticmethod
    def get_high_engagement_templates() -> List[str]:
        """Templates that should generate high engagement scores"""
        return [
            "🚀 {headline} - This could be a game-changer for the crypto market! What are your thoughts? {hashtags}",
            "📈 Breaking: {headline}. The implications for institutional adoption are huge! {hashtags}",
            "💡 Major development: {headline}. This is why I'm bullish on crypto long-term! {hashtags}",
            "🔥 Hot take: {headline}. Smart money is definitely paying attention to this! {hashtags}"
        ]
    
    @staticmethod
    def get_medium_engagement_templates() -> List[str]:
        """Templates that should generate medium engagement scores"""
        return [
            "📊 Update: {headline}. Interesting developments in the crypto space. {hashtags}",
            "💭 Thoughts on this: {headline}. What do you think this means? {hashtags}",
            "📰 News: {headline}. Worth keeping an eye on. {hashtags}",
            "🤔 Analysis: {headline}. The crypto market keeps evolving. {hashtags}"
        ]
    
    @staticmethod
    def get_low_engagement_templates() -> List[str]:
        """Templates that should generate low engagement scores (for filtering tests)"""
        return [
            "Buy crypto now! {headline} Moon! 🚀🚀🚀",
            "Guaranteed profits! {headline} Don't miss out!",
            "{headline} To the moon! Lambo time!",
            "URGENT: {headline} Buy buy buy!"
        ]
    
    @staticmethod
    def generate_content_from_template(template: str, news_item: NewsItem) -> str:
        """Generate content using a template and news item"""
        hashtags = " ".join([f"#{topic.lower().replace(' ', '')}" for topic in news_item.topics[:3]])
        
        return template.format(
            headline=news_item.headline[:100],  # Truncate long headlines
            hashtags=hashtags
        )


class APIResponseMocks:
    """Mock API responses for consistent testing"""
    
    @staticmethod
    def get_perplexity_success_response(news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock successful Perplexity API response"""
        content_parts = []
        for item in news_items:
            content_parts.append(f"**{item['headline']}**")
            content_parts.append(item['summary'])
            content_parts.append("")  # Empty line separator
        
        return {
            "choices": [{
                "message": {
                    "content": "\n".join(content_parts)
                }
            }],
            "citations": [
                {
                    "title": item['source'],
                    "url": item.get('url', f"https://example.com/{i}")
                }
                for i, item in enumerate(news_items)
            ]
        }
    
    @staticmethod
    def get_perplexity_error_response(error_message: str = "API rate limit exceeded") -> Exception:
        """Mock Perplexity API error response"""
        return Exception(error_message)
    
    @staticmethod
    def get_bluesky_success_response(post_id: str = None) -> Dict[str, Any]:
        """Mock successful Bluesky API response"""
        if post_id is None:
            post_id = f"at://did:plc:test123/app.bsky.feed.post/{int(datetime.now().timestamp())}"
        
        return {
            "success": True,
            "post_id": post_id,
            "cid": f"cid_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0
        }
    
    @staticmethod
    def get_bluesky_error_response(error_message: str = "Authentication failed") -> Dict[str, Any]:
        """Mock Bluesky API error response"""
        return {
            "success": False,
            "post_id": None,
            "error_message": error_message,
            "retry_count": 2,
            "timestamp": datetime.now().isoformat()
        }


# Export commonly used test data for easy imports
DEFAULT_NEWS_ITEM = TestDataFactory.create_news_item()
DEFAULT_GENERATED_CONTENT = TestDataFactory.create_generated_content()
DEFAULT_POST_RESULT = TestDataFactory.create_post_result()
DEFAULT_AGENT_CONFIG = TestDataFactory.create_agent_config()

# Export datasets
BITCOIN_NEWS_DATASET = CryptoNewsDatasets.get_bitcoin_news_dataset()
ETHEREUM_NEWS_DATASET = CryptoNewsDatasets.get_ethereum_news_dataset()
MIXED_CRYPTO_NEWS_DATASET = CryptoNewsDatasets.get_mixed_crypto_news_dataset()

# Export scenarios
SUCCESSFUL_WORKFLOW_SCENARIO = TestScenarios.get_successful_workflow_scenario()
NEWS_FAILURE_SCENARIO = TestScenarios.get_news_retrieval_failure_scenario()
CONTENT_FAILURE_SCENARIO = TestScenarios.get_content_generation_failure_scenario()
FILTERING_SCENARIO = TestScenarios.get_content_filtering_scenario()
POSTING_FAILURE_SCENARIO = TestScenarios.get_posting_failure_scenario()