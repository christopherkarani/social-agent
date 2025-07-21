# tests/test_config.py
"""
Unit tests for configuration management
"""
import os
import pytest
from unittest.mock import patch
from src.config.agent_config import AgentConfig


class TestAgentConfig:
    """Test cases for AgentConfig class"""
    
    def test_default_config_creation(self):
        """Test creating config with default values"""
        config = AgentConfig()
        
        assert config.posting_interval_minutes == 30
        assert config.max_execution_time_minutes == 25
        assert config.max_post_length == 300
        assert config.min_engagement_score == 0.7
        assert config.duplicate_threshold == 0.8
        assert config.max_retries == 3
        assert "Bitcoin" in config.content_themes
        assert "Ethereum" in config.content_themes
    
    def test_config_with_custom_values(self):
        """Test creating config with custom values"""
        config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_pass",
            posting_interval_minutes=60,
            max_post_length=280
        )
        
        assert config.perplexity_api_key == "test_key"
        assert config.bluesky_username == "test_user"
        assert config.bluesky_password == "test_pass"
        assert config.posting_interval_minutes == 60
        assert config.max_post_length == 280
    
    @patch.dict(os.environ, {
        'PERPLEXITY_API_KEY': 'env_perplexity_key',
        'BLUESKY_USERNAME': 'env_username',
        'BLUESKY_PASSWORD': 'env_password',
        'POSTING_INTERVAL_MINUTES': '45',
        'MAX_POST_LENGTH': '280',
        'CONTENT_THEMES': 'Bitcoin,Ethereum,DeFi',
        'MIN_ENGAGEMENT_SCORE': '0.8',
        'DUPLICATE_THRESHOLD': '0.9'
    })
    def test_config_from_env(self):
        """Test loading configuration from environment variables"""
        config = AgentConfig.from_env()
        
        assert config.perplexity_api_key == 'env_perplexity_key'
        assert config.bluesky_username == 'env_username'
        assert config.bluesky_password == 'env_password'
        assert config.posting_interval_minutes == 45
        assert config.max_post_length == 280
        assert config.content_themes == ['Bitcoin', 'Ethereum', 'DeFi']
        assert config.min_engagement_score == 0.8
        assert config.duplicate_threshold == 0.9
    
    @patch.dict(os.environ, {}, clear=True)
    def test_config_from_env_defaults(self):
        """Test loading configuration from environment with default values"""
        config = AgentConfig.from_env()
        
        assert config.perplexity_api_key == ''
        assert config.bluesky_username == ''
        assert config.bluesky_password == ''
        assert config.posting_interval_minutes == 30
        assert config.max_post_length == 300
    
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        config = AgentConfig(
            perplexity_api_key="valid_key",
            bluesky_username="valid_user",
            bluesky_password="valid_pass"
        )
        
        assert config.validate() is True
    
    def test_config_validation_missing_api_key(self):
        """Test validation failure with missing API key"""
        config = AgentConfig(
            bluesky_username="valid_user",
            bluesky_password="valid_pass"
        )
        
        assert config.validate() is False
    
    def test_config_validation_missing_credentials(self):
        """Test validation failure with missing Bluesky credentials"""
        config = AgentConfig(
            perplexity_api_key="valid_key"
        )
        
        assert config.validate() is False
    
    def test_config_validation_invalid_ranges(self):
        """Test validation failure with invalid numeric ranges"""
        config = AgentConfig(
            perplexity_api_key="valid_key",
            bluesky_username="valid_user",
            bluesky_password="valid_pass",
            posting_interval_minutes=0,  # Invalid
            min_engagement_score=1.5,    # Invalid
            duplicate_threshold=-0.1,    # Invalid
            max_retries=-1               # Invalid
        )
        
        assert config.validate() is False
    
    def test_config_validation_empty_themes(self):
        """Test validation failure with empty content themes"""
        config = AgentConfig(
            perplexity_api_key="valid_key",
            bluesky_username="valid_user",
            bluesky_password="valid_pass",
            content_themes=[]  # Invalid
        )
        
        assert config.validate() is False
    
    def test_config_to_dict(self):
        """Test converting configuration to dictionary"""
        config = AgentConfig(
            perplexity_api_key="secret_key",
            bluesky_username="test_user",
            bluesky_password="secret_pass"
        )
        
        config_dict = config.to_dict()
        
        # Check that sensitive data is masked
        assert config_dict['perplexity_api_key'] == '***'
        assert config_dict['bluesky_password'] == '***'
        assert config_dict['bluesky_username'] == 'test_user'
        assert config_dict['posting_interval_minutes'] == 30
    
    def test_config_to_dict_empty_secrets(self):
        """Test converting configuration with empty secrets to dictionary"""
        config = AgentConfig()
        config_dict = config.to_dict()
        
        # Check that empty secrets remain empty
        assert config_dict['perplexity_api_key'] == ''
        assert config_dict['bluesky_password'] == ''