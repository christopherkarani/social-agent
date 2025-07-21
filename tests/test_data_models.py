# tests/test_data_models.py
"""
Unit tests for data models
"""
import pytest
from datetime import datetime
from src.models.data_models import NewsItem, GeneratedContent, PostResult, ContentType


class TestNewsItem:
    """Test cases for NewsItem data model"""
    
    def test_valid_news_item_creation(self):
        """Test creating a valid NewsItem"""
        news_item = NewsItem(
            headline="Bitcoin Reaches New High",
            summary="Bitcoin price surged to $50,000 today",
            source="CryptoNews",
            timestamp=datetime.now(),
            relevance_score=0.9,
            topics=["Bitcoin", "Price"],
            url="https://example.com/news"
        )
        
        assert news_item.headline == "Bitcoin Reaches New High"
        assert news_item.summary == "Bitcoin price surged to $50,000 today"
        assert news_item.source == "CryptoNews"
        assert news_item.relevance_score == 0.9
        assert news_item.topics == ["Bitcoin", "Price"]
        assert news_item.url == "https://example.com/news"
    
    def test_news_item_validation_empty_headline(self):
        """Test NewsItem validation with empty headline"""
        with pytest.raises(ValueError, match="headline cannot be empty"):
            NewsItem(
                headline="",
                summary="Valid summary",
                source="Valid source",
                timestamp=datetime.now(),
                relevance_score=0.8,
                topics=["Bitcoin"]
            )
    
    def test_news_item_validation_empty_summary(self):
        """Test NewsItem validation with empty summary"""
        with pytest.raises(ValueError, match="summary cannot be empty"):
            NewsItem(
                headline="Valid headline",
                summary="",
                source="Valid source",
                timestamp=datetime.now(),
                relevance_score=0.8,
                topics=["Bitcoin"]
            )
    
    def test_news_item_validation_invalid_relevance_score(self):
        """Test NewsItem validation with invalid relevance score"""
        with pytest.raises(ValueError, match="relevance_score must be between 0.0 and 1.0"):
            NewsItem(
                headline="Valid headline",
                summary="Valid summary",
                source="Valid source",
                timestamp=datetime.now(),
                relevance_score=1.5,  # Invalid
                topics=["Bitcoin"]
            )
    
    def test_news_item_validation_empty_topics(self):
        """Test NewsItem validation with empty topics"""
        with pytest.raises(ValueError, match="topics cannot be empty"):
            NewsItem(
                headline="Valid headline",
                summary="Valid summary",
                source="Valid source",
                timestamp=datetime.now(),
                relevance_score=0.8,
                topics=[]  # Invalid
            )
    
    def test_news_item_to_dict(self):
        """Test converting NewsItem to dictionary"""
        timestamp = datetime.now()
        news_item = NewsItem(
            headline="Test headline",
            summary="Test summary",
            source="Test source",
            timestamp=timestamp,
            relevance_score=0.8,
            topics=["Bitcoin", "Test"]
        )
        
        result = news_item.to_dict()
        
        assert result['headline'] == "Test headline"
        assert result['summary'] == "Test summary"
        assert result['source'] == "Test source"
        assert result['timestamp'] == timestamp.isoformat()
        assert result['relevance_score'] == 0.8
        assert result['topics'] == ["Bitcoin", "Test"]


