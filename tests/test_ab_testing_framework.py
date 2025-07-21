# tests/test_ab_testing_framework.py
"""
Tests for A/B Testing Framework
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.services.ab_testing_framework import (
    ABTestingFramework, TestVariant, ContentStrategy, TestStatus,
    TestMetrics, ABTest, StatisticalAnalyzer, create_ab_testing_framework
)
from src.models.data_models import GeneratedContent, PostResult, NewsItem, ContentType
from src.config.agent_config import AgentConfig


@pytest.fixture
def sample_config():
    """Create sample configuration for testing"""
    return AgentConfig(
        perplexity_api_key="test_key",
        bluesky_username="test_user",
        bluesky_password="test_pass",
        max_post_length=300
    )


@pytest.fixture
def sample_news_item():
    """Create sample news item for testing"""
    return NewsItem(
        headline="Bitcoin Surges to New High",
        summary="Bitcoin has reached a new all-time high of $75,000 amid institutional adoption.",
        source="CryptoNews",
        timestamp=datetime.now(),
        relevance_score=0.9,
        topics=["Bitcoin", "Price", "Institutional"]
    )


@pytest.fixture
def sample_generated_content(sample_news_item):
    """Create sample generated content for testing"""
    return GeneratedContent(
        text="🚨 BREAKING: Bitcoin hits $75K! Institutional money is flooding in 📈",
        hashtags=["#Bitcoin", "#BTC", "#Crypto"],
        engagement_score=0.85,
        content_type=ContentType.NEWS,
        source_news=sample_news_item,
        metadata={"generation_strategy": "viral_hooks"}
    )


@pytest.fixture
def sample_post_result(sample_generated_content):
    """Create sample post result for testing"""
    return PostResult(
        success=True,
        post_id="post_123",
        timestamp=datetime.now(),
        content=sample_generated_content
    )


class TestTestVariant:
    """Test TestVariant class"""
    
    def test_create_test_variant(self):
        """Test creating a test variant"""
        variant = TestVariant(
            id="test_variant",
            name="Test Variant",
            strategy=ContentStrategy.VIRAL_HOOKS,
            weight=0.5
        )
        
        assert variant.id == "test_variant"
        assert variant.name == "Test Variant"
        assert variant.strategy == ContentStrategy.VIRAL_HOOKS
        assert variant.weight == 0.5
    
    def test_invalid_weight_raises_error(self):
        """Test that invalid weight raises error"""
        with pytest.raises(ValueError, match="weight must be between 0.0 and 1.0"):
            TestVariant(
                id="test_variant",
                name="Test Variant",
                strategy=ContentStrategy.VIRAL_HOOKS,
                weight=1.5
            )


class TestTestMetrics:
    """Test TestMetrics class"""
    
    def test_create_test_metrics(self):
        """Test creating test metrics"""
        metrics = TestMetrics(variant_id="test_variant")
        
        assert metrics.variant_id == "test_variant"
        assert metrics.impressions == 0
        assert metrics.engagement_rate == 0.0
    
    def test_calculate_engagement_rate(self):
        """Test engagement rate calculation"""
        metrics = TestMetrics(variant_id="test_variant")
        metrics.impressions = 100
        metrics.engagements = 25
        
        metrics.calculate_engagement_rate()
        
        assert metrics.engagement_rate == 0.25
    
    def test_update_metrics(self, sample_post_result):
        """Test updating metrics with post result"""
        metrics = TestMetrics(variant_id="test_variant")
        
        engagement_data = {
            "likes": 10,
            "reposts": 5,
            "replies": 3,
            "clicks": 8
        }
        
        metrics.update_metrics(sample_post_result, engagement_data)
        
        assert metrics.impressions == 1
        assert metrics.likes == 10
        assert metrics.reposts == 5
        assert metrics.replies == 3
        assert metrics.clicks == 8
        assert metrics.engagements == 18  # likes + reposts + replies
        assert metrics.avg_engagement_score == 0.85


class TestABTest:
    """Test ABTest class"""
    
    def test_create_ab_test(self):
        """Test creating an A/B test"""
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        test = ABTest(
            id="test_1",
            name="Test AB Test",
            description="Test description",
            variants=variants
        )
        
        assert test.id == "test_1"
        assert test.name == "Test AB Test"
        assert len(test.variants) == 2
        assert len(test.metrics) == 2
        assert test.status == TestStatus.ACTIVE
    
    def test_invalid_weights_raise_error(self):
        """Test that invalid weights raise error"""
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, weight=0.3),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, weight=0.3)
        ]
        
        with pytest.raises(ValueError, match="Variant weights must sum to 1.0"):
            ABTest(
                id="test_1",
                name="Test AB Test",
                description="Test description",
                variants=variants
            )
    
    def test_is_active(self):
        """Test is_active method"""
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        # Active test
        test = ABTest(
            id="test_1",
            name="Test AB Test",
            description="Test description",
            variants=variants
        )
        
        assert test.is_active() is True
        
        # Completed test
        test.status = TestStatus.COMPLETED
        assert test.is_active() is False
        
        # Expired test
        test.status = TestStatus.ACTIVE
        test.end_date = datetime.now() - timedelta(days=1)
        assert test.is_active() is False
    
    def test_select_variant(self):
        """Test variant selection"""
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.7),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.3)
        ]
        
        test = ABTest(
            id="test_1",
            name="Test AB Test",
            description="Test description",
            variants=variants
        )
        
        # Mock random to test selection
        with patch('random.random', return_value=0.5):
            selected = test.select_variant()
            assert selected.id == "v1"
        
        with patch('random.random', return_value=0.8):
            selected = test.select_variant()
            assert selected.id == "v2"


class TestStatisticalAnalyzer:
    """Test StatisticalAnalyzer class"""
    
    def test_calculate_confidence_interval(self):
        """Test confidence interval calculation"""
        data = [0.5, 0.6, 0.7, 0.8, 0.9]
        
        ci = StatisticalAnalyzer.calculate_confidence_interval(data, 0.95)
        
        assert len(ci) == 2
        assert ci[0] < ci[1]  # Lower bound < upper bound
        assert ci[0] <= 0.7 <= ci[1]  # Mean should be within interval
    
    def test_calculate_statistical_significance(self):
        """Test statistical significance calculation"""
        variant_a = [0.5, 0.6, 0.7, 0.8, 0.9]
        variant_b = [0.3, 0.4, 0.5, 0.6, 0.7]
        
        result = StatisticalAnalyzer.calculate_statistical_significance(
            variant_a, variant_b, 0.95
        )
        
        assert "is_significant" in result
        assert "p_value" in result
        assert "mean_difference" in result
        assert "effect_size" in result
        assert isinstance(result["is_significant"], bool)
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data"""
        variant_a = [0.5]
        variant_b = [0.3]
        
        result = StatisticalAnalyzer.calculate_statistical_significance(
            variant_a, variant_b, 0.95
        )
        
        assert result["is_significant"] is False
        assert result["p_value"] == 1.0
        assert "error" in result


