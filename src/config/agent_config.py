# src/config/agent_config.py
"""
Configuration management for the Bluesky crypto agent with environment variable support
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """
    Configuration class for the Bluesky crypto agent with environment variable support
    """
    # API Configuration
    perplexity_api_key: str = ""
    bluesky_username: str = ""
    bluesky_password: str = ""
    
    # Scheduling Configuration
    posting_interval_minutes: int = 30
    max_execution_time_minutes: int = 25
    
    # Content Settings
    max_post_length: int = 300
    content_themes: List[str] = field(default_factory=lambda: [
        "Bitcoin", "Ethereum", "DeFi", "NFTs", "Altcoins", "Crypto News"
    ])
    
    # Quality Control Settings
    min_engagement_score: float = 0.7
    duplicate_threshold: float = 0.8
    max_retries: int = 3
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file_path: str = "logs/bluesky_agent.log"
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """
        Create configuration from environment variables
        """
        logger.info("Loading configuration from environment variables")
        
        # Load content themes from environment (comma-separated)
        themes_env = os.getenv('CONTENT_THEMES', 'Bitcoin,Ethereum,DeFi,NFTs,Altcoins,Crypto News')
        content_themes = [theme.strip() for theme in themes_env.split(',')]
        
        config = cls(
            # API Configuration
            perplexity_api_key=os.getenv('PERPLEXITY_API_KEY', ''),
            bluesky_username=os.getenv('BLUESKY_USERNAME', ''),
            bluesky_password=os.getenv('BLUESKY_PASSWORD', ''),
            
            # Scheduling Configuration
            posting_interval_minutes=int(os.getenv('POSTING_INTERVAL_MINUTES', '30')),
            max_execution_time_minutes=int(os.getenv('MAX_EXECUTION_TIME_MINUTES', '25')),
            
            # Content Settings
            max_post_length=int(os.getenv('MAX_POST_LENGTH', '300')),
            content_themes=content_themes,
            
            # Quality Control Settings
            min_engagement_score=float(os.getenv('MIN_ENGAGEMENT_SCORE', '0.7')),
            duplicate_threshold=float(os.getenv('DUPLICATE_THRESHOLD', '0.8')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            
            # Logging Configuration
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file_path=os.getenv('LOG_FILE_PATH', 'logs/bluesky_agent.log')
        )
        
        return config
    
    def validate(self) -> bool:
        """
        Validate the configuration settings
        """
        errors = []
        
        # Check required API keys
        if not self.perplexity_api_key:
            errors.append("PERPLEXITY_API_KEY is required")
            
        if not self.bluesky_username:
            errors.append("BLUESKY_USERNAME is required")
            
        if not self.bluesky_password:
            errors.append("BLUESKY_PASSWORD is required")
            
        # Validate numeric ranges
        if self.posting_interval_minutes < 1:
            errors.append("posting_interval_minutes must be at least 1")
            
        if self.max_execution_time_minutes < 1:
            errors.append("max_execution_time_minutes must be at least 1")
            
        if self.max_post_length < 50:
            errors.append("max_post_length must be at least 50 characters")
            
        if not (0.0 <= self.min_engagement_score <= 1.0):
            errors.append("min_engagement_score must be between 0.0 and 1.0")
            
        if not (0.0 <= self.duplicate_threshold <= 1.0):
            errors.append("duplicate_threshold must be between 0.0 and 1.0")
            
        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")
            
        # Validate content themes
        if not self.content_themes:
            errors.append("content_themes cannot be empty")
            
        if errors:
            for error in errors:
                logger.error(f"Configuration validation error: {error}")
            return False
            
        logger.info("Configuration validation passed")
        return True
    
    def ensure_log_directory(self):
        """Ensure the log directory exists"""
        log_path = Path(self.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            'perplexity_api_key': '***' if self.perplexity_api_key else '',
            'bluesky_username': self.bluesky_username,
            'bluesky_password': '***' if self.bluesky_password else '',
            'posting_interval_minutes': self.posting_interval_minutes,
            'max_execution_time_minutes': self.max_execution_time_minutes,
            'max_post_length': self.max_post_length,
            'content_themes': self.content_themes,
            'min_engagement_score': self.min_engagement_score,
            'duplicate_threshold': self.duplicate_threshold,
            'max_retries': self.max_retries,
            'log_level': self.log_level,
            'log_file_path': self.log_file_path
        }