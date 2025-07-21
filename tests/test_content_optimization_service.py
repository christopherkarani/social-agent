# tests/test_content_optimization_service.py
"""
Tests for Content Optimization Service
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.services.content_optimization_service import (
    ContentOptimizationService, ContentStrategyOptimizer, AutomatedOptimizer,
    ContentPerformanceAnalytics, create_content_optimization_service
)
from src.services.ab_testing_framework import (
    ContentStrategy, TestVariant, ABTestingFramework
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
        headline="Ethereum Upgrade Improves Scalability",
        summary="The latest Ethereum upgrade has significantly improved transaction throughput and reduced gas fees.",
        source="EthNews",
        timestamp=datetime.now(),
        relevance_score=0.85,
        topics=["Ethereum", "Upgrade", "Scalability"]
    )


@pytest.fixture
def sample_generated_content(sample_news_item):
    """Create sample generated content for testing"""
    return GeneratedContent(
        text="📊 ANALYSIS: Ethereum upgrade delivers 40% gas reduction! Scalability breakthrough 🚀",
        hashtags=["#Ethereum", "#ETH", "#Upgrade"],
        engagement_score=0.78,
        content_type=ContentType.ANALYSIS,
        source_news=sample_news_item,
        metadata={"generation_strategy": "analytical"}
    )


@pytest.fixture
def sample_post_result(sample_generated_content):
    """Create sample post result for testing"""
    return PostResult(
        success=True,
        post_id="post_456",
        timestamp=datetime.now(),
        content=sample_generated_content
    )


@pytest.fixture
def mock_content_generation_tool():
    """Create mock content generation tool"""
    tool = Mock()
    tool._run.return_value = json.dumps({
        "success": True,
        "content": {
            "text": "Test generated content",
            "hashtags": ["#Test"],
            "engagement_score": 0.75,
            "content_type": "news",
            "source_news": {
                "headline": "Test headline",
                "summary": "Test summary",
                "source": "Test source",
                "timestamp": datetime.now().isoformat(),
                "relevance_score": 0.8,
                "topics": ["Test"]
            },
            "created_at": datetime.now().isoformat(),
            "metadata": {"generation_strategy": "viral_hooks"}
        },
        "alternatives": []
    })
    return tool


class TestContentStrategyOptimizer:
    """Test ContentStrategyOptimizer class"""
    
    def test_create_optimizer(self, sample_config):
        """Test creating content strategy optimizer"""
        optimizer = ContentStrategyOptimizer(sample_config)
        
        assert optimizer.config == sample_config
        assert len(optimizer.strategy_performance) == 0
        assert len(optimizer.optimization_history) == 0
    
    def test_record_performance(self, sample_config, sample_post_result):
        """Test recording performance data"""
        optimizer = ContentStrategyOptimizer(sample_config)
        
        optimizer.record_performance(
            ContentStrategy.ANALYTICAL,
            0.85,
            sample_post_result
        )
        
        assert len(optimizer.strategy_performance[ContentStrategy.ANALYTICAL.value]) == 1
        assert optimizer.strategy_performance[ContentStrategy.ANALYTICAL.value][0] == 0.85
        assert len(optimizer.optimization_history) == 1
    
    def test_get_strategy_performance(self, sample_config, sample_post_result):
        """Test getting strategy performance statistics"""
        optimizer = ContentStrategyOptimizer(sample_config)
        
        # Record multiple performances
        for score in [0.7, 0.8, 0.9, 0.6, 0.85]:
            optimizer.record_performance(
                ContentStrategy.VIRAL_HOOKS,
                score,
                sample_post_result
            )
        
        stats = optimizer.get_strategy_performance(ContentStrategy.VIRAL_HOOKS)
        
        assert stats["strategy"] == ContentStrategy.VIRAL_HOOKS.value
        assert stats["sample_size"] == 5
        assert stats["avg_score"] == 0.77  # (0.7+0.8+0.9+0.6+0.85)/5
        assert stats["min_score"] == 0.6
        assert stats["max_score"] == 0.9
        assert stats["success_rate"] == 1.0  # All posts successful
    
    def test_calculate_trend(self, sample_config, sample_post_result):
        """Test trend calculation"""
        optimizer = ContentStrategyOptimizer(sample_config)
        
        # Record improving trend
        improving_scores = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        for score in improving_scores:
            optimizer.record_performance(
                ContentStrategy.ANALYTICAL,
                score,
                sample_post_result
            )
        
        stats = optimizer.get_strategy_performance(ContentStrategy.ANALYTICAL)
        assert stats["trend"] == "improving"
        
        # Record declining trend
        optimizer_2 = ContentStrategyOptimizer(sample_config)
        declining_scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
        for score in declining_scores:
            optimizer_2.record_performance(
                ContentStrategy.CONTROVERSIAL,
                score,
                sample_post_result
            )
        
        stats_2 = optimizer_2.get_strategy_performance(ContentStrategy.CONTROVERSIAL)
        assert stats_2["trend"] == "declining"
    
    def test_get_best_strategy(self, sample_config, sample_post_result):
        """Test getting best performing strategy"""
        optimizer = ContentStrategyOptimizer(sample_config)
        
        # Record performance for multiple strategies
        strategies_scores = {
            ContentStrategy.VIRAL_HOOKS: [0.6, 0.7, 0.8, 0.7, 0.75, 0.8, 0.85, 0.9, 0.8, 0.75],
            ContentStrategy.ANALYTICAL: [0.8, 0.85, 0.9, 0.88, 0.92, 0.87, 0.89, 0.91, 0.86, 0.88],
            ContentStrategy.CONTROVERSIAL: [0.5, 0.6, 0.55, 0.65, 0.7, 0.6, 0.58, 0.62, 0.67, 0.63]
        }
        
        for strategy, scores in strategies_scores.items():
            for score in scores:
                optimizer.record_performance(strategy, score, sample_post_result)
        
        best_strategy = optimizer.get_best_strategy(min_sample_size=10)
        assert best_strategy == ContentStrategy.ANALYTICAL
    
    def test_get_optimization_recommendations(self, sample_config, sample_post_result):
        """Test getting optimization recommendations"""
        optimizer = ContentStrategyOptimizer(sample_config)
        
        # Record underperforming strategy
        for score in [0.2, 0.3, 0.25, 0.35, 0.28]:
            optimizer.record_performance(
                ContentStrategy.CONTROVERSIAL,
                score,
                sample_post_result
            )
        
        # Record high-performing strategy
        for score in [0.85, 0.9, 0.88, 0.92, 0.87]:
            optimizer.record_performance(
                ContentStrategy.ANALYTICAL,
                score,
                sample_post_result
            )
        
        recommendations = optimizer.get_optimization_recommendations()
        
        assert len(recommendations) >= 2
        
        # Check for underperforming strategy recommendation
        underperforming = [r for r in recommendations if r["type"] == "underperforming_strategy"]
        assert len(underperforming) > 0
        assert underperforming[0]["strategy"] == ContentStrategy.CONTROVERSIAL.value
        
        # Check for high-performing strategy recommendation
        high_performing = [r for r in recommendations if r["type"] == "high_performing_strategy"]
        assert len(high_performing) > 0
        assert high_performing[0]["strategy"] == ContentStrategy.ANALYTICAL.value


class TestAutomatedOptimizer:
    """Test AutomatedOptimizer class"""
    
    def test_create_optimizer(self, sample_config):
        """Test creating automated optimizer"""
        ab_framework = ABTestingFramework()
        optimizer = AutomatedOptimizer(sample_config, ab_framework)
        
        assert optimizer.config == sample_config
        assert optimizer.ab_framework == ab_framework
        assert optimizer.auto_optimization_enabled is True
        assert len(optimizer.optimization_rules) > 0
    
    def test_run_optimization_cycle_disabled(self, sample_config):
        """Test optimization cycle when disabled"""
        ab_framework = ABTestingFramework()
        optimizer = AutomatedOptimizer(sample_config, ab_framework)
        optimizer.auto_optimization_enabled = False
        
        result = optimizer.run_optimization_cycle()
        
        assert result["status"] == "disabled"
        assert result["actions"] == []
    
    def test_run_optimization_cycle_with_data(self, sample_config, sample_post_result):
        """Test optimization cycle with performance data"""
        ab_framework = ABTestingFramework()
        optimizer = AutomatedOptimizer(sample_config, ab_framework)
        
        # Record some performance data
        for score in [0.3, 0.25, 0.35, 0.28, 0.32, 0.29, 0.31, 0.27, 0.33, 0.26]:
            optimizer.strategy_optimizer.record_performance(
                ContentStrategy.CONTROVERSIAL,
                score,
                sample_post_result
            )
        
        result = optimizer.run_optimization_cycle()
        
        assert result["status"] == "completed"
        assert "actions" in result
        assert "recommendations" in result
        assert "timestamp" in result
    
    def test_record_content_performance(self, sample_config, sample_generated_content, sample_post_result):
        """Test recording content performance"""
        ab_framework = ABTestingFramework()
        optimizer = AutomatedOptimizer(sample_config, ab_framework)
        
        engagement_data = {"likes": 15, "reposts": 8, "replies": 5}
        
        optimizer.record_content_performance(
            sample_generated_content,
            sample_post_result,
            engagement_data
        )
        
        # Check that performance was recorded
        strategy_performance = optimizer.strategy_optimizer.strategy_performance
        assert len(strategy_performance[ContentStrategy.ANALYTICAL.value]) == 1
    
    def test_get_optimization_status(self, sample_config, sample_post_result):
        """Test getting optimization status"""
        ab_framework = ABTestingFramework()
        optimizer = AutomatedOptimizer(sample_config, ab_framework)
        
        # Record some data
        optimizer.strategy_optimizer.record_performance(
            ContentStrategy.VIRAL_HOOKS,
            0.8,
            sample_post_result
        )
        
        status = optimizer.get_optimization_status()
        
        assert "auto_optimization_enabled" in status
        assert "active_ab_tests" in status
        assert "strategy_performance" in status
        assert "best_strategy" in status
        assert "optimization_recommendations" in status
        assert status["auto_optimization_enabled"] is True


class TestContentPerformanceAnalytics:
    """Test ContentPerformanceAnalytics class"""
    
    def test_create_analytics(self):
        """Test creating performance analytics"""
        analytics = ContentPerformanceAnalytics()
        
        assert len(analytics.performance_data) == 0
        assert len(analytics.daily_summaries) == 0
    
    def test_record_performance(self, sample_generated_content, sample_post_result):
        """Test recording performance data"""
        analytics = ContentPerformanceAnalytics()
        
        engagement_data = {"likes": 12, "reposts": 6, "replies": 4}
        
        analytics.record_performance(
            sample_generated_content,
            sample_post_result,
            engagement_data
        )
        
        assert len(analytics.performance_data) == 1
        
        # Check daily summary
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in analytics.daily_summaries
        assert analytics.daily_summaries[today]["total_posts"] == 1
        assert analytics.daily_summaries[today]["successful_posts"] == 1
    
    def test_generate_report(self, sample_generated_content, sample_post_result):
        """Test generating performance report"""
        analytics = ContentPerformanceAnalytics()
        
        # Record multiple performances
        for i in range(5):
            content = GeneratedContent(
                text=f"Test content {i}",
                hashtags=["#Test"],
                engagement_score=0.7 + i * 0.05,
                content_type=ContentType.NEWS,
                source_news=sample_generated_content.source_news,
                metadata={"generation_strategy": "viral_hooks"}
            )
            
            result = PostResult(
                success=True,
                post_id=f"post_{i}",
                timestamp=datetime.now(),
                content=content
            )
            
            analytics.record_performance(content, result)
        
        report = analytics.generate_report(days_back=1)
        
        assert report["total_posts"] == 5
        assert report["successful_posts"] == 5
        assert report["success_rate"] == 1.0
        assert "avg_engagement_score" in report
        assert "strategy_performance" in report
        assert "daily_summaries" in report


class TestContentOptimizationService:
    """Test ContentOptimizationService class"""
    
    def test_create_service(self, sample_config):
        """Test creating content optimization service"""
        service = ContentOptimizationService(sample_config)
        
        assert service.config == sample_config
        assert service.ab_framework is not None
        assert service.automated_optimizer is not None
        assert service.performance_analytics is not None
    
    def test_initialize_default_tests(self, sample_config):
        """Test initializing default A/B tests"""
        service = ContentOptimizationService(sample_config)
        
        test_id = service.initialize_default_tests()
        
        assert test_id is not None
        assert test_id in service.ab_framework.active_tests
        
        test = service.ab_framework.active_tests[test_id]
        assert len(test.variants) == 4  # Four strategies
        assert test.name == "Content Strategy Comparison"
    
    def test_generate_optimized_content(self, sample_config, sample_news_item, mock_content_generation_tool):
        """Test generating optimized content"""
        service = ContentOptimizationService(sample_config)
        
        # Initialize a test
        service.initialize_default_tests()
        
        content = service.generate_optimized_content(
            sample_news_item,
            mock_content_generation_tool
        )
        
        assert content is not None
        assert isinstance(content, GeneratedContent)
        assert "generation_strategy" in content.metadata
        
        # Verify tool was called
        mock_content_generation_tool._run.assert_called_once()
    
    def test_record_post_performance(self, sample_config, sample_generated_content, sample_post_result):
        """Test recording post performance"""
        service = ContentOptimizationService(sample_config)
        
        engagement_data = {"likes": 20, "reposts": 10, "replies": 8}
        
        service.record_post_performance(
            sample_generated_content,
            sample_post_result,
            engagement_data
        )
        
        # Verify data was recorded in both systems
        assert len(service.automated_optimizer.strategy_optimizer.optimization_history) == 1
        assert len(service.performance_analytics.performance_data) == 1
    
    def test_run_optimization_cycle(self, sample_config, sample_post_result):
        """Test running optimization cycle"""
        service = ContentOptimizationService(sample_config)
        
        # Record some performance data first
        for score in [0.6, 0.7, 0.8, 0.75, 0.82]:
            service.automated_optimizer.strategy_optimizer.record_performance(
                ContentStrategy.VIRAL_HOOKS,
                score,
                sample_post_result
            )
        
        result = service.run_optimization_cycle()
        
        assert "status" in result
        assert result["status"] == "completed"
    
    def test_get_performance_report(self, sample_config, sample_generated_content, sample_post_result):
        """Test getting performance report"""
        service = ContentOptimizationService(sample_config)
        
        # Record some data
        service.record_post_performance(
            sample_generated_content,
            sample_post_result,
            {"likes": 15, "reposts": 7}
        )
        
        report = service.get_performance_report()
        
        assert "optimization_status" in report
        assert "performance_analytics" in report
        assert "active_tests" in report
        assert "timestamp" in report
    
    def test_export_optimization_data(self, sample_config, sample_post_result):
        """Test exporting optimization data"""
        service = ContentOptimizationService(sample_config)
        
        # Initialize test and record data
        service.initialize_default_tests()
        service.automated_optimizer.strategy_optimizer.record_performance(
            ContentStrategy.VIRAL_HOOKS,
            0.8,
            sample_post_result
        )
        
        export_data = service.export_optimization_data()
        
        assert "ab_tests" in export_data
        assert "performance_history" in export_data
        assert "strategy_performance" in export_data
        assert "export_timestamp" in export_data
        
        # Verify strategy performance data
        assert len(export_data["strategy_performance"]) == len(ContentStrategy)


class TestIntegration:
    """Integration tests for content optimization service"""
    
    def test_complete_optimization_workflow(self, sample_config, sample_news_item, mock_content_generation_tool):
        """Test complete optimization workflow"""
        service = create_content_optimization_service(sample_config)
        
        # Initialize default tests
        test_id = service.initialize_default_tests()
        assert test_id is not None
        
        # Generate optimized content multiple times
        contents_and_results = []
        
        for i in range(20):
            # Generate content
            content = service.generate_optimized_content(
                sample_news_item,
                mock_content_generation_tool
            )
            
            # Create mock post result
            result = PostResult(
                success=True,
                post_id=f"post_{i}",
                timestamp=datetime.now(),
                content=content
            )
            
            # Record performance
            engagement_data = {
                "likes": 10 + (i % 15),
                "reposts": 3 + (i % 8),
                "replies": 1 + (i % 5)
            }
            
            service.record_post_performance(content, result, engagement_data)
            contents_and_results.append((content, result))
        
        # Run optimization cycle
        optimization_result = service.run_optimization_cycle()
        assert optimization_result["status"] == "completed"
        
        # Get performance report
        report = service.get_performance_report()
        assert report["performance_analytics"]["total_posts"] == 20
        
        # Analyze A/B test results
        analysis = service.ab_framework.analyze_test(test_id)
        assert analysis["sample_size"] > 0
        assert len(analysis["variants"]) == 4
        
        # Export all data
        export_data = service.export_optimization_data()
        assert len(export_data["performance_history"]) == 20
        
        # Verify optimization recommendations
        recommendations = service.ab_framework.get_optimization_recommendations(test_id)
        assert "recommendations" in recommendations
        assert "next_steps" in recommendations
    
    def test_strategy_performance_tracking(self, sample_config, sample_news_item, mock_content_generation_tool):
        """Test strategy performance tracking over time"""
        service = ContentOptimizationService(sample_config)
        
        # Simulate different strategies performing differently
        strategy_scores = {
            ContentStrategy.VIRAL_HOOKS: [0.6, 0.65, 0.7, 0.68, 0.72],
            ContentStrategy.ANALYTICAL: [0.8, 0.85, 0.82, 0.88, 0.86],
            ContentStrategy.CONTROVERSIAL: [0.4, 0.45, 0.42, 0.48, 0.44]
        }
        
        for strategy, scores in strategy_scores.items():
            for score in scores:
                content = GeneratedContent(
                    text="Test content",
                    hashtags=["#Test"],
                    engagement_score=score,
                    content_type=ContentType.NEWS,
                    source_news=sample_news_item,
                    metadata={"generation_strategy": strategy.value}
                )
                
                result = PostResult(
                    success=True,
                    post_id="test_post",
                    timestamp=datetime.now(),
                    content=content
                )
                
                service.record_post_performance(content, result)
        
        # Check that best strategy is identified correctly
        best_strategy = service.automated_optimizer.strategy_optimizer.get_best_strategy(min_sample_size=5)
        assert best_strategy == ContentStrategy.ANALYTICAL
        
        # Check optimization recommendations
        recommendations = service.automated_optimizer.strategy_optimizer.get_optimization_recommendations()
        
        # Should recommend reducing controversial strategy usage
        controversial_recs = [r for r in recommendations if r["strategy"] == ContentStrategy.CONTROVERSIAL.value]
        assert len(controversial_recs) > 0
        assert controversial_recs[0]["type"] == "underperforming_strategy"
        
        # Should recommend increasing analytical strategy usage
        analytical_recs = [r for r in recommendations if r["strategy"] == ContentStrategy.ANALYTICAL.value]
        assert len(analytical_recs) > 0
        assert analytical_recs[0]["type"] == "high_performing_strategy"


if __name__ == "__main__":
    pytest.main([__file__])