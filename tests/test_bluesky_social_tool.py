# tests/test_bluesky_social_tool.py
"""
Unit tests for BlueskySocialTool
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.tools.bluesky_social_tool import BlueskySocialTool, BlueskySocialInput


class TestBlueskySocialTool:
    """Test cases for BlueskySocialTool"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tool = BlueskySocialTool()
        self.test_content = "Test crypto post about Bitcoin! #BTC #crypto"
        self.test_username = "testuser.bsky.social"
        self.test_password = "testpassword"
    
    def test_tool_initialization(self):
        """Test tool initialization with correct properties"""
        assert self.tool.name == "bluesky_publisher"
        assert "Posts content to Bluesky" in self.tool.description
        assert self.tool.max_retries == 2
        assert self.tool.client is None
        assert self.tool.authenticated_user is None
    
    def test_tool_initialization_custom_retries(self):
        """Test tool initialization with custom retry count"""
        tool = BlueskySocialTool(max_retries=5)
        assert tool.max_retries == 5
    
    def test_input_schema(self):
        """Test the input schema validation"""
        # Valid input
        valid_input = BlueskySocialInput(
            content=self.test_content,
            username=self.test_username,
            password=self.test_password
        )
        assert valid_input.content == self.test_content
        assert valid_input.username == self.test_username
        assert valid_input.password == self.test_password
    
    def test_content_length_validation(self):
        """Test content length validation (300 character limit)"""
        long_content = "x" * 301  # Exceeds 300 character limit
        
        result = self.tool._run(long_content, self.test_username, self.test_password)
        
        assert result['success'] is False
        assert "exceeds Bluesky character limit" in result['error_message']
        assert result['retry_count'] == 0
    
    def test_content_length_validation_at_limit(self):
        """Test content at exactly 300 characters is accepted"""
        content_300 = "x" * 300  # Exactly 300 characters
        
        with patch.object(self.tool, '_authenticate'), \
             patch.object(self.tool, '_create_post', return_value={'uri': 'test_uri', 'cid': 'test_cid'}):
            result = self.tool._run(content_300, self.test_username, self.test_password)
            
            assert result['success'] is True
    
    @patch('src.tools.bluesky_social_tool.Client')
    def test_successful_authentication(self, mock_client_class):
        """Test successful authentication with Bluesky"""
        mock_client = Mock()
        mock_client.login.return_value = None
        mock_client.me = {'handle': self.test_username}
        mock_client_class.return_value = mock_client
        
        self.tool._authenticate(self.test_username, self.test_password)
        
        assert self.tool.client == mock_client
        assert self.tool.authenticated_user == self.test_username
        mock_client.login.assert_called_once_with(self.test_username, self.test_password)
    
    @patch('src.tools.bluesky_social_tool.Client')
    def test_authentication_failure(self, mock_client_class):
        """Test authentication failure handling"""
        mock_client = Mock()
        mock_client.login.side_effect = Exception("Invalid credentials")
        mock_client_class.return_value = mock_client
        
        with pytest.raises(Exception, match="Authentication failed"):
            self.tool._authenticate(self.test_username, self.test_password)
        
        assert self.tool.client is None
        assert self.tool.authenticated_user is None
    
    def test_is_authenticated_true(self):
        """Test is_authenticated returns True for valid session"""
        mock_client = Mock()
        mock_client.me = {'handle': self.test_username}
        
        self.tool.client = mock_client
        self.tool.authenticated_user = self.test_username
        
        assert self.tool._is_authenticated(self.test_username) is True
    
    def test_is_authenticated_false_no_client(self):
        """Test is_authenticated returns False when no client"""
        assert self.tool._is_authenticated(self.test_username) is False
    
    def test_is_authenticated_false_different_user(self):
        """Test is_authenticated returns False for different user"""
        mock_client = Mock()
        mock_client.me = {'handle': 'other_user'}
        
        self.tool.client = mock_client
        self.tool.authenticated_user = 'other_user'
        
        assert self.tool._is_authenticated(self.test_username) is False
    
    def test_create_post_success(self):
        """Test successful post creation"""
        mock_client = Mock()
        mock_post_result = Mock()
        mock_post_result.uri = "at://test_uri"
        mock_post_result.cid = "test_cid"
        mock_client.send_post.return_value = mock_post_result
        
        self.tool.client = mock_client
        
        result = self.tool._create_post(self.test_content)
        
        assert result['uri'] == "at://test_uri"
        assert result['cid'] == "test_cid"
        assert 'timestamp' in result
        mock_client.send_post.assert_called_once_with(text=self.test_content)
    
    def test_create_post_no_client(self):
        """Test create_post fails when not authenticated"""
        with pytest.raises(Exception, match="Not authenticated"):
            self.tool._create_post(self.test_content)
    
    def test_create_post_api_failure(self):
        """Test create_post handles API failures"""
        mock_client = Mock()
        mock_client.send_post.side_effect = Exception("API Error")
        
        self.tool.client = mock_client
        
        with pytest.raises(Exception, match="Failed to create post"):
            self.tool._create_post(self.test_content)
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_successful_post_with_retry(self, mock_sleep):
        """Test successful posting after initial failure"""
        with patch.object(self.tool, '_authenticate') as mock_auth, \
             patch.object(self.tool, '_is_authenticated', side_effect=[False, True]) as mock_is_auth, \
             patch.object(self.tool, '_create_post', side_effect=[Exception("Network error"), {'uri': 'test_uri', 'cid': 'test_cid'}]) as mock_create:
            
            result = self.tool._run(self.test_content, self.test_username, self.test_password)
            
            assert result['success'] is True
            assert result['post_id'] == 'test_uri'
            assert result['retry_count'] == 1
            assert mock_sleep.called  # Verify retry delay was used
    
    @patch('time.sleep')
    def test_max_retries_exceeded(self, mock_sleep):
        """Test behavior when max retries are exceeded"""
        with patch.object(self.tool, '_authenticate'), \
             patch.object(self.tool, '_is_authenticated', return_value=True), \
             patch.object(self.tool, '_create_post', side_effect=Exception("Persistent error")):
            
            result = self.tool._run(self.test_content, self.test_username, self.test_password)
            
            assert result['success'] is False
            assert "Failed to post after 3 attempts" in result['error_message']
            assert result['retry_count'] == 3
    
    @patch('time.sleep')
    def test_authentication_error_resets_client(self, mock_sleep):
        """Test that authentication errors reset the client"""
        with patch.object(self.tool, '_authenticate') as mock_auth, \
             patch.object(self.tool, '_is_authenticated', return_value=False), \
             patch.object(self.tool, '_create_post', side_effect=[Exception("unauthorized"), {'uri': 'test_uri', 'cid': 'test_cid'}]):
            
            # Set initial client state
            self.tool.client = Mock()
            self.tool.authenticated_user = "old_user"
            
            result = self.tool._run(self.test_content, self.test_username, self.test_password)
            
            # Verify client was reset after auth error
            assert mock_auth.call_count >= 2  # Called multiple times due to reset
    
    def test_create_success_result(self):
        """Test creation of success result dictionary"""
        post_result = {'uri': 'test_uri', 'cid': 'test_cid'}
        
        result = self.tool._create_success_result(self.test_content, post_result, 1)
        
        assert result['success'] is True
        assert result['post_id'] == 'test_uri'
        assert result['cid'] == 'test_cid'
        assert result['content'] == self.test_content
        assert result['retry_count'] == 1
        assert result['error_message'] is None
        assert 'timestamp' in result
    
    def test_create_error_result(self):
        """Test creation of error result dictionary"""
        error_msg = "Test error message"
        
        result = self.tool._create_error_result(self.test_content, error_msg, 2)
        
        assert result['success'] is False
        assert result['post_id'] is None
        assert result['cid'] is None
        assert result['content'] == self.test_content
        assert result['retry_count'] == 2
        assert result['error_message'] == error_msg
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_async_run(self):
        """Test async version of run method"""
        with patch.object(self.tool, '_run', return_value={'success': True}) as mock_run:
            result = await self.tool._arun(self.test_content, self.test_username, self.test_password)
            
            assert result['success'] is True
            mock_run.assert_called_once_with(self.test_content, self.test_username, self.test_password)
    
    def test_exponential_backoff_timing(self):
        """Test that retry delays follow exponential backoff pattern"""
        with patch('time.sleep') as mock_sleep, \
             patch.object(self.tool, '_authenticate'), \
             patch.object(self.tool, '_is_authenticated', return_value=True), \
             patch.object(self.tool, '_create_post', side_effect=Exception("Network error")):
            
            self.tool._run(self.test_content, self.test_username, self.test_password)
            
            # Verify exponential backoff: 1s, 2s
            expected_delays = [1, 2]
            actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_delays == expected_delays


