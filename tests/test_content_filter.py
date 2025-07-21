# tests/test_content_filter.py
"""
Unit tests for ContentFilter class
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.services.content_filter import ContentFilter, ContentHistoryItem
from src.models.data_models import GeneratedContent, NewsItem, ContentType


class TestContentFilter:
    """Test cases for ContentFilter functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.content_filter = ContentFilter(
            history_size=10,
            duplicate_threshold=0.75,
            quality_threshold=0.6,
            retention_hours=24
        )
        
        # Sample news item for testing
        self.sample_news = NewsItem(
            headline="Bitcoin Price Analysis",
            summary="Bitcoin shows strong technical indicators",
            source="CryptoNews",
            timestamp=datetime.now(),
            relevance_score=0.9,
            topics=["Bitcoin", "Analysis"]
        )
    
    def create_sample_content(self, text: str, engagement_score: float = 0.8) -> GeneratedContent:
        """Helper method to create sample GeneratedContent"""
        return GeneratedContent(
            text=text,
            hashtags=["#Bitcoin", "#Crypto"],
            engagement_score=engagement_score,
            content_type=ContentType.ANALYSIS,
            source_news=self.sample_news
        )
    
    def test_initialization(self):
        """Test ContentFilter initialization"""
        cf = ContentFilter(
            history_size=50,
            duplicate_threshold=0.8,
            quality_threshold=0.7,
            retention_hours=48
        )
        
        assert len(cf.recent_posts) == 0
        assert cf.duplicate_threshold == 0.8
        assert cf.quality_threshold == 0.7
        assert cf.retention_hours == 48
        assert len(cf.content_hashes) == 0
    
    def test_duplicate_detection_exact_match(self):
        """Test duplicate detection with exact content match"""
        content_text = "Bitcoin analysis shows bullish trends with strong technical indicators #Bitcoin #Crypto"
        content = self.create_sample_content(content_text)
        
        # First content should not be duplicate
        is_duplicate, similarity = self.content_filter._check_duplicates(content_text)
        assert not is_duplicate
        assert similarity == 0.0
        
        # Add to history
        self.content_filter.add_to_history(content)
        
        # Same content should be detected as duplicate
        is_duplicate, similarity = self.content_filter._check_duplicates(content_text)
        assert is_duplicate
        assert similarity == 1.0
    
    def test_duplicate_detection_similar_content(self):
        """Test duplicate detection with similar but not identical content"""
        original_text = "Bitcoin shows strong bullish signals in technical analysis #Bitcoin #Crypto"
        similar_text = "Bitcoin displays strong bullish indicators in technical analysis #Bitcoin #Crypto"
        
        original_content = self.create_sample_content(original_text)
        self.content_filter.add_to_history(original_content)
        
        # Similar content should be detected as duplicate
        is_duplicate, similarity = self.content_filter._check_duplicates(similar_text)
        assert is_duplicate
        assert similarity > 0.75
    
    def test_duplicate_detection_different_content(self):
        """Test that different content is not flagged as duplicate"""
        original_text = "Bitcoin analysis shows bullish trends #Bitcoin"
        different_text = "Ethereum network upgrade completed successfully #Ethereum #DeFi"
        
        original_content = self.create_sample_content(original_text)
        self.content_filter.add_to_history(original_content)
        
        # Different content should not be duplicate
        is_duplicate, similarity = self.content_filter._check_duplicates(different_text)
        assert not is_duplicate
        assert similarity < 0.5
    
    def test_quality_scoring_high_quality(self):
        """Test quality scoring for high-quality content"""
        high_quality_text = "Bitcoin technical analysis reveals strong adoption trends and innovative development in the ecosystem #Bitcoin #Analysis"
        
        score = self.content_filter._calculate_quality_score(high_quality_text)
        assert score > 0.7  # Should be high quality
    
    def test_quality_scoring_low_quality(self):
        """Test quality scoring for low-quality content"""
        low_quality_text = "BITCOIN TO THE MOON!!! 🚀🚀🚀🚀 DIAMOND HANDS HODL!!! #MOON #LAMBO #HODL #DIAMOND #HANDS #CRYPTO"
        
        score = self.content_filter._calculate_quality_score(low_quality_text)
        assert score < 0.5  # Should be low quality
    
    def test_quality_scoring_optimal_length(self):
        """Test quality scoring rewards optimal content length"""
        # Optimal length content (100-200 chars)
        optimal_text = "Bitcoin shows strong technical indicators with increasing adoption and development activity #Bitcoin #Crypto"
        
        # Too short content
        short_text = "Bitcoin up #BTC"
        
        # Too long content
        long_text = "Bitcoin analysis shows extremely detailed technical indicators with comprehensive market data analysis revealing significant bullish trends across multiple timeframes and various technical analysis methodologies indicating strong potential for continued upward price movement #Bitcoin #Crypto #Analysis #Technical #Bullish #Market #Trends #Data"
        
        optimal_score = self.content_filter._calculate_quality_score(optimal_text)
        short_score = self.content_filter._calculate_quality_score(short_text)
        long_score = self.content_filter._calculate_quality_score(long_text)
        
        assert optimal_score > short_score
        assert optimal_score > long_score
    
    def test_content_moderation_appropriate_content(self):
        """Test content moderation with appropriate content"""
        appropriate_text = "Bitcoin technical analysis shows positive development trends #Bitcoin #Analysis"
        
        is_appropriate, details = self.content_filter._moderate_content(appropriate_text)
        assert is_appropriate
        assert details['severity'] == 'none'
        assert len(details['inappropriate_patterns_found']) == 0
    
    def test_content_moderation_inappropriate_content(self):
        """Test content moderation with inappropriate content"""
        inappropriate_texts = [
            "This is a guaranteed profit scam scheme",
            "Pump and dump this coin now!",
            "Risk free investment opportunity",
            "This is financial advice - buy now!"
        ]
        
        for text in inappropriate_texts:
            is_appropriate, details = self.content_filter._moderate_content(text)
            assert not is_appropriate
            assert details['severity'] in ['medium', 'high']
            assert len(details['inappropriate_patterns_found']) > 0
    
    def test_format_validation_valid_content(self):
        """Test format validation with valid content"""
        valid_content = self.create_sample_content(
            "Bitcoin shows strong technical analysis indicators #Bitcoin #Crypto",
            engagement_score=0.8
        )
        
        is_valid, issues = self.content_filter._validate_format(valid_content)
        assert is_valid
        assert len(issues) == 0
    
    def test_format_validation_invalid_content(self):
        """Test format validation with invalid content"""
        # Test content too long - create manually to bypass GeneratedContent validation
        long_content = GeneratedContent.__new__(GeneratedContent)
        long_content.text = "A" * 350  # Exceeds 300 char limit
        long_content.hashtags = ["#Bitcoin", "#Crypto"]
        long_content.engagement_score = 0.8
        long_content.content_type = ContentType.ANALYSIS
        long_content.source_news = self.sample_news
        long_content.created_at = datetime.now()
        long_content.metadata = {}
        
        is_valid, issues = self.content_filter._validate_format(long_content)
        assert not is_valid
        assert any("exceeds 300 character limit" in issue for issue in issues)
        
        # Test content too short
        short_content = self.create_sample_content("Short")
        is_valid, issues = self.content_filter._validate_format(short_content)
        assert not is_valid
        assert any("too short" in issue for issue in issues)
        
        # Test too many hashtags
        many_hashtags_content = GeneratedContent(
            text="Bitcoin analysis with many tags",
            hashtags=["#1", "#2", "#3", "#4", "#5", "#6", "#7", "#8"],  # 8 hashtags
            engagement_score=0.8,
            content_type=ContentType.ANALYSIS,
            source_news=self.sample_news
        )
        is_valid, issues = self.content_filter._validate_format(many_hashtags_content)
        assert not is_valid
        assert any("Too many hashtags" in issue for issue in issues)
    
    def test_comprehensive_filter_content_approved(self):
        """Test comprehensive content filtering with approved content"""
        good_content = self.create_sample_content(
            "Bitcoin technical analysis reveals strong development trends and community adoption #Bitcoin #Analysis",
            engagement_score=0.8
        )
        
        approved, details = self.content_filter.filter_content(good_content)
        assert approved
        assert 'All quality checks passed' in details['reasons']
        assert details['scores']['quality'] >= 0.6
        assert len(details['checks_performed']) == 4
    
    def test_comprehensive_filter_content_rejected_quality(self):
        """Test comprehensive content filtering with low quality content"""
        bad_content = self.create_sample_content(
            "MOON LAMBO!!! 🚀🚀🚀🚀🚀 #MOON #LAMBO #HODL #DIAMOND #HANDS #CRYPTO #BITCOIN",
            engagement_score=0.3
        )
        
        approved, details = self.content_filter.filter_content(bad_content)
        assert not approved
        assert any("Quality score too low" in reason for reason in details['reasons'])
        assert details['scores']['quality'] < 0.6
    
    def test_comprehensive_filter_content_rejected_duplicate(self):
        """Test comprehensive content filtering with duplicate content"""
        original_content = self.create_sample_content(
            "Bitcoin analysis shows strong technical indicators and development trends #Bitcoin #Analysis"
        )
        
        # Add original to history
        self.content_filter.add_to_history(original_content)
        
        # Try to filter very similar content
        similar_content = self.create_sample_content(
            "Bitcoin analysis displays strong technical indicators and development trends #Bitcoin #Analysis"
        )
        
        approved, details = self.content_filter.filter_content(similar_content)
        assert not approved
        assert any("Duplicate content detected" in reason for reason in details['reasons'])
        assert details['scores']['similarity'] > 0.75
    
    def test_comprehensive_filter_content_rejected_inappropriate(self):
        """Test comprehensive content filtering with inappropriate content"""
        inappropriate_content = self.create_sample_content(
            "This guaranteed profit scam will make you rich with no risk involved in this investment scheme"
        )
        
        approved, details = self.content_filter.filter_content(inappropriate_content)
        assert not approved
        assert "Content failed moderation checks" in details['reasons']
        assert details['moderation']['severity'] in ['medium', 'high']
    
    def test_add_to_history(self):
        """Test adding content to history"""
        content = self.create_sample_content(
            "Bitcoin technical analysis shows positive trends #Bitcoin #Analysis"
        )
        
        initial_count = len(self.content_filter.recent_posts)
        self.content_filter.add_to_history(content)
        
        assert len(self.content_filter.recent_posts) == initial_count + 1
        assert len(self.content_filter.content_hashes) == 1
        
        # Check that the history item has correct structure
        history_item = self.content_filter.recent_posts[-1]
        assert isinstance(history_item, ContentHistoryItem)
        assert history_item.content == content.text
        assert history_item.engagement_score == content.engagement_score
        assert history_item.topics == content.source_news.topics
    
    def test_history_size_limit(self):
        """Test that history respects size limit"""
        # Create content filter with small history size
        small_filter = ContentFilter(history_size=3)
        
        # Add more items than the limit
        for i in range(5):
            content = self.create_sample_content(f"Content number {i} with unique text")
            small_filter.add_to_history(content)
        
        # Should only keep the last 3 items
        assert len(small_filter.recent_posts) == 3
        assert small_filter.recent_posts[-1].content.startswith("Content number 4")
    
    def test_get_history_stats_empty(self):
        """Test history statistics with empty history"""
        stats = self.content_filter.get_history_stats()
        
        assert stats['total_items'] == 0
        assert stats['avg_quality'] == 0.0
        assert stats['topics'] == []
    
    def test_get_history_stats_with_data(self):
        """Test history statistics with data"""
        # Add multiple content items
        contents = [
            self.create_sample_content("Bitcoin analysis #Bitcoin", 0.8),
            self.create_sample_content("Ethereum update #Ethereum", 0.7),
            self.create_sample_content("DeFi trends #DeFi", 0.9)
        ]
        
        for content in contents:
            self.content_filter.add_to_history(content)
        
        stats = self.content_filter.get_history_stats()
        
        assert stats['total_items'] == 3
        assert stats['avg_engagement_score'] == 0.8  # (0.8 + 0.7 + 0.9) / 3
        assert len(stats['top_topics']) > 0
        assert 'oldest_item_age_hours' in stats
    
    def test_cleanup_old_content(self):
        """Test cleanup of old content based on retention period"""
        # Create filter with short retention period
        short_retention_filter = ContentFilter(retention_hours=1)
        
        # Add old content by manually creating history item with old timestamp
        old_content = self.create_sample_content("Old content")
        old_time = datetime.now() - timedelta(hours=2)
        
        # Manually create old history item
        old_history_item = ContentHistoryItem(
            content=old_content.text,
            timestamp=old_time,
            content_hash=short_retention_filter._generate_content_hash(old_content.text),
            engagement_score=old_content.engagement_score,
            topics=old_content.source_news.topics
        )
        
        # Add old item directly to history
        short_retention_filter.recent_posts.append(old_history_item)
        short_retention_filter.content_hashes.add(old_history_item.content_hash)
        
        # Verify old content is there
        assert len(short_retention_filter.recent_posts) == 1
        
        # Trigger cleanup by calling filter_content (which calls _cleanup_old_content)
        new_content = self.create_sample_content("New content")
        short_retention_filter.filter_content(new_content)
        
        # Old content should be cleaned up
        assert len(short_retention_filter.recent_posts) == 0  # Old content removed, new not added to history yet
        
        # Now add new content to history
        short_retention_filter.add_to_history(new_content)
        assert len(short_retention_filter.recent_posts) == 1
        assert short_retention_filter.recent_posts[0].content == "New content"
    
    def test_word_similarity_calculation(self):
        """Test Jaccard similarity calculation"""
        # Identical texts
        similarity = self.content_filter._calculate_word_similarity("hello world", "hello world")
        assert similarity == 1.0
        
        # Completely different texts
        similarity = self.content_filter._calculate_word_similarity("hello world", "foo bar")
        assert similarity == 0.0
        
        # Partially similar texts
        similarity = self.content_filter._calculate_word_similarity("hello world test", "hello world example")
        assert 0.0 < similarity < 1.0
        
        # Empty texts
        similarity = self.content_filter._calculate_word_similarity("", "")
        assert similarity == 1.0
        
        # One empty text
        similarity = self.content_filter._calculate_word_similarity("hello", "")
        assert similarity == 0.0
    
    def test_content_hash_generation(self):
        """Test content hash generation for deduplication"""
        # Same content should generate same hash
        hash1 = self.content_filter._generate_content_hash("Hello World")
        hash2 = self.content_filter._generate_content_hash("Hello World")
        assert hash1 == hash2
        
        # Different content should generate different hashes
        hash3 = self.content_filter._generate_content_hash("Different Content")
        assert hash1 != hash3
        
        # Content with different spacing should generate same hash (normalization)
        hash4 = self.content_filter._generate_content_hash("Hello    World")
        hash5 = self.content_filter._generate_content_hash("hello world")
        assert hash4 == hash5
    
    def test_hashtag_balance_scoring(self):
        """Test that quality scoring considers hashtag balance"""
        # Optimal hashtag count (2-4)
        optimal_text = "Bitcoin analysis shows trends #Bitcoin #Analysis #Crypto"
        optimal_score = self.content_filter._calculate_quality_score(optimal_text)
        
        # Too many hashtags
        excessive_text = "Bitcoin analysis #1 #2 #3 #4 #5 #6 #7 #8"
        excessive_score = self.content_filter._calculate_quality_score(excessive_text)
        
        # No hashtags
        no_hashtags_text = "Bitcoin analysis shows trends"
        no_hashtags_score = self.content_filter._calculate_quality_score(no_hashtags_text)
        
        assert optimal_score > excessive_score
        assert optimal_score > no_hashtags_score
    
    def test_emoji_balance_scoring(self):
        """Test that quality scoring considers emoji balance"""
        # Good emoji usage (1-3)
        good_emoji_text = "Bitcoin analysis shows trends 📈 #Bitcoin"
        good_score = self.content_filter._calculate_quality_score(good_emoji_text)
        
        # Excessive emoji usage
        excessive_emoji_text = "Bitcoin 🚀🚀🚀🚀🚀🚀 analysis #Bitcoin"
        excessive_score = self.content_filter._calculate_quality_score(excessive_emoji_text)
        
        assert good_score > excessive_score
    
    def test_caps_ratio_scoring(self):
        """Test that quality scoring penalizes excessive capitalization"""
        # Normal capitalization
        normal_text = "Bitcoin analysis shows positive trends #Bitcoin"
        normal_score = self.content_filter._calculate_quality_score(normal_text)
        
        # Excessive capitalization
        caps_text = "BITCOIN ANALYSIS SHOWS POSITIVE TRENDS #BITCOIN"
        caps_score = self.content_filter._calculate_quality_score(caps_text)
        
        assert normal_score > caps_score


class TestContentHistoryItem:
    """Test cases for ContentHistoryItem dataclass"""
    
    def test_content_history_item_creation(self):
        """Test ContentHistoryItem creation"""
        item = ContentHistoryItem(
            content="Test content",
            timestamp=datetime.now(),
            content_hash="abc123",
            engagement_score=0.8,
            topics=["Bitcoin", "Analysis"]
        )
        
        assert item.content == "Test content"
        assert item.content_hash == "abc123"
        assert item.engagement_score == 0.8
        assert item.topics == ["Bitcoin", "Analysis"]
        assert isinstance(item.timestamp, datetime)


if __name__ == "__main__":
    pytest.main([__file__])