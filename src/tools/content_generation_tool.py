# src/tools/content_generation_tool.py
"""
ContentGenerationTool - AI-powered content generation tool for creating viral crypto social media posts
"""
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import asdict

from langchain.tools import Tool
from pydantic import BaseModel, Field, PrivateAttr

from ..models.data_models import NewsItem, GeneratedContent, ContentType
from ..config.agent_config import AgentConfig
from ..services.ab_testing_framework import ContentStrategy

logger = logging.getLogger(__name__)


class ContentGenerationInput(BaseModel):
    """Input schema for ContentGenerationTool"""
    news_data: str = Field(description="JSON string containing news data to generate content from")
    content_type: str = Field(default="news", description="Type of content to generate: news, analysis, opinion, market_update")
    target_engagement: float = Field(default=0.8, description="Target engagement score (0.0-1.0)")


class ViralContentStrategies:
    """
    Collection of viral content generation strategies for crypto social media
    """
    
    ENGAGEMENT_HOOKS = [
        "🚨 BREAKING:",
        "🔥 HOT TAKE:",
        "💡 INSIGHT:",
        "⚡ QUICK UPDATE:",
        "🎯 PREDICTION:",
        "📈 BULLISH:",
        "📉 BEARISH:",
        "🤔 THOUGHTS:",
        "💰 OPPORTUNITY:",
        "⚠️ WARNING:",
    ]
    
    VIRAL_TEMPLATES = {
        "breaking_news": [
            "{hook} {headline} - {key_insight} {hashtags}",
            "{hook} {headline}. This could mean {implication}. {hashtags}",
            "{hook} {headline}! {reaction} {hashtags}",
        ],
        "analysis": [
            "{hook} {key_point}. Here's why this matters: {explanation} {hashtags}",
            "Everyone's talking about {topic}, but here's what they're missing: {insight} {hashtags}",
            "{hook} {analysis}. The implications are huge. {hashtags}",
        ],
        "opinion": [
            "{hook} Unpopular opinion - {opinion}. {reasoning} {hashtags}",
            "Hot take: {opinion}. {justification} Thoughts? {hashtags}",
            "{hook} {controversial_statement}. Change my mind. {hashtags}",
        ],
        "market_update": [
            "{hook} {asset} is {movement}! {context} {hashtags}",
            "Market update: {summary}. {implication} {hashtags}",
            "{hook} {price_action}. {analysis} What's your take? {hashtags}",
        ]
    }
    
    CRYPTO_HASHTAGS = {
        "bitcoin": ["#Bitcoin", "#BTC", "#DigitalGold"],
        "ethereum": ["#Ethereum", "#ETH", "#SmartContracts"],
        "defi": ["#DeFi", "#DecentralizedFinance", "#YieldFarming"],
        "nft": ["#NFT", "#NFTs", "#DigitalArt"],
        "altcoin": ["#Altcoins", "#Crypto", "#Blockchain"],
        "trading": ["#CryptoTrading", "#TradingView", "#TechnicalAnalysis"],
        "general": ["#Crypto", "#Blockchain", "#Web3", "#HODL", "#ToTheMoon"]
    }
    
    @classmethod
    def get_engagement_hook(cls, content_type: str, sentiment: str = "neutral") -> str:
        """Get an appropriate engagement hook based on content type and sentiment"""
        if content_type == "breaking_news":
            return "🚨 BREAKING:"
        elif content_type == "analysis":
            return "💡 INSIGHT:"
        elif content_type == "opinion":
            return "🔥 HOT TAKE:"
        elif sentiment == "bullish":
            return "📈 BULLISH:"
        elif sentiment == "bearish":
            return "📉 BEARISH:"
        else:
            return "⚡ QUICK UPDATE:"
    
    @classmethod
    def get_relevant_hashtags(cls, topics: List[str], max_hashtags: int = 3) -> List[str]:
        """Get relevant hashtags based on content topics"""
        hashtags = set()
        
        for topic in topics:
            topic_lower = topic.lower()
            
            # Map topics to hashtag categories
            if any(keyword in topic_lower for keyword in ["bitcoin", "btc"]):
                hashtags.update(cls.CRYPTO_HASHTAGS["bitcoin"][:2])
            elif any(keyword in topic_lower for keyword in ["ethereum", "eth"]):
                hashtags.update(cls.CRYPTO_HASHTAGS["ethereum"][:2])
            elif "defi" in topic_lower:
                hashtags.update(cls.CRYPTO_HASHTAGS["defi"][:2])
            elif "nft" in topic_lower:
                hashtags.update(cls.CRYPTO_HASHTAGS["nft"][:2])
            elif any(keyword in topic_lower for keyword in ["trading", "price", "market"]):
                hashtags.update(cls.CRYPTO_HASHTAGS["trading"][:2])
            else:
                hashtags.update(cls.CRYPTO_HASHTAGS["general"][:1])
        
        # Ensure we have at least some general hashtags
        if not hashtags:
            hashtags.update(cls.CRYPTO_HASHTAGS["general"][:2])
        
        # Limit to max_hashtags
        return list(hashtags)[:max_hashtags]


