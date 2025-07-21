# src/agents/bluesky_crypto_agent.py
"""
Bluesky Crypto Agent - Main agent class for automated crypto content creation and posting
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import logging
import json
import traceback
import time

from .base_agent import BaseAgent
from ..utils.logging_config import log_performance
from ..utils.metrics_collector import get_metrics_collector, timer
from ..utils.alert_system import get_alert_manager, AlertSeverity
from ..utils.error_handler import get_error_handler, handle_errors, ErrorContext
from ..utils.circuit_breaker import get_circuit_breaker_manager, CircuitBreakerError
from ..models.data_models import NewsItem, GeneratedContent, PostResult, ContentType
from ..config.agent_config import AgentConfig
from ..services.content_filter import ContentFilter
from ..tools.news_retrieval_tool import create_news_retrieval_tool
from ..tools.content_generation_tool import create_content_generation_tool
from ..tools.bluesky_social_tool import BlueskySocialTool

logger = logging.getLogger(__name__)


class BlueskyCryptoAgent(BaseAgent):
    """
    Main orchestrator for the Bluesky crypto content creation workflow.
    Extends BaseAgent with specialized crypto content functionality.
    """
    
    def __init__(self, llm, config: AgentConfig, management_interface=None):
        """
        Initialize the BlueskyCryptoAgent with configuration and tools
        
        Args:
            llm: Language model instance for AI operations
            config: Agent configuration object
            management_interface: Optional management interface for overrides
        """
        super().__init__(llm)
        self.config = config
        self.management_interface = management_interface
        self.content_history: List[GeneratedContent] = []
        self.content_filter = ContentFilter(
            duplicate_threshold=config.duplicate_threshold,
            quality_threshold=config.min_engagement_score
        )
        
        # Initialize tools
        self._initialize_tools()
        
        # Workflow statistics
        self.workflow_stats = {
            'total_executions': 0,
            'successful_posts': 0,
            'failed_posts': 0,
            'filtered_content': 0,
            'last_execution': None,
            'last_success': None
        }
        
        logger.info(f"BlueskyCryptoAgent initialized with {len(self.tools)} tools")
    
    def _initialize_tools(self):
        """Initialize all required tools for the agent"""
        try:
            # News retrieval tool
            self.news_tool = create_news_retrieval_tool(self.config)
            self.add_tool(self.news_tool)
            
            # Content generation tool
            self.content_tool = create_content_generation_tool(self.config)
            self.add_tool(self.content_tool)
            
            # Bluesky social tool
            self.social_tool = BlueskySocialTool(max_retries=self.config.max_retries)
            self.add_tool(self.social_tool)
            
            logger.info("All tools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize tools: {str(e)}")
            raise
    
    @log_performance(component="bluesky_crypto_agent")
    async def execute_workflow(self, query: str = "latest cryptocurrency news") -> PostResult:
        """
        Execute the complete workflow: retrieve -> generate -> filter -> post
        
        Args:
            query: Search query for news retrieval
            
        Returns:
            PostResult object containing execution results
        """
        workflow_start = datetime.now()
        metrics_collector = get_metrics_collector()
        alert_manager = get_alert_manager()
        
        # Initialize workflow tracking
        self.workflow_stats['total_executions'] += 1
        self.workflow_stats['last_execution'] = workflow_start
        
        # Log workflow start event
        logger.info(f"Starting Bluesky crypto agent workflow with query: '{query}'", extra={
            "workflow_id": f"workflow_{int(time.time())}",
            "query": query,
            "execution_count": self.workflow_stats['total_executions']
        })
        
        # Record workflow start metrics
        metrics_collector.increment_counter("workflow_started", "bluesky_crypto_agent")
        metrics_collector.set_gauge("active_workflows", 1, "bluesky_crypto_agent")
        
        try:
            # Check for manual overrides before starting workflow
            if self.management_interface:
                skip_posting, _ = self.management_interface.is_override_active('skip_posting')
                if skip_posting:
                    logger.info("Workflow skipped due to manual override", extra={"step": "manual_override"})
                    return self._create_error_result("Workflow skipped by manual override", workflow_start)
            
            # Step 1: Retrieve cryptocurrency news
            logger.info("Step 1: Retrieving cryptocurrency news", extra={"step": "news_retrieval"})
            
            with metrics_collector.timer("news_retrieval", "bluesky_crypto_agent"):
                news_data = await self._retrieve_news(query)
            
            if not news_data or not news_data.get('success', False):
                error_msg = "Failed to retrieve news data"
                logger.error(error_msg, extra={"step": "news_retrieval", "error_type": "retrieval_failure"})
                
                # Record failure metrics and trigger alert
                metrics_collector.increment_counter("news_retrieval_failures", "bluesky_crypto_agent")
                alert_manager.trigger_alert(
                    title="News Retrieval Failed",
                    message=error_msg,
                    severity=AlertSeverity.HIGH,
                    component="bluesky_crypto_agent",
                    metadata={"query": query, "step": "news_retrieval"}
                )
                
                return self._create_error_result(error_msg, workflow_start)
            
            # Record successful news retrieval
            metrics_collector.increment_counter("news_retrieval_success", "bluesky_crypto_agent")
            metrics_collector.record_metric("news_items_retrieved", news_data.get('count', 0), "count", "bluesky_crypto_agent")
            
            # Step 2: Generate content from news
            logger.info("Step 2: Generating viral content", extra={"step": "content_generation"})
            
            with metrics_collector.timer("content_generation", "bluesky_crypto_agent"):
                content_data = await self._generate_content(news_data)
            
            if not content_data or not content_data.get('success', False):
                error_msg = "Failed to generate content"
                logger.error(error_msg, extra={"step": "content_generation", "error_type": "generation_failure"})
                
                # Record failure metrics and trigger alert
                metrics_collector.increment_counter("content_generation_failures", "bluesky_crypto_agent")
                alert_manager.trigger_alert(
                    title="Content Generation Failed",
                    message=error_msg,
                    severity=AlertSeverity.HIGH,
                    component="bluesky_crypto_agent",
                    metadata={"step": "content_generation"}
                )
                
                return self._create_error_result(error_msg, workflow_start)
            
            # Record successful content generation
            metrics_collector.increment_counter("content_generation_success", "bluesky_crypto_agent")
            
            # Step 3: Filter and validate content
            logger.info("Step 3: Filtering and validating content", extra={"step": "content_filtering"})
            
            with metrics_collector.timer("content_parsing", "bluesky_crypto_agent"):
                generated_content = self._parse_generated_content(content_data['content'])
            
            if not generated_content:
                error_msg = "Failed to parse generated content"
                logger.error(error_msg, extra={"step": "content_filtering", "error_type": "parsing_failure"})
                
                metrics_collector.increment_counter("content_parsing_failures", "bluesky_crypto_agent")
                return self._create_error_result(error_msg, workflow_start)
            
            # Apply content filtering
            with metrics_collector.timer("content_filtering", "bluesky_crypto_agent"):
                is_approved, filter_details = self.content_filter.filter_content(generated_content)
            
            # Check for manual content approval override
            force_approval = False
            if self.management_interface:
                force_approval, _ = self.management_interface.is_override_active('force_content_approval')
                if force_approval:
                    logger.info("Content approval forced by manual override", extra={"step": "manual_override"})
                    is_approved = True
            
            # Record content quality metrics
            metrics_collector.record_metric("content_engagement_score", generated_content.engagement_score, "score", "bluesky_crypto_agent")
            
            if not is_approved:
                self.workflow_stats['filtered_content'] += 1
                error_msg = f"Content filtered out: {filter_details.get('reasons', ['Unknown reason'])}"
                logger.warning(error_msg, extra={
                    "step": "content_filtering", 
                    "filter_reasons": filter_details.get('reasons', []),
                    "engagement_score": generated_content.engagement_score
                })
                
                # Record filtering metrics
                metrics_collector.increment_counter("content_filtered", "bluesky_crypto_agent")
                metrics_collector.record_metric("filtered_content_engagement_score", generated_content.engagement_score, "score", "bluesky_crypto_agent")
                
                return self._create_error_result(error_msg, workflow_start, generated_content)
            
            # Record successful content filtering
            metrics_collector.increment_counter("content_approved", "bluesky_crypto_agent")
            
            # Step 4: Post to Bluesky
            logger.info("Step 4: Posting to Bluesky", extra={"step": "bluesky_posting"})
            
            with metrics_collector.timer("bluesky_posting", "bluesky_crypto_agent"):
                post_result = await self._post_to_bluesky(generated_content)
            
            # Update history and statistics
            self.add_to_history(generated_content)
            
            # Calculate total workflow time
            workflow_duration = (datetime.now() - workflow_start).total_seconds()
            metrics_collector.record_metric("workflow_duration", workflow_duration, "seconds", "bluesky_crypto_agent")
            
            if post_result.success:
                self.workflow_stats['successful_posts'] += 1
                self.workflow_stats['last_success'] = datetime.now()
                
                logger.info(f"Workflow completed successfully. Post ID: {post_result.post_id}", extra={
                    "step": "workflow_complete",
                    "post_id": post_result.post_id,
                    "duration_seconds": workflow_duration,
                    "engagement_score": generated_content.engagement_score
                })
                
                # Record success metrics
                metrics_collector.increment_counter("workflow_success", "bluesky_crypto_agent")
                metrics_collector.increment_counter("posts_published", "bluesky_crypto_agent")
                metrics_collector.record_metric("successful_post_engagement_score", generated_content.engagement_score, "score", "bluesky_crypto_agent")
                
            else:
                self.workflow_stats['failed_posts'] += 1
                logger.error(f"Workflow failed at posting step: {post_result.error_message}", extra={
                    "step": "bluesky_posting",
                    "error_type": "posting_failure",
                    "error_message": post_result.error_message,
                    "retry_count": post_result.retry_count
                })
                
                # Record failure metrics and trigger alert
                metrics_collector.increment_counter("posting_failures", "bluesky_crypto_agent")
                alert_manager.trigger_alert(
                    title="Bluesky Posting Failed",
                    message=f"Failed to post content: {post_result.error_message}",
                    severity=AlertSeverity.HIGH,
                    component="bluesky_crypto_agent",
                    metadata={
                        "step": "bluesky_posting",
                        "error_message": post_result.error_message,
                        "retry_count": post_result.retry_count
                    }
                )
            
            return post_result
            
        except Exception as e:
            self.workflow_stats['failed_posts'] += 1
            workflow_duration = (datetime.now() - workflow_start).total_seconds()
            error_msg = f"Workflow execution failed: {str(e)}"
            
            logger.error(f"{error_msg}\n{traceback.format_exc()}", extra={
                "step": "workflow_exception",
                "error_type": "unexpected_exception",
                "duration_seconds": workflow_duration,
                "exception_type": type(e).__name__
            })
            
            # Record exception metrics and trigger critical alert
            metrics_collector.increment_counter("workflow_exceptions", "bluesky_crypto_agent")
            metrics_collector.record_metric("failed_workflow_duration", workflow_duration, "seconds", "bluesky_crypto_agent")
            
            alert_manager.trigger_alert(
                title="Workflow Exception",
                message=f"Unexpected error in workflow: {str(e)}",
                severity=AlertSeverity.CRITICAL,
                component="bluesky_crypto_agent",
                metadata={
                    "exception_type": type(e).__name__,
                    "duration_seconds": workflow_duration,
                    "traceback": traceback.format_exc()
                }
            )
            
            return self._create_error_result(error_msg, workflow_start)
        
        finally:
            # Always reset active workflows gauge
            metrics_collector.set_gauge("active_workflows", 0, "bluesky_crypto_agent")
    
    @handle_errors("bluesky_crypto_agent", "retrieve_news", attempt_recovery=True)
    async def _retrieve_news(self, query: str) -> Dict[str, Any]:
        """
        Retrieve news using the news retrieval tool with enhanced error handling
        
        Args:
            query: Search query for news
            
        Returns:
            Dictionary containing news data
        """
        try:
            # Check circuit breaker status
            circuit_breaker_manager = get_circuit_breaker_manager()
            news_circuit = circuit_breaker_manager.get_circuit_breaker("perplexity_api")
            
            if news_circuit.get_state().value == "open":
                logger.warning("News retrieval circuit breaker is open, using fallback")
                return self._get_fallback_news_data(query)
            
            # Use the news retrieval tool
            news_result = await self.news_tool._arun(query)
            return json.loads(news_result)
            
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker prevented news retrieval: {str(e)}")
            return self._get_fallback_news_data(query)
            
        except Exception as e:
            # Handle specific error types with recovery
            error_handler = get_error_handler()
            context = ErrorContext(
                component="bluesky_crypto_agent",
                operation="retrieve_news",
                metadata={"query": query}
            )
            
            error_record = error_handler.handle_error(e, context, attempt_recovery=True)
            
            if error_record and not error_record.recovery_successful:
                logger.error(f"News retrieval failed after recovery attempts: {str(e)}")
                return self._get_fallback_news_data(query)
            
            # If we reach here, recovery was successful, retry the operation
            try:
                news_result = await self.news_tool._arun(query)
                return json.loads(news_result)
            except Exception as retry_error:
                logger.error(f"News retrieval retry failed: {str(retry_error)}")
                return {'success': False, 'error': str(retry_error)}
    
    def _get_fallback_news_data(self, query: str) -> Dict[str, Any]:
        """
        Provide fallback news data when primary news retrieval fails
        
        Args:
            query: Original search query
            
        Returns:
            Dictionary containing fallback news data
        """
        logger.info("Using fallback news data due to API failure")
        
        # Create generic crypto news items based on common topics
        fallback_news = [
            {
                "headline": "Cryptocurrency Market Update",
                "summary": "Latest developments in the cryptocurrency market continue to show volatility and innovation across major digital assets.",
                "source": "Fallback System",
                "timestamp": datetime.now().isoformat(),
                "relevance_score": 0.6,
                "topics": ["Bitcoin", "Cryptocurrency", "Market"],
                "url": None,
                "raw_content": "Cryptocurrency market analysis and updates"
            },
            {
                "headline": "Bitcoin and Ethereum Price Analysis",
                "summary": "Technical analysis shows continued interest in major cryptocurrencies as institutional adoption grows.",
                "source": "Fallback System", 
                "timestamp": datetime.now().isoformat(),
                "relevance_score": 0.7,
                "topics": ["Bitcoin", "Ethereum", "Analysis"],
                "url": None,
                "raw_content": "Bitcoin Ethereum price technical analysis"
            }
        ]
        
        return {
            "success": True,
            "count": len(fallback_news),
            "news_items": fallback_news,
            "fallback": True,
            "original_query": query
        }
    
    @handle_errors("bluesky_crypto_agent", "generate_content", attempt_recovery=True)
    async def _generate_content(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate content using the content generation tool with enhanced error handling
        
        Args:
            news_data: News data from retrieval step
            
        Returns:
            Dictionary containing generated content
        """
        try:
            # Convert news data back to JSON string for the tool
            news_json = json.dumps(news_data)
            
            # Use the content generation tool
            content_result = await self.content_tool._arun(
                news_data=news_json,
                content_type="news",
                target_engagement=self.config.min_engagement_score
            )
            
            result = json.loads(content_result)
            
            # Validate the generated content
            if not self._validate_generated_content(result):
                logger.warning("Generated content failed validation, using fallback")
                return self._get_fallback_content_data(news_data)
            
            return result
            
        except Exception as e:
            # Handle specific error types with recovery
            error_handler = get_error_handler()
            context = ErrorContext(
                component="bluesky_crypto_agent",
                operation="generate_content",
                metadata={"news_count": news_data.get('count', 0)}
            )
            
            error_record = error_handler.handle_error(e, context, attempt_recovery=True)
            
            if error_record and not error_record.recovery_successful:
                logger.error(f"Content generation failed after recovery attempts: {str(e)}")
                return self._get_fallback_content_data(news_data)
            
            # If we reach here, recovery was successful, retry the operation
            try:
                news_json = json.dumps(news_data)
                content_result = await self.content_tool._arun(
                    news_data=news_json,
                    content_type="news",
                    target_engagement=self.config.min_engagement_score
                )
                return json.loads(content_result)
            except Exception as retry_error:
                logger.error(f"Content generation retry failed: {str(retry_error)}")
                return self._get_fallback_content_data(news_data)
    
    def _validate_generated_content(self, content_data: Dict[str, Any]) -> bool:
        """
        Validate generated content data structure and quality
        
        Args:
            content_data: Generated content data to validate
            
        Returns:
            True if content is valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['success', 'content']
            for field in required_fields:
                if field not in content_data:
                    logger.warning(f"Missing required field in content data: {field}")
                    return False
            
            if not content_data.get('success', False):
                logger.warning("Content generation was not successful")
                return False
            
            content = content_data.get('content', {})
            
            # Check content structure
            content_required_fields = ['text', 'hashtags', 'engagement_score', 'content_type', 'source_news']
            for field in content_required_fields:
                if field not in content:
                    logger.warning(f"Missing required field in content: {field}")
                    return False
            
            # Validate content quality
            text = content.get('text', '')
            if not text or len(text.strip()) < 10:
                logger.warning("Generated text is too short or empty")
                return False
            
            if len(text) > self.config.max_post_length:
                logger.warning(f"Generated text exceeds maximum length: {len(text)}/{self.config.max_post_length}")
                return False
            
            engagement_score = content.get('engagement_score', 0)
            if engagement_score < 0.1:  # Minimum quality threshold
                logger.warning(f"Generated content has very low engagement score: {engagement_score}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating generated content: {str(e)}")
            return False
    
    def _get_fallback_content_data(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fallback content when primary content generation fails
        
        Args:
            news_data: News data to base fallback content on
            
        Returns:
            Dictionary containing fallback content data
        """
        logger.info("Using fallback content generation due to primary failure")
        
        # Extract key information from news data
        news_items = news_data.get('news_items', [])
        
        # Create fallback content based on available news
        if news_items:
            first_item = news_items[0]
            headline = first_item.get('headline', 'Cryptocurrency Update')
            topics = first_item.get('topics', ['Cryptocurrency'])
        else:
            headline = 'Cryptocurrency Market Update'
            topics = ['Cryptocurrency', 'Market']
        
        # Generate simple fallback content
        fallback_texts = [
            f"🚀 {headline[:100]}... What are your thoughts on this crypto development?",
            f"📈 Latest in crypto: {headline[:120]}... #crypto #blockchain",
            f"💡 Crypto insight: {headline[:110]}... Stay informed! #cryptocurrency",
            f"🔥 Breaking: {headline[:130]}... #bitcoin #ethereum #crypto"
        ]
        
        # Select appropriate fallback text based on length
        selected_text = None
        for text in fallback_texts:
            if len(text) <= self.config.max_post_length:
                selected_text = text
                break
        
        if not selected_text:
            selected_text = f"🚀 Crypto update: Stay informed about the latest developments! #crypto"
        
        # Generate hashtags based on topics
        hashtags = []
        for topic in topics[:3]:  # Limit to 3 hashtags
            hashtag = f"#{topic.lower().replace(' ', '').replace('-', '')}"
            if hashtag not in hashtags:
                hashtags.append(hashtag)
        
        # Create fallback source news
        fallback_source_news = {
            "headline": headline,
            "summary": "Fallback content generated due to primary system failure",
            "source": "Fallback System",
            "timestamp": datetime.now().isoformat(),
            "relevance_score": 0.5,
            "topics": topics,
            "url": None,
            "raw_content": headline
        }
        
        # Create fallback content structure
        fallback_content = {
            "text": selected_text,
            "hashtags": hashtags,
            "engagement_score": 0.6,  # Moderate engagement score for fallback
            "content_type": "news",
            "source_news": fallback_source_news,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "fallback": True,
                "fallback_reason": "primary_content_generation_failed"
            }
        }
        
        return {
            "success": True,
            "content": fallback_content,
            "fallback": True
        }
    
    @handle_errors("bluesky_crypto_agent", "post_to_bluesky", attempt_recovery=True)
    async def _post_to_bluesky(self, content: GeneratedContent) -> PostResult:
        """
        Post content to Bluesky using the social tool with enhanced error handling
        
        Args:
            content: Generated content to post
            
        Returns:
            PostResult object
        """
        try:
            # Check circuit breaker status for Bluesky posting
            circuit_breaker_manager = get_circuit_breaker_manager()
            post_circuit = circuit_breaker_manager.get_circuit_breaker("bluesky_post")
            
            if post_circuit.get_state().value == "open":
                error_msg = "Bluesky posting circuit breaker is open, skipping post"
                logger.warning(error_msg)
                return PostResult(
                    success=False,
                    post_id=None,
                    timestamp=datetime.now(),
                    content=content,
                    error_message=error_msg,
                    retry_count=0
                )
            
            # Prepare the full post text with hashtags
            full_text = content.text
            if content.hashtags:
                hashtag_text = " " + " ".join(content.hashtags)
                if len(full_text + hashtag_text) <= self.config.max_post_length:
                    full_text += hashtag_text
            
            # Use the Bluesky social tool
            post_result = await self.social_tool._arun(
                content=full_text,
                username=self.config.bluesky_username,
                password=self.config.bluesky_password
            )
            
            # Create PostResult object
            result = PostResult(
                success=post_result['success'],
                post_id=post_result.get('post_id'),
                timestamp=datetime.now(),
                content=content,
                error_message=post_result.get('error_message'),
                retry_count=post_result.get('retry_count', 0),
                response_data=post_result
            )
            
            # If posting failed, handle with error recovery
            if not result.success:
                error_handler = get_error_handler()
                context = ErrorContext(
                    component="bluesky_crypto_agent",
                    operation="post_to_bluesky",
                    metadata={
                        "content_length": len(full_text),
                        "hashtag_count": len(content.hashtags),
                        "engagement_score": content.engagement_score
                    }
                )
                
                # Create a temporary exception for error handling
                posting_error = Exception(result.error_message or "Bluesky posting failed")
                error_record = error_handler.handle_error(posting_error, context, attempt_recovery=True)
                
                if error_record and error_record.recovery_successful:
                    # Retry posting after successful recovery
                    logger.info("Retrying Bluesky posting after successful error recovery")
                    retry_result = await self.social_tool._arun(
                        content=full_text,
                        username=self.config.bluesky_username,
                        password=self.config.bluesky_password
                    )
                    
                    result = PostResult(
                        success=retry_result['success'],
                        post_id=retry_result.get('post_id'),
                        timestamp=datetime.now(),
                        content=content,
                        error_message=retry_result.get('error_message'),
                        retry_count=retry_result.get('retry_count', 0) + 1,
                        response_data=retry_result
                    )
            
            return result
            
        except CircuitBreakerError as e:
            error_msg = f"Circuit breaker prevented Bluesky posting: {str(e)}"
            logger.warning(error_msg)
            return PostResult(
                success=False,
                post_id=None,
                timestamp=datetime.now(),
                content=content,
                error_message=error_msg,
                retry_count=0
            )
            
        except Exception as e:
            # Handle unexpected errors with recovery
            error_handler = get_error_handler()
            context = ErrorContext(
                component="bluesky_crypto_agent",
                operation="post_to_bluesky",
                metadata={
                    "content_length": len(content.text),
                    "hashtag_count": len(content.hashtags),
                    "engagement_score": content.engagement_score,
                    "exception_type": type(e).__name__
                }
            )
            
            error_record = error_handler.handle_error(e, context, attempt_recovery=True)
            
            if error_record and error_record.recovery_successful:
                # Retry posting after successful recovery
                try:
                    full_text = content.text
                    if content.hashtags:
                        hashtag_text = " " + " ".join(content.hashtags)
                        if len(full_text + hashtag_text) <= self.config.max_post_length:
                            full_text += hashtag_text
                    
                    retry_result = await self.social_tool._arun(
                        content=full_text,
                        username=self.config.bluesky_username,
                        password=self.config.bluesky_password
                    )
                    
                    return PostResult(
                        success=retry_result['success'],
                        post_id=retry_result.get('post_id'),
                        timestamp=datetime.now(),
                        content=content,
                        error_message=retry_result.get('error_message'),
                        retry_count=retry_result.get('retry_count', 0) + 1,
                        response_data=retry_result
                    )
                    
                except Exception as retry_error:
                    logger.error(f"Bluesky posting retry failed: {str(retry_error)}")
            
            # Return error result
            logger.error(f"Bluesky posting failed: {str(e)}")
            return PostResult(
                success=False,
                post_id=None,
                timestamp=datetime.now(),
                content=content,
                error_message=str(e),
                retry_count=0
            )
    
    def _parse_generated_content(self, content_data: Dict[str, Any]) -> Optional[GeneratedContent]:
        """
        Parse generated content data into GeneratedContent object
        
        Args:
            content_data: Raw content data from generation tool
            
        Returns:
            GeneratedContent object or None if parsing fails
        """
        try:
            # Parse source news
            source_news_data = content_data['source_news']
            if isinstance(source_news_data.get('timestamp'), str):
                source_news_data['timestamp'] = datetime.fromisoformat(
                    source_news_data['timestamp'].replace('Z', '+00:00')
                )
            
            source_news = NewsItem(**source_news_data)
            
            # Parse generated content
            return GeneratedContent(
                text=content_data['text'],
                hashtags=content_data['hashtags'],
                engagement_score=content_data['engagement_score'],
                content_type=ContentType(content_data['content_type']),
                source_news=source_news,
                created_at=datetime.fromisoformat(content_data['created_at']) if isinstance(content_data.get('created_at'), str) else datetime.now(),
                metadata=content_data.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Failed to parse generated content: {str(e)}")
            return None
    
    def _create_error_result(self, error_message: str, start_time: datetime, content: Optional[GeneratedContent] = None) -> PostResult:
        """
        Create a PostResult object for error cases
        
        Args:
            error_message: Error description
            start_time: Workflow start time
            content: Generated content if available
            
        Returns:
            PostResult object representing the error
        """
        # Create dummy content if none provided
        if not content:
            dummy_news = NewsItem(
                headline="Error in workflow",
                summary="Workflow execution failed",
                source="System",
                timestamp=start_time,
                relevance_score=0.0,
                topics=["Error"]
            )
            
            content = GeneratedContent(
                text="Workflow execution failed",
                hashtags=[],
                engagement_score=0.0,
                content_type=ContentType.NEWS,
                source_news=dummy_news,
                created_at=start_time
            )
        
        return PostResult(
            success=False,
            post_id=None,
            timestamp=datetime.now(),
            content=content,
            error_message=error_message,
            retry_count=0
        )
    
    def add_to_history(self, content: GeneratedContent):
        """
        Add generated content to history for duplicate prevention
        
        Args:
            content: Generated content to add to history
        """
        self.content_history.append(content)
        
        # Add to content filter history as well
        self.content_filter.add_to_history(content)
        
        # Keep only recent history based on config (default 50 items)
        max_history = getattr(self.config, 'max_history_size', 50)
        if len(self.content_history) > max_history:
            self.content_history = self.content_history[-max_history:]
        
        logger.debug(f"Added content to history. Total items: {len(self.content_history)}")
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """
        Get workflow execution statistics
        
        Returns:
            Dictionary containing workflow statistics
        """
        stats = self.workflow_stats.copy()
        
        # Add success rate
        if stats['total_executions'] > 0:
            stats['success_rate'] = stats['successful_posts'] / stats['total_executions']
        else:
            stats['success_rate'] = 0.0
        
        # Add content filter stats
        stats['content_filter_stats'] = self.content_filter.get_history_stats()
        
        # Add history size
        stats['content_history_size'] = len(self.content_history)
        
        return stats
    
    def get_recent_content(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent content from history
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of content dictionaries
        """
        recent_content = self.content_history[-limit:] if self.content_history else []
        return [content.to_dict() for content in reversed(recent_content)]
    
    def clear_history(self):
        """Clear content history (useful for testing or maintenance)"""
        self.content_history.clear()
        # Reset content filter history as well
        self.content_filter.recent_posts.clear()
        self.content_filter.content_hashes.clear()
        logger.info("Content history cleared")