class TestGeneratedContent:
    """Test cases for GeneratedContent data model"""
    
    def create_sample_news_item(self):
        """Helper method to create a sample NewsItem"""
        return NewsItem(
            headline="Test News",
            summary="Test summary",
            source="Test Source",
            timestamp=datetime.now(),
            relevance_score=0.8,
            topics=["Bitcoin"]
        )
    
    def test_valid_generated_content_creation(self):
        """Test creating valid GeneratedContent"""
        news_item = self.create_sample_news_item()
        content = GeneratedContent(
            text="Bitcoin is mooning! 🚀 #Bitcoin #Crypto",
            hashtags=["#Bitcoin", "#Crypto"],
            engagement_score=0.85,
            content_type=ContentType.NEWS,
            source_news=news_item
        )
        
        assert content.text == "Bitcoin is mooning! 🚀 #Bitcoin #Crypto"
        assert content.hashtags == ["#Bitcoin", "#Crypto"]
        assert content.engagement_score == 0.85
        assert content.content_type == ContentType.NEWS
        assert content.source_news == news_item
        assert content.character_count == len(content.text)
        assert content.hashtag_count == 2
    
    def test_generated_content_validation_empty_text(self):
        """Test GeneratedContent validation with empty text"""
        news_item = self.create_sample_news_item()
        
        with pytest.raises(ValueError, match="text cannot be empty"):
            GeneratedContent(
                text="",
                hashtags=["#Bitcoin"],
                engagement_score=0.8,
                content_type=ContentType.NEWS,
                source_news=news_item
            )
    
    def test_generated_content_validation_text_too_long(self):
        """Test GeneratedContent validation with text exceeding character limit"""
        news_item = self.create_sample_news_item()
        long_text = "x" * 301  # Exceeds 300 character limit
        
        with pytest.raises(ValueError, match="text exceeds 300 character limit"):
            GeneratedContent(
                text=long_text,
                hashtags=["#Bitcoin"],
                engagement_score=0.8,
                content_type=ContentType.NEWS,
                source_news=news_item
            )
    
    def test_generated_content_validation_invalid_engagement_score(self):
        """Test GeneratedContent validation with invalid engagement score"""
        news_item = self.create_sample_news_item()
        
        with pytest.raises(ValueError, match="engagement_score must be between 0.0 and 1.0"):
            GeneratedContent(
                text="Valid text",
                hashtags=["#Bitcoin"],
                engagement_score=1.5,  # Invalid
                content_type=ContentType.NEWS,
                source_news=news_item
            )
    
    def test_generated_content_to_dict(self):
        """Test converting GeneratedContent to dictionary"""
        news_item = self.create_sample_news_item()
        content = GeneratedContent(
            text="Test content",
            hashtags=["#Test"],
            engagement_score=0.8,
            content_type=ContentType.ANALYSIS,
            source_news=news_item
        )
        
        result = content.to_dict()
        
        assert result['text'] == "Test content"
        assert result['hashtags'] == ["#Test"]
        assert result['engagement_score'] == 0.8
        assert result['content_type'] == "analysis"
        assert 'source_news' in result
        assert result['character_count'] == len("Test content")
        assert result['hashtag_count'] == 1


class TestPostResult:
    """Test cases for PostResult data model"""
    
    def create_sample_generated_content(self):
        """Helper method to create sample GeneratedContent"""
        news_item = NewsItem(
            headline="Test News",
            summary="Test summary",
            source="Test Source",
            timestamp=datetime.now(),
            relevance_score=0.8,
            topics=["Bitcoin"]
        )
        
        return GeneratedContent(
            text="Test content",
            hashtags=["#Test"],
            engagement_score=0.8,
            content_type=ContentType.NEWS,
            source_news=news_item
        )
    
    def test_successful_post_result_creation(self):
        """Test creating successful PostResult"""
        content = self.create_sample_generated_content()
        timestamp = datetime.now()
        
        result = PostResult(
            success=True,
            post_id="12345",
            timestamp=timestamp,
            content=content
        )
        
        assert result.success is True
        assert result.post_id == "12345"
        assert result.timestamp == timestamp
        assert result.content == content
        assert result.is_successful is True
        assert result.retry_count == 0
    
    def test_failed_post_result_creation(self):
        """Test creating failed PostResult"""
        content = self.create_sample_generated_content()
        timestamp = datetime.now()
        
        result = PostResult(
            success=False,
            post_id=None,
            timestamp=timestamp,
            content=content,
            error_message="API error occurred",
            retry_count=2
        )
        
        assert result.success is False
        assert result.post_id is None
        assert result.error_message == "API error occurred"
        assert result.retry_count == 2
        assert result.is_successful is False
    
    def test_post_result_validation_success_without_post_id(self):
        """Test PostResult validation when success is True but post_id is missing"""
        content = self.create_sample_generated_content()
        
        with pytest.raises(ValueError, match="post_id is required when success is True"):
            PostResult(
                success=True,
                post_id=None,  # Invalid for successful post
                timestamp=datetime.now(),
                content=content
            )
    
    def test_post_result_validation_failure_without_error_message(self):
        """Test PostResult validation when success is False but error_message is missing"""
        content = self.create_sample_generated_content()
        
        with pytest.raises(ValueError, match="error_message is required when success is False"):
            PostResult(
                success=False,
                post_id=None,
                timestamp=datetime.now(),
                content=content
                # Missing error_message
            )
    
    def test_post_result_validation_negative_retry_count(self):
        """Test PostResult validation with negative retry count"""
        content = self.create_sample_generated_content()
        
        with pytest.raises(ValueError, match="retry_count cannot be negative"):
            PostResult(
                success=False,
                post_id=None,
                timestamp=datetime.now(),
                content=content,
                error_message="Error",
                retry_count=-1  # Invalid
            )
    
    def test_post_result_to_dict(self):
        """Test converting PostResult to dictionary"""
        content = self.create_sample_generated_content()
        timestamp = datetime.now()
        
        result = PostResult(
            success=True,
            post_id="12345",
            timestamp=timestamp,
            content=content,
            retry_count=1
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['success'] is True
        assert result_dict['post_id'] == "12345"
        assert result_dict['timestamp'] == timestamp.isoformat()
        assert 'content' in result_dict
        assert result_dict['retry_count'] == 1
        assert 'execution_time' in result_dict