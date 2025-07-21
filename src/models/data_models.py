# src/models/data_models.py
"""
Data models for the Bluesky crypto agent
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ContentType(Enum):
    """Content type enumeration"""
    NEWS = "news"
    ANALYSIS = "analysis"
    OPINION = "opinion"
    MARKET_UPDATE = "market_update"


@dataclass
class NewsItem:
    """
    Data model for cryptocurrency news items retrieved from Perplexity API
    """
    headline: str
    summary: str
    source: str
    timestamp: datetime
    relevance_score: float
    topics: List[str]
    url: Optional[str] = None
    raw_content: Optional[str] = None
    
    def __post_init__(self):
        """Validate data after initialization"""
        if not self.headline:
            raise ValueError("headline cannot be empty")
        if not self.summary:
            raise ValueError("summary cannot be empty")
        if not self.source:
            raise ValueError("source cannot be empty")
        if not (0.0 <= self.relevance_score <= 1.0):
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        if not self.topics:
            raise ValueError("topics cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'headline': self.headline,
            'summary': self.summary,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'relevance_score': self.relevance_score,
            'topics': self.topics,
            'url': self.url,
            'raw_content': self.raw_content
        }


@dataclass
class GeneratedContent:
    """
    Data model for AI-generated social media content
    """
    text: str
    hashtags: List[str]
    engagement_score: float
    content_type: ContentType
    source_news: NewsItem
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization"""
        if not self.text:
            raise ValueError("text cannot be empty")
        if len(self.text) > 300:  # Bluesky character limit
            raise ValueError("text exceeds 300 character limit")
        if not (0.0 <= self.engagement_score <= 1.0):
            raise ValueError("engagement_score must be between 0.0 and 1.0")
        if not isinstance(self.content_type, ContentType):
            raise ValueError("content_type must be a ContentType enum")
    
    @property
    def character_count(self) -> int:
        """Get character count of the content"""
        return len(self.text)
    
    @property
    def hashtag_count(self) -> int:
        """Get number of hashtags"""
        return len(self.hashtags)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'text': self.text,
            'hashtags': self.hashtags,
            'engagement_score': self.engagement_score,
            'content_type': self.content_type.value,
            'source_news': self.source_news.to_dict(),
            'created_at': self.created_at.isoformat(),
            'character_count': self.character_count,
            'hashtag_count': self.hashtag_count,
            'metadata': self.metadata
        }


@dataclass
class PostResult:
    """
    Data model for social media posting results
    """
    success: bool
    post_id: Optional[str]
    timestamp: datetime
    content: GeneratedContent
    error_message: Optional[str] = None
    retry_count: int = 0
    response_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate data after initialization"""
        if self.success and not self.post_id:
            raise ValueError("post_id is required when success is True")
        if not self.success and not self.error_message:
            raise ValueError("error_message is required when success is False")
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")
    
    @property
    def is_successful(self) -> bool:
        """Check if the post was successful"""
        return self.success and self.post_id is not None
    
    @property
    def execution_time(self) -> str:
        """Get formatted execution time"""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'success': self.success,
            'post_id': self.post_id,
            'timestamp': self.timestamp.isoformat(),
            'content': self.content.to_dict(),
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'response_data': self.response_data,
            'execution_time': self.execution_time
        }


# Re-export AgentConfig from agent_config module for convenience
from ..config.agent_config import AgentConfig

__all__ = [
    'NewsItem', 
    'GeneratedContent', 
    'PostResult', 
    'AgentConfig', 
    'ContentType'
]