class TestABTestingFramework:
    """Test ABTestingFramework class"""
    
    def test_create_framework(self):
        """Test creating A/B testing framework"""
        framework = ABTestingFramework(max_concurrent_tests=3)
        
        assert len(framework.active_tests) == 0
        assert len(framework.completed_tests) == 0
        assert framework.max_concurrent_tests == 3
    
    def test_create_test(self):
        """Test creating a new A/B test"""
        framework = ABTestingFramework()
        
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        test_id = framework.create_test(
            name="Test AB Test",
            description="Test description",
            variants=variants,
            duration_days=7,
            min_sample_size=50
        )
        
        assert test_id in framework.active_tests
        assert framework.active_tests[test_id].name == "Test AB Test"
        assert len(framework.active_tests[test_id].variants) == 2
    
    def test_max_concurrent_tests_limit(self):
        """Test maximum concurrent tests limit"""
        framework = ABTestingFramework(max_concurrent_tests=1)
        
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        # Create first test
        framework.create_test("Test 1", "Description", variants)
        
        # Try to create second test - should fail
        with pytest.raises(ValueError, match="Maximum concurrent tests"):
            framework.create_test("Test 2", "Description", variants)
    
    def test_get_variant_for_content(self):
        """Test getting variant for content generation"""
        framework = ABTestingFramework()
        
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        test_id = framework.create_test("Test", "Description", variants)
        
        variant = framework.get_variant_for_content(test_id)
        assert variant is not None
        assert variant.id in ["v1", "v2"]
        
        # Test non-existent test
        variant = framework.get_variant_for_content("non_existent")
        assert variant is None
    
    def test_record_result(self, sample_post_result):
        """Test recording A/B test result"""
        framework = ABTestingFramework()
        
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        test_id = framework.create_test("Test", "Description", variants)
        
        engagement_data = {"likes": 10, "reposts": 5, "replies": 3}
        
        framework.record_result(test_id, "v1", sample_post_result, engagement_data)
        
        test = framework.active_tests[test_id]
        metrics = test.metrics["v1"]
        
        assert metrics.impressions == 1
        assert metrics.likes == 10
        assert metrics.reposts == 5
        assert metrics.replies == 3
    
    def test_analyze_test(self, sample_post_result):
        """Test analyzing A/B test results"""
        framework = ABTestingFramework()
        
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        test_id = framework.create_test("Test", "Description", variants, min_sample_size=2)
        
        # Record some results
        framework.record_result(test_id, "v1", sample_post_result)
        framework.record_result(test_id, "v2", sample_post_result)
        
        analysis = framework.analyze_test(test_id)
        
        assert analysis is not None
        assert analysis["test_id"] == test_id
        assert "variants" in analysis
        assert "winner" in analysis
        assert len(analysis["variants"]) == 2
    
    def test_get_optimization_recommendations(self, sample_post_result):
        """Test getting optimization recommendations"""
        framework = ABTestingFramework()
        
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        test_id = framework.create_test("Test", "Description", variants)
        
        # Record some results
        framework.record_result(test_id, "v1", sample_post_result)
        
        recommendations = framework.get_optimization_recommendations(test_id)
        
        assert "test_id" in recommendations
        assert "recommendations" in recommendations
        assert "next_steps" in recommendations
        assert "performance_insights" in recommendations
    
    def test_export_test_results(self, sample_post_result):
        """Test exporting test results"""
        framework = ABTestingFramework()
        
        variants = [
            TestVariant("v1", "Variant 1", ContentStrategy.VIRAL_HOOKS, 0.5),
            TestVariant("v2", "Variant 2", ContentStrategy.ANALYTICAL, 0.5)
        ]
        
        test_id = framework.create_test("Test", "Description", variants)
        framework.record_result(test_id, "v1", sample_post_result)
        
        export_data = framework.export_test_results(test_id)
        
        assert export_data is not None
        assert "test_config" in export_data
        assert "results" in export_data
        assert "analysis" in export_data
        assert "recommendations" in export_data