class ContentOptimizer:
    """
    Content optimization engine for maximizing engagement
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.max_length = config.max_post_length
    
    def calculate_engagement_score(self, content: str, hashtags: List[str], topics: List[str]) -> float:
        """
        Calculate predicted engagement score based on content characteristics
        """
        score = 0.0
        content_lower = content.lower()
        
        # Hook presence (0.2 points)
        if any(hook.lower().replace(":", "").replace("🚨", "").replace("🔥", "").strip() in content_lower 
               for hook in ViralContentStrategies.ENGAGEMENT_HOOKS):
            score += 0.2
        
        # Emoji usage (0.15 points)
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content))
        score += min(emoji_count * 0.05, 0.15)
        
        # Question or call-to-action (0.15 points)
        if any(phrase in content_lower for phrase in ["?", "thoughts?", "what do you think", "change my mind"]):
            score += 0.15
        
        # Urgency/excitement words (0.1 points)
        urgency_words = ["breaking", "huge", "massive", "incredible", "shocking", "urgent", "now", "today"]
        if any(word in content_lower for word in urgency_words):
            score += 0.1
        
        # Hashtag relevance (0.2 points)
        if hashtags:
            relevant_hashtags = sum(1 for tag in hashtags if any(topic.lower() in tag.lower() for topic in topics))
            score += min(relevant_hashtags * 0.1, 0.2)
        
        # Content length optimization (0.1 points)
        # Optimal length is 100-200 characters for engagement
        if 100 <= len(content) <= 200:
            score += 0.1
        elif 80 <= len(content) <= 250:
            score += 0.05
        
        # Controversy/opinion indicators (0.1 points)
        opinion_indicators = ["unpopular opinion", "hot take", "controversial", "disagree", "wrong"]
        if any(indicator in content_lower for indicator in opinion_indicators):
            score += 0.1
        
        return min(score, 1.0)
    
    def optimize_content_length(self, content: str, hashtags: List[str]) -> Tuple[str, List[str]]:
        """
        Optimize content length while preserving key information
        """
        hashtag_text = " " + " ".join(hashtags) if hashtags else ""
        total_length = len(content) + len(hashtag_text)
        
        if total_length <= self.max_length:
            return content, hashtags
        
        # Calculate available space for content
        available_space = self.max_length - len(hashtag_text) - 5  # 5 char buffer
        
        if available_space < 50:  # Too little space, reduce hashtags
            hashtags = hashtags[:2] if len(hashtags) > 2 else hashtags
            hashtag_text = " " + " ".join(hashtags) if hashtags else ""
            available_space = self.max_length - len(hashtag_text) - 5
        
        if len(content) > available_space:
            # Truncate content intelligently
            content = self._smart_truncate(content, available_space)
        
        return content, hashtags
    
    def _smart_truncate(self, content: str, max_length: int) -> str:
        """
        Intelligently truncate content while preserving meaning
        """
        if len(content) <= max_length:
            return content
        
        # Try to truncate at sentence boundary
        sentences = content.split('. ')
        if len(sentences) > 1:
            truncated = sentences[0]
            for sentence in sentences[1:]:
                if len(truncated + '. ' + sentence) <= max_length - 3:  # 3 for "..."
                    truncated += '. ' + sentence
                else:
                    break
            if len(truncated) < max_length - 3:
                return truncated + "..."
        
        # Truncate at word boundary
        words = content.split()
        truncated = ""
        for word in words:
            if len(truncated + " " + word) <= max_length - 3:
                truncated += " " + word if truncated else word
            else:
                break
        
        return truncated.strip() + "..."


class ContentGenerationTool(Tool):
    """
    LangChain tool for generating viral cryptocurrency social media content
    """
    
    _config: AgentConfig = PrivateAttr()
    _optimizer: ContentOptimizer = PrivateAttr()
    _strategies: ViralContentStrategies = PrivateAttr()
    
    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__(
            name="viral_content_generator",
            description="Generates engaging social media content from cryptocurrency news with viral optimization",
            func=self._run,
            args_schema=ContentGenerationInput,
            **kwargs
        )
        self._config = config
        self._optimizer = ContentOptimizer(config)
        self._strategies = ViralContentStrategies()
    
    @property
    def config(self) -> AgentConfig:
        return self._config
    
    @property
    def optimizer(self) -> ContentOptimizer:
        return self._optimizer
    
    @property
    def strategies(self) -> ViralContentStrategies:
        return self._strategies
    
    def _run(self, news_data: str, content_type: str = "news", target_engagement: float = 0.8) -> str:
        """
        Generate viral content from news data
        
        Args:
            news_data: JSON string containing news items
            content_type: Type of content to generate
            target_engagement: Target engagement score
            
        Returns:
            JSON string containing generated content data
        """
        try:
            logger.info(f"Generating {content_type} content with target engagement {target_engagement}")
            
            # Parse input news data
            news_items = self._parse_news_data(news_data)
            if not news_items:
                return self._create_error_result("No valid news items found in input data")
            
            # Select the most relevant news item
            primary_news = max(news_items, key=lambda x: x.relevance_score)
            
            # Generate content based on type
            generated_contents = []
            
            # Generate multiple variations and select the best
            for _ in range(3):  # Generate 3 variations
                content_text = self._generate_content_text(primary_news, content_type)
                hashtags = self.strategies.get_relevant_hashtags(primary_news.topics)
                
                # Optimize content length
                optimized_text, optimized_hashtags = self.optimizer.optimize_content_length(content_text, hashtags)
                
                # Calculate engagement score
                engagement_score = self.optimizer.calculate_engagement_score(
                    optimized_text, optimized_hashtags, primary_news.topics
                )
                
                # Create GeneratedContent object
                generated_content = GeneratedContent(
                    text=optimized_text,
                    hashtags=optimized_hashtags,
                    engagement_score=engagement_score,
                    content_type=ContentType(content_type),
                    source_news=primary_news,
                    metadata={
                        "generation_strategy": content_type,
                        "target_engagement": target_engagement,
                        "original_length": len(content_text),
                        "optimized_length": len(optimized_text)
                    }
                )
                
                generated_contents.append(generated_content)
            
            # Select the best content based on engagement score
            best_content = max(generated_contents, key=lambda x: x.engagement_score)
            
            # Check if it meets the target engagement threshold
            if best_content.engagement_score < target_engagement:
                logger.warning(f"Generated content engagement score ({best_content.engagement_score:.2f}) below target ({target_engagement})")
            
            logger.info(f"Generated content with engagement score: {best_content.engagement_score:.2f}")
            
            return json.dumps({
                "success": True,
                "content": best_content.to_dict(),
                "alternatives": [content.to_dict() for content in generated_contents if content != best_content]
            }, indent=2)
            
        except Exception as e:
            error_msg = f"Error generating content: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(error_msg)
    
    def _parse_news_data(self, news_data: str) -> List[NewsItem]:
        """Parse news data from JSON string"""
        try:
            data = json.loads(news_data)
            
            if isinstance(data, dict) and "news_items" in data:
                news_items_data = data["news_items"]
            elif isinstance(data, list):
                news_items_data = data
            else:
                logger.error("Invalid news data format")
                return []
            
            news_items = []
            for item_data in news_items_data:
                try:
                    # Convert timestamp string back to datetime
                    if isinstance(item_data.get("timestamp"), str):
                        item_data["timestamp"] = datetime.fromisoformat(item_data["timestamp"].replace("Z", "+00:00"))
                    
                    news_item = NewsItem(**item_data)
                    news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"Failed to parse news item: {str(e)}")
                    continue
            
            return news_items
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse news data JSON: {str(e)}")
            return []
    
    def _generate_content_text(self, news_item: NewsItem, content_type: str) -> str:
        """Generate content text based on news item and content type"""
        
        # Extract key information
        headline = news_item.headline
        summary = news_item.summary
        topics = news_item.topics
        
        # Determine sentiment and key insights
        sentiment = self._analyze_sentiment(headline + " " + summary)
        key_insight = self._extract_key_insight(summary)
        
        # Check if content_type is a ContentStrategy
        try:
            strategy = ContentStrategy(content_type)
            return self._generate_strategy_content(news_item, strategy, sentiment, key_insight)
        except ValueError:
            # Fallback to original content type handling
            pass
        
        # Get appropriate hook
        hook = self.strategies.get_engagement_hook(content_type, sentiment)
        
        # Generate content based on type
        if content_type == "news":
            return self._generate_news_content(hook, headline, key_insight, topics)
        elif content_type == "analysis":
            return self._generate_analysis_content(hook, key_insight, topics, summary)
        elif content_type == "opinion":
            return self._generate_opinion_content(hook, headline, key_insight, topics)
        elif content_type == "market_update":
            return self._generate_market_update_content(hook, headline, summary, topics)
        else:
            return self._generate_news_content(hook, headline, key_insight, topics)
    
    def _generate_strategy_content(self, news_item: NewsItem, strategy: ContentStrategy, 
                                 sentiment: str, key_insight: str) -> str:
        """Generate content based on specific A/B testing strategy"""
        
        headline = news_item.headline
        summary = news_item.summary
        topics = news_item.topics
        
        if strategy == ContentStrategy.VIRAL_HOOKS:
            return self._generate_viral_hooks_content(headline, key_insight, topics, sentiment)
        elif strategy == ContentStrategy.ANALYTICAL:
            return self._generate_analytical_content(headline, summary, topics, key_insight)
        elif strategy == ContentStrategy.CONTROVERSIAL:
            return self._generate_controversial_content(headline, key_insight, topics, sentiment)
        elif strategy == ContentStrategy.EDUCATIONAL:
            return self._generate_educational_content(headline, summary, topics, key_insight)
        elif strategy == ContentStrategy.MARKET_FOCUSED:
            return self._generate_market_focused_content(headline, summary, topics, sentiment)
        elif strategy == ContentStrategy.COMMUNITY_DRIVEN:
            return self._generate_community_driven_content(headline, key_insight, topics, sentiment)
        else:
            # Fallback to viral hooks
            return self._generate_viral_hooks_content(headline, key_insight, topics, sentiment)
    
    def _generate_viral_hooks_content(self, headline: str, key_insight: str, 
                                    topics: List[str], sentiment: str) -> str:
        """Generate content using viral hooks strategy"""
        hooks = ["🚨 BREAKING:", "🔥 This is HUGE:", "⚡ ALERT:", "💥 BOOM:", "🎯 CALLED IT:"]
        hook = hooks[0] if sentiment == "neutral" else ("📈 BULLISH:" if sentiment == "bullish" else "📉 BEARISH:")
        
        if len(headline) > 80:
            headline = headline[:77] + "..."
        
        templates = [
            f"{hook} {headline} - {key_insight}",
            f"{hook} {headline}! This changes everything 👀",
            f"{hook} {key_insight} - Are you ready? 🚀"
        ]
        
        return templates[0]
    
    def _generate_analytical_content(self, headline: str, summary: str, 
                                   topics: List[str], key_insight: str) -> str:
        """Generate content using analytical strategy"""
        hook = "📊 ANALYSIS:"
        
        # Extract data points or numbers from summary
        data_points = self._extract_data_points(summary)
        
        if data_points:
            return f"{hook} {key_insight} Key metrics: {data_points}"
        else:
            return f"{hook} {key_insight} Here's what the data shows..."
    
    def _generate_controversial_content(self, headline: str, key_insight: str, 
                                      topics: List[str], sentiment: str) -> str:
        """Generate content using controversial strategy"""
        hook = "🔥 HOT TAKE:"
        
        controversial_starters = [
            "Unpopular opinion:",
            "Everyone's wrong about this:",
            "The truth nobody wants to hear:",
            "Controversial but true:"
        ]
        
        starter = controversial_starters[0]
        return f"{hook} {starter} {key_insight} Change my mind 🤔"
    
    def _generate_educational_content(self, headline: str, summary: str, 
                                    topics: List[str], key_insight: str) -> str:
        """Generate content using educational strategy"""
        hook = "💡 LEARN:"
        
        educational_frames = [
            "Here's what you need to know:",
            "Quick explainer:",
            "Breaking it down:",
            "The basics:"
        ]
        
        frame = educational_frames[0]
        return f"{hook} {frame} {key_insight} Thread 🧵"
    
    def _generate_market_focused_content(self, headline: str, summary: str, 
                                       topics: List[str], sentiment: str) -> str:
        """Generate content using market-focused strategy"""
        if sentiment == "bullish":
            hook = "📈 MARKET:"
        elif sentiment == "bearish":
            hook = "📉 MARKET:"
        else:
            hook = "📊 MARKET:"
        
        # Extract price/market info
        price_info = self._extract_price_info(summary)
        
        if price_info:
            return f"{hook} {price_info} - Market implications are significant"
        else:
            return f"{hook} {headline[:100]}... Watch the charts 👀"
    
    def _generate_community_driven_content(self, headline: str, key_insight: str, 
                                         topics: List[str], sentiment: str) -> str:
        """Generate content using community-driven strategy"""
        hook = "🤝 COMMUNITY:"
        
        community_calls = [
            "What's your take?",
            "Thoughts below 👇",
            "Community, weigh in:",
            "Your opinion matters:"
        ]
        
        call = community_calls[0]
        return f"{hook} {key_insight} {call}"
    
    def _extract_data_points(self, text: str) -> str:
        """Extract numerical data points from text"""
        import re
        
        # Look for percentages, prices, numbers
        patterns = [
            r'\d+\.?\d*%',  # Percentages
            r'\$\d+\.?\d*[KMB]?',  # Prices
            r'\d+\.?\d*[KMB]',  # Large numbers
        ]
        
        data_points = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            data_points.extend(matches)
        
        return ", ".join(data_points[:3]) if data_points else ""
    
    def _extract_price_info(self, text: str) -> str:
        """Extract price-related information from text"""
        import re
        
        # Look for price movements, percentages, dollar amounts
        price_patterns = [
            r'up \d+\.?\d*%',
            r'down \d+\.?\d*%',
            r'gained? \d+\.?\d*%',
            r'lost \d+\.?\d*%',
            r'\$\d+\.?\d*[KMB]?',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        
        return ""
    
    def _analyze_sentiment(self, text: str) -> str:
        """Simple sentiment analysis based on keywords"""
        text_lower = text.lower()
        
        bullish_words = ["surge", "rally", "bull", "up", "gain", "rise", "pump", "moon", "bullish", "positive"]
        bearish_words = ["crash", "dump", "bear", "down", "fall", "drop", "decline", "bearish", "negative"]
        
        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)
        
        if bullish_count > bearish_count:
            return "bullish"
        elif bearish_count > bullish_count:
            return "bearish"
        else:
            return "neutral"
    
    def _extract_key_insight(self, summary: str) -> str:
        """Extract key insight from summary"""
        # Simple extraction - take first sentence or key phrase
        sentences = summary.split('. ')
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 100:
                return first_sentence[:97] + "..."
            return first_sentence
        return summary[:100] + "..." if len(summary) > 100 else summary
    
    def _generate_news_content(self, hook: str, headline: str, key_insight: str, topics: List[str]) -> str:
        """Generate news-type content"""
        templates = self.strategies.VIRAL_TEMPLATES["breaking_news"]
        template = templates[0]  # Use first template for now
        
        # Simplify headline if too long
        if len(headline) > 100:
            headline = headline[:97] + "..."
        
        return template.format(
            hook=hook,
            headline=headline,
            key_insight=key_insight,
            hashtags=""  # Hashtags added separately
        ).strip()
    
    def _generate_analysis_content(self, hook: str, key_insight: str, topics: List[str], summary: str) -> str:
        """Generate analysis-type content"""
        templates = self.strategies.VIRAL_TEMPLATES["analysis"]
        template = templates[0]
        
        # Extract explanation from summary
        explanation = self._extract_key_insight(summary)
        if len(explanation) > 80:
            explanation = explanation[:77] + "..."
        
        return template.format(
            hook=hook,
            key_point=key_insight,
            explanation=explanation,
            hashtags=""
        ).strip()
    
    def _generate_opinion_content(self, hook: str, headline: str, key_insight: str, topics: List[str]) -> str:
        """Generate opinion-type content"""
        templates = self.strategies.VIRAL_TEMPLATES["opinion"]
        template = templates[0]
        
        # Create opinion statement
        opinion = f"{key_insight}"
        reasoning = "The market dynamics are shifting."
        
        return template.format(
            hook=hook,
            opinion=opinion,
            reasoning=reasoning,
            hashtags=""
        ).strip()
    
    def _generate_market_update_content(self, hook: str, headline: str, summary: str, topics: List[str]) -> str:
        """Generate market update content"""
        templates = self.strategies.VIRAL_TEMPLATES["market_update"]
        template = templates[0]
        
        # Extract asset and movement
        asset = topics[0] if topics else "Crypto"
        movement = "moving" if "up" in summary.lower() or "rise" in summary.lower() else "active"
        context = self._extract_key_insight(summary)
        
        return template.format(
            hook=hook,
            asset=asset,
            movement=movement,
            context=context,
            hashtags=""
        ).strip()
    
    def _create_error_result(self, error_message: str) -> str:
        """Create error result JSON"""
        return json.dumps({
            "success": False,
            "error": error_message,
            "content": None,
            "alternatives": []
        }, indent=2)
    
    async def _arun(self, news_data: str, content_type: str = "news", target_engagement: float = 0.8) -> str:
        """Async version of _run method"""
        return self._run(news_data, content_type, target_engagement)


def create_content_generation_tool(config: AgentConfig) -> ContentGenerationTool:
    """
    Factory function to create a ContentGenerationTool instance
    """
    return ContentGenerationTool(config)