class TestBlueskySocialToolIntegration:
    """Integration-style tests for BlueskySocialTool"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tool = BlueskySocialTool(max_retries=1)  # Reduce retries for faster tests
    
    def test_full_workflow_success(self):
        """Test complete successful workflow from authentication to posting"""
        test_content = "Integration test post #crypto"
        test_username = "test.bsky.social"
        test_password = "testpass"
        
        with patch('src.tools.bluesky_social_tool.Client') as mock_client_class:
            # Mock successful client
            mock_client = Mock()
            mock_client.login.return_value = None
            mock_client.me = {'handle': test_username}
            
            mock_post_result = Mock()
            mock_post_result.uri = "at://test_uri_integration"
            mock_post_result.cid = "test_cid_integration"
            mock_client.send_post.return_value = mock_post_result
            
            mock_client_class.return_value = mock_client
            
            # Execute the full workflow
            result = self.tool._run(test_content, test_username, test_password)
            
            # Verify complete success
            assert result['success'] is True
            assert result['post_id'] == "at://test_uri_integration"
            assert result['cid'] == "test_cid_integration"
            assert result['content'] == test_content
            assert result['retry_count'] == 0
            
            # Verify API calls were made correctly
            mock_client.login.assert_called_once_with(test_username, test_password)
            mock_client.send_post.assert_called_once_with(text=test_content)
    
    def test_full_workflow_with_recovery(self):
        """Test workflow with initial failure and successful recovery"""
        test_content = "Recovery test post"
        test_username = "test.bsky.social"
        test_password = "testpass"
        
        with patch('src.tools.bluesky_social_tool.Client') as mock_client_class, \
             patch('time.sleep'):  # Speed up test
            
            mock_client = Mock()
            mock_client.login.return_value = None
            mock_client.me = {'handle': test_username}
            
            # First call fails, second succeeds
            mock_post_result = Mock()
            mock_post_result.uri = "at://recovery_uri"
            mock_post_result.cid = "recovery_cid"
            mock_client.send_post.side_effect = [Exception("Temporary failure"), mock_post_result]
            
            mock_client_class.return_value = mock_client
            
            result = self.tool._run(test_content, test_username, test_password)
            
            # Verify successful recovery
            assert result['success'] is True
            assert result['post_id'] == "at://recovery_uri"
            assert result['retry_count'] == 1
            assert mock_client.send_post.call_count == 2