class TestIntegration:
    """Integration tests for A/B testing framework"""
    
    def test_complete_ab_test_workflow(self, sample_config, sample_news_item):
        """Test complete A/B testing workflow"""
        framework = create_ab_testing_framework(max_concurrent_tests=2)
        
        # Create test
        variants = [
            TestVariant("viral", "Viral Hooks", ContentStrategy.VIRAL_HOOKS, weight=0.5),
            TestVariant("analytical", "Analytical", ContentStrategy.ANALYTICAL, weight=0.5)
        ]
        
        test_id = framework.create_test(
            name="Content Strategy Test",
            description="Compare viral vs analytical strategies",
            variants=variants,
            duration_days=3,
            min_sample_size=50  # Higher sample size to prevent auto-completion
        )
        
        # Simulate content generation and posting
        for i in range(15):
            variant = framework.get_variant_for_content(test_id)
            if variant is None:
                test = framework.active_tests.get(test_id)
                print(f"Test {test_id} status: {test.status if test else 'Not found'}")
                print(f"Test is active: {test.is_active() if test else 'N/A'}")
                print(f"Active tests: {list(framework.active_tests.keys())}")
            assert variant is not None
            
            # Create mock content and result
            content = GeneratedContent(
                text=f"Test content {i}",
                hashtags=["#Test"],
                engagement_score=0.7 + (i % 3) * 0.1,
                content_type=ContentType.NEWS,
                source_news=sample_news_item,
                metadata={"ab_test_variant": variant.id}
            )
            
            result = PostResult(
                success=True,
                post_id=f"post_{i}",
                timestamp=datetime.now(),
                content=content
            )
            
            engagement_data = {
                "likes": 5 + (i % 10),
                "reposts": 2 + (i % 5),
                "replies": 1 + (i % 3)
            }
            
            framework.record_result(test_id, variant.id, result, engagement_data)
        
        # Analyze results
        analysis = framework.analyze_test(test_id)
        
        assert analysis["sample_size"] == 15
        assert analysis["has_sufficient_data"] is False  # 15 < 50 min sample size
        assert len(analysis["variants"]) == 2
        
        # Get recommendations
        recommendations = framework.get_optimization_recommendations(test_id)
        assert len(recommendations["recommendations"]) > 0
        
        # Export results
        export_data = framework.export_test_results(test_id)
        assert export_data is not None
        
        # Verify test completion logic
        test = framework.active_tests[test_id]
        assert test.get_sample_size() == 15
        assert test.has_sufficient_data() is False  # 15 < 50 min sample size


if __name__ == "__main__":
    pytest.main([__file__])