# src/tools/bluesky_social_tool.py
"""
Bluesky Social Tool - LangChain tool for posting content to Bluesky social platform
Enhanced with circuit breaker pattern and comprehensive error handling
"""
import logging
import time
from typing import Dict, Optional, Any
from datetime import datetime

from langchain.tools import Tool
from atproto import Client, models
from pydantic import BaseModel, Field, PrivateAttr

from ..models.data_models import PostResult, GeneratedContent
from ..utils.circuit_breaker import circuit_breaker, CircuitBreakerConfig, CircuitBreakerError
from ..utils.error_handler import handle_errors, ErrorContext, get_error_handler

logger = logging.getLogger(__name__)


class BlueskySocialInput(BaseModel):
    """Input schema for BlueskySocialTool"""
    content: str = Field(description="Content to post to Bluesky")
    username: str = Field(description="Bluesky username")
    password: str = Field(description="Bluesky password")


class BlueskySocialTool(Tool):
    """
    LangChain tool for posting content to Bluesky social platform using AT Protocol
    """
    
    _max_retries: int = PrivateAttr(default=2)
    _client: Optional[Client] = PrivateAttr(default=None)
    _authenticated_user: Optional[str] = PrivateAttr(default=None)
    
    def __init__(self, max_retries: int = 2, **kwargs):
        super().__init__(
            name="bluesky_publisher",
            description="Posts content to Bluesky social platform with authentication and retry logic",
            func=self._run,
            args_schema=BlueskySocialInput,
            **kwargs
        )
        self._max_retries = max_retries
        self._client = None
        self._authenticated_user = None
    
    @property
    def max_retries(self) -> int:
        return self._max_retries
    
    @property
    def client(self) -> Optional[Client]:
        return self._client
    
    @client.setter
    def client(self, value: Optional[Client]) -> None:
        self._client = value
    
    @property
    def authenticated_user(self) -> Optional[str]:
        return self._authenticated_user
    
    @authenticated_user.setter
    def authenticated_user(self, value: Optional[str]) -> None:
        self._authenticated_user = value
        
    def _run(self, content: str, username: str, password: str) -> Dict[str, Any]:
        """
        Post content to Bluesky with authentication and retry logic
        
        Args:
            content: The content to post (max 300 characters)
            username: Bluesky username
            password: Bluesky password
            
        Returns:
            Dict containing post result information
        """
        logger.info(f"Attempting to post content to Bluesky for user: {username}")
        
        # Validate content length
        if len(content) > 300:
            error_msg = f"Content exceeds Bluesky character limit: {len(content)}/300 characters"
            logger.error(error_msg)
            return self._create_error_result(content, error_msg, 0)
        
        # Attempt posting with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                # Authenticate if needed
                if not self._is_authenticated(username):
                    self._authenticate(username, password)
                
                # Create and publish post
                post_result = self._create_post(content)
                
                logger.info(f"Successfully posted to Bluesky: {post_result.get('uri', 'Unknown URI')}")
                return self._create_success_result(content, post_result, attempt)
                
            except Exception as e:
                logger.warning(f"Post attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    # Exponential backoff: 1s, 2s
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
                    # Reset authentication on auth errors
                    if "auth" in str(e).lower() or "unauthorized" in str(e).lower():
                        self.client = None
                        self.authenticated_user = None
                else:
                    # Final attempt failed
                    error_msg = f"Failed to post after {self.max_retries + 1} attempts: {str(e)}"
                    logger.error(error_msg)
                    return self._create_error_result(content, error_msg, attempt + 1)
        
        # Should not reach here, but safety fallback
        return self._create_error_result(content, "Unknown error occurred", self.max_retries + 1)
    
    def _is_authenticated(self, username: str) -> bool:
        """Check if we have a valid authenticated session"""
        return (self.client is not None and 
                self.authenticated_user == username and
                hasattr(self.client, 'me') and 
                self.client.me is not None)
    
    @circuit_breaker("bluesky_auth")
    @handle_errors("bluesky_social_tool", "authenticate", attempt_recovery=False)
    def _authenticate(self, username: str, password: str) -> None:
        """
        Authenticate with Bluesky using AT Protocol
        
        Args:
            username: Bluesky username (handle or email)
            password: Bluesky password
            
        Raises:
            Exception: If authentication fails
        """
        logger.info(f"Authenticating with Bluesky for user: {username}")
        
        try:
            # Create new client instance
            self.client = Client()
            
            # Login with credentials
            self.client.login(username, password)
            self.authenticated_user = username
            
            logger.info("Successfully authenticated with Bluesky")
            
        except Exception as e:
            self.client = None
            self.authenticated_user = None
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    @circuit_breaker("bluesky_post")
    @handle_errors("bluesky_social_tool", "create_post", attempt_recovery=True)
    def _create_post(self, content: str) -> Dict[str, Any]:
        """
        Create and publish a post to Bluesky
        
        Args:
            content: The content to post
            
        Returns:
            Dict containing post information from Bluesky API
            
        Raises:
            Exception: If posting fails
        """
        if not self.client:
            raise Exception("Not authenticated with Bluesky")
        
        try:
            # Create the post using AT Protocol
            post = self.client.send_post(text=content)
            
            return {
                'uri': post.uri,
                'cid': post.cid,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to create post: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _create_success_result(self, content: str, post_result: Dict[str, Any], retry_count: int) -> Dict[str, Any]:
        """Create a success result dictionary"""
        return {
            'success': True,
            'post_id': post_result.get('uri'),
            'cid': post_result.get('cid'),
            'timestamp': datetime.now().isoformat(),
            'content': content,
            'retry_count': retry_count,
            'error_message': None
        }
    
    def _create_error_result(self, content: str, error_message: str, retry_count: int) -> Dict[str, Any]:
        """Create an error result dictionary"""
        return {
            'success': False,
            'post_id': None,
            'cid': None,
            'timestamp': datetime.now().isoformat(),
            'content': content,
            'retry_count': retry_count,
            'error_message': error_message
        }
    
    async def _arun(self, content: str, username: str, password: str) -> Dict[str, Any]:
        """Async version of _run method"""
        return self._run(content, username, password)