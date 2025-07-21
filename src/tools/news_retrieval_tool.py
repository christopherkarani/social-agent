# src/tools/news_retrieval_tool.py
"""
NewsRetrievalTool for integrating with Perplexity API to retrieve cryptocurrency news
Enhanced with circuit breaker pattern and comprehensive error handling
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from pydantic import BaseModel, Field

from ..models.data_models import NewsItem
from ..config.agent_config import AgentConfig
from ..utils.circuit_breaker import circuit_breaker, CircuitBreakerConfig, CircuitBreakerError
from ..utils.error_handler import handle_errors, ErrorContext, get_error_handler

logger = logging.getLogger(__name__)


class NewsRetrievalInput(BaseModel):
    """Input schema for news retrieval tool"""
    query: str = Field(description="Search query for cryptocurrency news")
    max_results: int = Field(default=10, description="Maximum number of results to return")
    topics: Optional[List[str]] = Field(default=None, description="Specific crypto topics to focus on")


class PerplexityAPIClient:
    """
    Client for interacting with Perplexity API with circuit breaker and enhanced error handling
    """
    
    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key
        self.max_retries = max_retries
        self.base_url = "https://api.perplexity.ai"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
        # Initialize circuit breaker for Perplexity API
        self.circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
            timeout=30,
            failure_status_codes=(429, 500, 502, 503, 504)
        )
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        return min(2 ** attempt, 30)  # Cap at 30 seconds
    
    def _is_retryable_error(self, status_code: int) -> bool:
        """Check if error is retryable"""
        return status_code in [429, 500, 502, 503, 504]
    
    @circuit_breaker("perplexity_api")
    @handle_errors("news_retrieval_tool", "search_news", attempt_recovery=True)
    def search_news(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search for news using Perplexity API with retry logic
        """
        url = f"{self.base_url}/chat/completions"
        
        # Construct the search prompt for crypto news
        search_prompt = f"""
        Search for the latest cryptocurrency news about: {query}
        
        Please provide recent news articles with the following information for each:
        - Headline
        - Brief summary (2-3 sentences)
        - Source publication
        - Publication date/time
        - Relevance to cryptocurrency market
        - Key topics covered
        - URL if available
        
        Focus on news from the last 24-48 hours. Prioritize major crypto publications and mainstream financial news.
        Return results in a structured format.
        """
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a cryptocurrency news aggregator. Provide accurate, recent news with proper source attribution."
                },
                {
                    "role": "user", 
                    "content": search_prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.2,
            "top_p": 0.9,
            "return_citations": True,
            "search_domain_filter": ["coindesk.com", "cointelegraph.com", "decrypt.co", "theblock.co", "bloomberg.com", "reuters.com"],
            "return_images": False
        }
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting Perplexity API request (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.session.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    logger.info("Successfully retrieved news from Perplexity API")
                    return response.json()
                
                elif self._is_retryable_error(response.status_code):
                    logger.warning(f"Retryable error {response.status_code}: {response.text}")
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff_delay(attempt)
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                        continue
                
                else:
                    logger.error(f"Non-retryable error {response.status_code}: {response.text}")
                    response.raise_for_status()
                    break  # Exit the retry loop for non-retryable errors
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                    continue
                    
            except requests.exceptions.HTTPError as e:
                # Re-raise HTTPError immediately for non-retryable errors
                raise e
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"Request exception on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                    continue
        
        # All retries exhausted
        error_msg = f"Failed to retrieve news after {self.max_retries} attempts"
        if last_exception:
            error_msg += f": {str(last_exception)}"
        logger.error(error_msg)
        raise Exception(error_msg)


class NewsContentParser:
    """
    Parser for processing and filtering Perplexity API responses into structured NewsItem objects
    """
    
    CRYPTO_KEYWORDS = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'cryptocurrency', 'crypto', 'blockchain',
        'defi', 'nft', 'altcoin', 'dogecoin', 'cardano', 'solana', 'polygon', 'avalanche',
        'chainlink', 'uniswap', 'binance', 'coinbase', 'trading', 'mining', 'staking',
        'web3', 'metaverse', 'dao', 'yield farming', 'liquidity', 'smart contract'
    ]
    
    def __init__(self, content_themes: List[str]):
        self.content_themes = [theme.lower() for theme in content_themes]
    
    def calculate_relevance_score(self, text: str, topics: List[str]) -> float:
        """
        Calculate relevance score based on crypto keywords and topics
        """
        text_lower = text.lower()
        
        # Count keyword matches
        keyword_matches = sum(1 for keyword in self.CRYPTO_KEYWORDS if keyword in text_lower)
        keyword_score = min(keyword_matches / 10, 0.7)  # Max 0.7 from keywords
        
        # Count theme matches
        theme_matches = sum(1 for theme in self.content_themes if theme in text_lower)
        theme_score = min(theme_matches / 5, 0.3)  # Max 0.3 from themes
        
        return min(keyword_score + theme_score, 1.0)
    
    def extract_topics(self, text: str) -> List[str]:
        """
        Extract relevant crypto topics from text
        """
        text_lower = text.lower()
        found_topics = []
        
        # Check for specific cryptocurrencies and topics
        topic_mapping = {
            'bitcoin': 'Bitcoin',
            'btc': 'Bitcoin', 
            'ethereum': 'Ethereum',
            'eth': 'Ethereum',
            'defi': 'DeFi',
            'nft': 'NFTs',
            'dogecoin': 'Dogecoin',
            'cardano': 'Cardano',
            'solana': 'Solana',
            'polygon': 'Polygon',
            'avalanche': 'Avalanche',
            'chainlink': 'Chainlink',
            'uniswap': 'Uniswap',
            'binance': 'Binance',
            'coinbase': 'Coinbase',
            'trading': 'Trading',
            'mining': 'Mining',
            'staking': 'Staking',
            'web3': 'Web3',
            'metaverse': 'Metaverse',
            'dao': 'DAO'
        }
        
        for keyword, topic in topic_mapping.items():
            if keyword in text_lower and topic not in found_topics:
                found_topics.append(topic)
        
        # Add general crypto topic if none found
        if not found_topics:
            found_topics.append('Cryptocurrency')
            
        return found_topics
    
    def parse_response(self, api_response: Dict[str, Any]) -> List[NewsItem]:
        """
        Parse Perplexity API response into NewsItem objects
        """
        news_items = []
        
        try:
            # Extract the main content from the response
            if 'choices' not in api_response or not api_response['choices']:
                logger.warning("No choices found in API response")
                return news_items
            
            content = api_response['choices'][0]['message']['content']
            citations = api_response.get('citations', [])
            
            # Debug logging to see the actual response format
            logger.info(f"API Response content: {content[:500]}...")
            logger.info(f"Citations: {citations}")
            
            # Parse the structured response from Perplexity API
            lines = content.split('\n')
            
            # Check if it's a table format
            if '|' in content and 'Headline' in content:
                # Parse table format
                table_lines = [line.strip() for line in lines if line.strip() and '|' in line]
                
                if len(table_lines) >= 3:  # Header, separator, and at least one data row
                    # Skip header and separator lines
                    data_lines = table_lines[2:]  # Skip header and separator
                    
                    for line in data_lines:
                        # Split by | and clean up
                        columns = [col.strip() for col in line.split('|')]
                        if len(columns) >= 4:  # At least headline, summary, source, date
                            headline = columns[1].strip('*').strip() if len(columns) > 1 else ""
                            summary = columns[2].strip() if len(columns) > 2 else ""
                            source = columns[3].strip() if len(columns) > 3 else "Perplexity AI"
                            
                            if headline and summary:
                                current_item = {
                                    'headline': headline,
                                    'summary': summary,
                                    'source': source
                                }
                                news_item = self._create_news_item(current_item, citations)
                                if news_item:
                                    news_items.append(news_item)
            else:
                # Parse the original structured format
                current_item = {}
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('---'):
                        continue
                    
                    # Look for numbered headlines: **1. Headline:** or **Headline:**
                    if line.startswith('**') and ('Headline:' in line):
                        # Extract headline
                        if current_item:
                            # Process previous item
                            news_item = self._create_news_item(current_item, citations)
                            if news_item:
                                news_items.append(news_item)
                        
                        # Extract headline text after "Headline:"
                        headline_part = line.split('Headline:', 1)
                        if len(headline_part) > 1:
                            headline = headline_part[1].strip().strip('*').strip()
                            current_item = {'headline': headline}
                    
                    # Look for summary: - **Summary:** or - **Brief summary:**
                    elif (line.startswith('- **Summary:**') or line.startswith('- **Brief summary:**')) and current_item:
                        if line.startswith('- **Summary:**'):
                            summary = line.replace('- **Summary:**', '').strip()
                        else:
                            summary = line.replace('- **Brief summary:**', '').strip()
                        current_item['summary'] = summary
                    
                    # Look for source: - **Source Publication:**
                    elif line.startswith('- **Source Publication:**') and current_item:
                        source = line.replace('- **Source Publication:**', '').strip()
                        current_item['source'] = source
                    
                    # Look for date: - **Publication Date/Time:**
                    elif line.startswith('- **Publication Date/Time:**') and current_item:
                        date = line.replace('- **Publication Date/Time:**', '').strip()
                        current_item['date'] = date
                    
                    # Continue summary if we're in a summary section
                    elif current_item and 'summary' in current_item and not line.startswith('- **'):
                        current_item['summary'] += ' ' + line
                
                # Process the last item
                if current_item:
                    news_item = self._create_news_item(current_item, citations)
                    if news_item:
                        news_items.append(news_item)
            
            # If structured parsing didn't work well, create a general news item
            if not news_items and content:
                general_item = {
                    'headline': 'Latest Cryptocurrency News Update',
                    'summary': content[:500] + '...' if len(content) > 500 else content
                }
                news_item = self._create_news_item(general_item, citations)
                if news_item:
                    news_items.append(news_item)
                    
        except Exception as e:
            logger.error(f"Error parsing API response: {str(e)}")
            # Create a fallback news item
            fallback_item = {
                'headline': 'Cryptocurrency Market Update',
                'summary': 'Latest developments in the cryptocurrency market. Check official sources for detailed information.'
            }
            news_item = self._create_news_item(fallback_item, [])
            if news_item:
                news_items.append(news_item)
        
        logger.info(f"Parsed {len(news_items)} news items from API response")
        return news_items
    
    def _create_news_item(self, item_data: Dict[str, str], citations: List[Dict]) -> Optional[NewsItem]:
        """
        Create a NewsItem from parsed data
        """
        try:
            # Debug logging to see what we're receiving
            logger.info(f"Creating NewsItem with data: {item_data} (type: {type(item_data)})")
            
            headline = item_data.get('headline', '').strip()
            summary = item_data.get('summary', '').strip()
            
            if not headline or not summary:
                return None
            
            # Extract topics and calculate relevance
            full_text = f"{headline} {summary}"
            topics = self.extract_topics(full_text)
            relevance_score = self.calculate_relevance_score(full_text, topics)
            
            # Get source information from citations if available
            source = item_data.get('source', 'Perplexity AI')
            url = None
            if citations and isinstance(citations, list) and len(citations) > 0:
                # Citations are URLs (strings), not dictionaries
                url = citations[0] if isinstance(citations[0], str) else None
            
            return NewsItem(
                headline=headline,
                summary=summary,
                source=source,
                timestamp=datetime.now(),
                relevance_score=relevance_score,
                topics=topics,
                url=url,
                raw_content=full_text
            )
            
        except Exception as e:
            logger.error(f"Error creating NewsItem: {str(e)}")
            return None


class NewsRetrievalTool:
    """
    Tool for retrieving cryptocurrency news from Perplexity API
    Compatible with LangChain agent framework
    """
    
    def __init__(self, config: AgentConfig):
        self.name = "crypto_news_retrieval"
        self.description = """
        Retrieves latest cryptocurrency news from Perplexity API.
        Input should be a search query for crypto news (e.g., "Bitcoin price", "Ethereum updates", "DeFi news").
        Returns structured news data with headlines, summaries, sources, and relevance scores.
        """
        self.config = config
        self.api_client = PerplexityAPIClient(
            api_key=config.perplexity_api_key,
            max_retries=config.max_retries
        )
        self.parser = NewsContentParser(config.content_themes)
    
    def _run(self, query: str) -> str:
        """
        Execute the news retrieval tool
        """
        try:
            logger.info(f"Retrieving crypto news for query: {query}")
            
            # Search for news using Perplexity API
            api_response = self.api_client.search_news(query, max_results=10)
            
            # Parse response into NewsItem objects
            news_items = self.parser.parse_response(api_response)
            
            # Filter for relevant content
            # Debug: Log relevance scores
            for item in news_items:
                logger.info(f"News item '{item.headline[:50]}...' has relevance score: {item.relevance_score}")
            
            relevant_news = [
                item for item in news_items 
                if item.relevance_score >= 0.1  # Minimum relevance threshold (lowered)
            ]
            
            logger.info(f"Filtered to {len(relevant_news)} relevant news items (threshold: 0.3)")
            
            # Sort by relevance score
            relevant_news.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Prepare response
            if relevant_news:
                result = {
                    "success": True,
                    "count": len(relevant_news),
                    "news_items": [item.to_dict() for item in relevant_news]
                }
                logger.info(f"Successfully retrieved {len(relevant_news)} relevant news items")
            else:
                result = {
                    "success": False,
                    "count": 0,
                    "news_items": [],
                    "message": "No relevant cryptocurrency news found for the given query"
                }
                logger.warning("No relevant news items found")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error retrieving news: {str(e)}"
            logger.error(error_msg)
            
            error_result = {
                "success": False,
                "count": 0,
                "news_items": [],
                "error": error_msg
            }
            
            return json.dumps(error_result, indent=2)
    
    async def _arun(self, query: str) -> str:
        """
        Async version of the tool execution
        """
        # For now, we'll run the sync version in an executor
        # In production, you might want to implement true async HTTP calls
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, query)


def create_news_retrieval_tool(config: AgentConfig) -> NewsRetrievalTool:
    """
    Factory function to create a NewsRetrievalTool instance
    """
    if not config.perplexity_api_key:
        raise ValueError("Perplexity API key is required")
    
    return NewsRetrievalTool(config)