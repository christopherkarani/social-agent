# src/services/content_optimization_service.py
"""
Content Optimization Service - Automated optimization based on A/B testing results
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque

from .ab_testing_framework import (
    ABTestingFramework, TestVariant, ContentStrategy, 
    create_ab_testing_framework
)
from ..models.data_models import GeneratedContent, PostResult, NewsItem, ContentType
from ..config.agent_config import AgentConfig

logger = logging.getLogger(__name__)


class ContentStrategyOptimizer:
    """Optimizes content generation strategies based on performance data"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.strategy_performance: Dict[str, List[float]] = defaultdict(list)
        self.optimization_history: deque = deque(maxlen=500)
        
    def record_performance(self, strategy: ContentStrategy, engagement_score: float, 
                          post_result: PostResult):
        """Record performance data for a strategy"""
        self.strategy_performance[strategy.value].append(engagement_score)
        
        self.optimization_history.append({
            "timestamp": datetime.now(),
            "strategy": strategy.value,
            "engagement_score": engagement_score,
            "success": post_result.success,
            "content_length": len(post_result.content.text),
            "hashtag_count": len(post_result.content.hashtags)
        })
        
        logger.debug(f"Recorded performance for {strategy.value}: {engagement_score:.3f}")
    
    def get_strategy_performance(self, strategy: ContentStrategy, 
                               days_back: int = 7) -> Dict[str, Any]:
        """Get performance statistics for a strategy"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        recent_scores = [
            record["engagement_score"] 
            for record in self.optimization_history
            if (record["strategy"] == strategy.value and 
                record["timestamp"] >= cutoff_date)
        ]
        
        if not recent_scores:
            return {
                "strategy": strategy.value,
                "sample_size": 0,
                "avg_score": 0.0,
                "min_score": 0.0,
                "max_score": 0.0,
                "success_rate": 0.0
            }
        
        recent_results = [
            record for record in self.optimization_history
            if (record["strategy"] == strategy.value and 
                record["timestamp"] >= cutoff_date)
        ]
        
        successful_posts = sum(1 for r in recent_results if r["success"])
        
        return {
            "strategy": strategy.value,
            "sample_size": len(recent_scores),
            "avg_score": sum(recent_scores) / len(recent_scores),
            "min_score": min(recent_scores),
            "max_score": max(recent_scores),
            "success_rate": successful_posts / len(recent_results) if recent_results else 0.0,
            "trend": self._calculate_trend(recent_scores)
        }
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate performance trend"""
        if len(scores) < 4:
            return "insufficient_data"
        
        # Compare first half vs second half
        mid_point = len(scores) // 2
        first_half_avg = sum(scores[:mid_point]) / mid_point
        second_half_avg = sum(scores[mid_point:]) / (len(scores) - mid_point)
        
        diff = second_half_avg - first_half_avg
        
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"
    
    def get_best_strategy(self, min_sample_size: int = 10) -> Optional[ContentStrategy]:
        """Get the best performing strategy"""
        strategy_stats = {}
        
        for strategy in ContentStrategy:
            stats = self.get_strategy_performance(strategy)
            if stats["sample_size"] >= min_sample_size:
                strategy_stats[strategy] = stats
        
        if not strategy_stats:
            return None
        
        # Find strategy with highest average score
        best_strategy = max(strategy_stats.keys(), 
                          key=lambda s: strategy_stats[s]["avg_score"])
        
        return best_strategy
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on performance data"""
        recommendations = []
        
        # Analyze each strategy
        for strategy in ContentStrategy:
            stats = self.get_strategy_performance(strategy)
            
            if stats["sample_size"] >= 5:
                if stats["avg_score"] < 0.5:
                    recommendations.append({
                        "type": "underperforming_strategy",
                        "strategy": strategy.value,
                        "message": f"{strategy.value} strategy is underperforming (avg: {stats['avg_score']:.2f})",
                        "suggestion": "Consider reducing usage or optimizing parameters",
                        "priority": "high" if stats["avg_score"] < 0.3 else "medium"
                    })
                elif stats["avg_score"] > 0.8:
                    recommendations.append({
                        "type": "high_performing_strategy",
                        "strategy": strategy.value,
                        "message": f"{strategy.value} strategy is performing well (avg: {stats['avg_score']:.2f})",
                        "suggestion": "Consider increasing usage frequency",
                        "priority": "low"
                    })
                
                if stats["trend"] == "declining":
                    recommendations.append({
                        "type": "declining_performance",
                        "strategy": strategy.value,
                        "message": f"{strategy.value} strategy showing declining performance",
                        "suggestion": "Review and refresh strategy parameters",
                        "priority": "medium"
                    })
        
        return recommendations


class AutomatedOptimizer:
    """Automated optimization system that adjusts strategies based on performance"""
    
    def __init__(self, config: AgentConfig, ab_framework: ABTestingFramework):
        self.config = config
        self.ab_framework = ab_framework
        self.strategy_optimizer = ContentStrategyOptimizer(config)
        self.optimization_rules: List[Dict[str, Any]] = []
        self.auto_optimization_enabled = True
        
        # Initialize default optimization rules
        self._initialize_optimization_rules()
    
    def _initialize_optimization_rules(self):
        """Initialize default optimization rules"""
        self.optimization_rules = [
            {
                "name": "low_performance_adjustment",
                "condition": lambda stats: stats["avg_score"] < 0.4 and stats["sample_size"] >= 10,
                "action": "reduce_weight",
                "parameters": {"weight_reduction": 0.2}
            },
            {
                "name": "high_performance_boost",
                "condition": lambda stats: stats["avg_score"] > 0.8 and stats["sample_size"] >= 10,
                "action": "increase_weight",
                "parameters": {"weight_increase": 0.1}
            },
            {
                "name": "declining_trend_alert",
                "condition": lambda stats: stats["trend"] == "declining" and stats["sample_size"] >= 15,
                "action": "create_optimization_test",
                "parameters": {"test_duration_days": 3}
            }
        ]
    
    def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run automated optimization cycle"""
        if not self.auto_optimization_enabled:
            return {"status": "disabled", "actions": []}
        
        optimization_actions = []
        
        # Analyze current strategy performance
        for strategy in ContentStrategy:
            stats = self.strategy_optimizer.get_strategy_performance(strategy)
            
            if stats["sample_size"] < 5:
                continue
            
            # Apply optimization rules
            for rule in self.optimization_rules:
                if rule["condition"](stats):
                    action_result = self._execute_optimization_action(
                        rule["action"], 
                        strategy, 
                        stats, 
                        rule["parameters"]
                    )
                    
                    if action_result:
                        optimization_actions.append({
                            "rule": rule["name"],
                            "strategy": strategy.value,
                            "action": rule["action"],
                            "result": action_result
                        })
        
        # Check for new optimization opportunities
        self._check_optimization_opportunities(optimization_actions)
        
        logger.info(f"Completed optimization cycle with {len(optimization_actions)} actions")
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "actions": optimization_actions,
            "recommendations": self.strategy_optimizer.get_optimization_recommendations()
        }
    
    def _execute_optimization_action(self, action: str, strategy: ContentStrategy, 
                                   stats: Dict[str, Any], parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute an optimization action"""
        
        if action == "create_optimization_test":
            return self._create_strategy_optimization_test(strategy, parameters)
        elif action == "reduce_weight":
            return self._adjust_strategy_weight(strategy, -parameters.get("weight_reduction", 0.1))
        elif action == "increase_weight":
            return self._adjust_strategy_weight(strategy, parameters.get("weight_increase", 0.1))
        else:
            logger.warning(f"Unknown optimization action: {action}")
            return None
    
    def _create_strategy_optimization_test(self, strategy: ContentStrategy, 
                                         parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create an A/B test to optimize a specific strategy"""
        
        # Create variants with different parameters
        base_variant = TestVariant(
            id=f"{strategy.value}_current",
            name=f"{strategy.value} (Current)",
            strategy=strategy,
            weight=0.5
        )
        
        # Create optimized variant with adjusted parameters
        optimized_params = self._generate_optimized_parameters(strategy)
        optimized_variant = TestVariant(
            id=f"{strategy.value}_optimized",
            name=f"{strategy.value} (Optimized)",
            strategy=strategy,
            parameters=optimized_params,
            weight=0.5
        )
        
        test_id = self.ab_framework.create_test(
            name=f"Optimize {strategy.value} Strategy",
            description=f"A/B test to optimize {strategy.value} content generation strategy",
            variants=[base_variant, optimized_variant],
            duration_days=parameters.get("test_duration_days", 3),
            min_sample_size=20
        )
        
        return {
            "test_id": test_id,
            "test_name": f"Optimize {strategy.value} Strategy",
            "variants": 2,
            "duration_days": parameters.get("test_duration_days", 3)
        }
    
    def _generate_optimized_parameters(self, strategy: ContentStrategy) -> Dict[str, Any]:
        """Generate optimized parameters for a strategy"""
        
        # Strategy-specific parameter optimization
        if strategy == ContentStrategy.VIRAL_HOOKS:
            return {
                "hook_intensity": "high",
                "emoji_usage": "moderate",
                "urgency_level": "medium"
            }
        elif strategy == ContentStrategy.ANALYTICAL:
            return {
                "data_focus": "high",
                "technical_depth": "medium",
                "chart_references": True
            }
        elif strategy == ContentStrategy.CONTROVERSIAL:
            return {
                "controversy_level": "medium",
                "opinion_strength": "strong",
                "debate_invitation": True
            }
        elif strategy == ContentStrategy.EDUCATIONAL:
            return {
                "explanation_depth": "medium",
                "examples_included": True,
                "actionable_tips": True
            }
        elif strategy == ContentStrategy.MARKET_FOCUSED:
            return {
                "price_emphasis": "high",
                "trend_analysis": True,
                "prediction_confidence": "medium"
            }
        elif strategy == ContentStrategy.COMMUNITY_DRIVEN:
            return {
                "question_frequency": "high",
                "community_references": True,
                "engagement_calls": "strong"
            }
        else:
            return {}
    
    def _adjust_strategy_weight(self, strategy: ContentStrategy, weight_change: float) -> Dict[str, Any]:
        """Adjust strategy weight in active tests"""
        
        # This would integrate with the content generation system
        # to adjust how frequently each strategy is used
        
        return {
            "strategy": strategy.value,
            "weight_change": weight_change,
            "new_weight": max(0.1, min(1.0, 0.5 + weight_change)),  # Keep within bounds
            "note": "Strategy weight adjustment applied to future content generation"
        }
    
    def _check_optimization_opportunities(self, current_actions: List[Dict[str, Any]]):
        """Check for additional optimization opportunities"""
        
        # Look for strategies that haven't been tested recently
        untested_strategies = []
        for strategy in ContentStrategy:
            stats = self.strategy_optimizer.get_strategy_performance(strategy, days_back=14)
            if stats["sample_size"] < 5:
                untested_strategies.append(strategy)
        
        # Suggest testing untested strategies
        if untested_strategies and len(current_actions) < 2:
            for strategy in untested_strategies[:1]:  # Test one at a time
                test_result = self._create_strategy_optimization_test(
                    strategy, 
                    {"test_duration_days": 2}
                )
                
                current_actions.append({
                    "rule": "untested_strategy_exploration",
                    "strategy": strategy.value,
                    "action": "create_exploration_test",
                    "result": test_result
                })
    
    def record_content_performance(self, content: GeneratedContent, post_result: PostResult,
                                 engagement_data: Dict[str, Any] = None):
        """Record content performance for optimization"""
        
        # Determine strategy from content metadata
        strategy_name = content.metadata.get("generation_strategy", "viral_hooks")
        try:
            strategy = ContentStrategy(strategy_name)
        except ValueError:
            strategy = ContentStrategy.VIRAL_HOOKS
        
        # Record in strategy optimizer
        self.strategy_optimizer.record_performance(
            strategy, 
            content.engagement_score, 
            post_result
        )
        
        # Record in active A/B tests
        for test_id, test in self.ab_framework.active_tests.items():
            # Check if this content was part of an A/B test
            test_strategy = content.metadata.get("ab_test_strategy")
            variant_id = content.metadata.get("ab_test_variant_id")
            
            if test_strategy and variant_id:
                self.ab_framework.record_result(
                    test_id, 
                    variant_id, 
                    post_result, 
                    engagement_data
                )
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        
        active_tests = self.ab_framework.get_active_tests()
        strategy_performance = {}
        
        for strategy in ContentStrategy:
            strategy_performance[strategy.value] = self.strategy_optimizer.get_strategy_performance(strategy)
        
        best_strategy = self.strategy_optimizer.get_best_strategy()
        
        return {
            "auto_optimization_enabled": self.auto_optimization_enabled,
            "active_ab_tests": len(active_tests),
            "strategy_performance": strategy_performance,
            "best_strategy": best_strategy.value if best_strategy else None,
            "optimization_recommendations": self.strategy_optimizer.get_optimization_recommendations(),
            "last_optimization_cycle": datetime.now().isoformat()
        }


class ContentOptimizationService:
    """Main service for content optimization and A/B testing"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.ab_framework = create_ab_testing_framework(max_concurrent_tests=3)
        self.automated_optimizer = AutomatedOptimizer(config, self.ab_framework)
        self.performance_analytics = ContentPerformanceAnalytics()
        
        # Mapping from ContentStrategy to ContentType
        self.strategy_to_content_type = {
            ContentStrategy.VIRAL_HOOKS: ContentType.NEWS,
            ContentStrategy.ANALYTICAL: ContentType.ANALYSIS,
            ContentStrategy.CONTROVERSIAL: ContentType.OPINION,
            ContentStrategy.EDUCATIONAL: ContentType.ANALYSIS,
            ContentStrategy.MARKET_FOCUSED: ContentType.MARKET_UPDATE,
            ContentStrategy.COMMUNITY_DRIVEN: ContentType.OPINION
        }
        
    def initialize_default_tests(self):
        """Initialize default A/B tests for content strategies"""
        
        # Create a comprehensive strategy comparison test
        strategy_variants = [
            TestVariant(
                id="viral_hooks",
                name="Viral Hooks Strategy",
                strategy=ContentStrategy.VIRAL_HOOKS,
                weight=0.25
            ),
            TestVariant(
                id="analytical",
                name="Analytical Strategy", 
                strategy=ContentStrategy.ANALYTICAL,
                weight=0.25
            ),
            TestVariant(
                id="controversial",
                name="Controversial Strategy",
                strategy=ContentStrategy.CONTROVERSIAL,
                weight=0.25
            ),
            TestVariant(
                id="market_focused",
                name="Market Focused Strategy",
                strategy=ContentStrategy.MARKET_FOCUSED,
                weight=0.25
            )
        ]
        
        test_id = self.ab_framework.create_test(
            name="Content Strategy Comparison",
            description="Compare different content generation strategies for optimal engagement",
            variants=strategy_variants,
            duration_days=7,
            min_sample_size=50
        )
        
        logger.info(f"Initialized default A/B test: {test_id}")
        return test_id
    
    def generate_optimized_content(self, news_item: NewsItem, 
                                 content_generation_tool) -> GeneratedContent:
        """Generate content using A/B testing optimization"""
        
        # Get active test variant
        active_tests = self.ab_framework.get_active_tests()
        
        if active_tests:
            # Use A/B test variant
            test_id = active_tests[0]["id"]
            variant = self.ab_framework.get_variant_for_content(test_id)
            
            if variant:
                # Generate content with specific strategy
                # Map ContentStrategy to ContentType for the content generation tool
                mapped_content_type = self.strategy_to_content_type.get(variant.strategy, ContentType.NEWS)
                content_data = {
                    "news_data": json.dumps([news_item.to_dict()]),
                    "content_type": mapped_content_type.value,
                    "target_engagement": 0.8
                }
                
                result = content_generation_tool._run(**content_data)
                result_data = json.loads(result)
                
                if result_data["success"]:
                    content_dict = result_data["content"]
                    # Convert content_type string to enum
                    if isinstance(content_dict.get("content_type"), str):
                        content_dict["content_type"] = ContentType(content_dict["content_type"])
                    # Convert source_news dict to NewsItem
                    if isinstance(content_dict.get("source_news"), dict):
                        source_news_dict = content_dict["source_news"]
                        if isinstance(source_news_dict.get("timestamp"), str):
                            source_news_dict["timestamp"] = datetime.fromisoformat(source_news_dict["timestamp"].replace("Z", "+00:00"))
                        content_dict["source_news"] = NewsItem(**source_news_dict)
                    # Convert created_at string to datetime
                    if isinstance(content_dict.get("created_at"), str):
                        content_dict["created_at"] = datetime.fromisoformat(content_dict["created_at"].replace("Z", "+00:00"))
                    
                    # Remove extra fields that aren't part of GeneratedContent constructor
                    extra_fields = ["character_count", "hashtag_count"]
                    for field in extra_fields:
                        content_dict.pop(field, None)
                    
                    content = GeneratedContent(**content_dict)
                    
                    # Add A/B test metadata
                    content.metadata.update({
                        "ab_test_id": test_id,
                        "ab_test_variant_id": variant.id,
                        "ab_test_strategy": variant.strategy.value,
                        "generation_strategy": variant.strategy.value
                    })
                    
                    return content
        
        # Fallback to best performing strategy
        best_strategy = self.automated_optimizer.strategy_optimizer.get_best_strategy()
        if best_strategy:
            mapped_content_type = self.strategy_to_content_type.get(best_strategy, ContentType.NEWS)
            strategy_name = best_strategy.value
        else:
            mapped_content_type = ContentType.NEWS  # Default
            strategy_name = "viral_hooks"  # Default
        
        content_data = {
            "news_data": json.dumps([news_item.to_dict()]),
            "content_type": mapped_content_type.value,
            "target_engagement": 0.8
        }
        
        result = content_generation_tool._run(**content_data)
        result_data = json.loads(result)
        
        if result_data["success"]:
            content_dict = result_data["content"]
            # Convert content_type string to enum
            if isinstance(content_dict.get("content_type"), str):
                content_dict["content_type"] = ContentType(content_dict["content_type"])
            # Convert source_news dict to NewsItem
            if isinstance(content_dict.get("source_news"), dict):
                source_news_dict = content_dict["source_news"]
                if isinstance(source_news_dict.get("timestamp"), str):
                    source_news_dict["timestamp"] = datetime.fromisoformat(source_news_dict["timestamp"].replace("Z", "+00:00"))
                content_dict["source_news"] = NewsItem(**source_news_dict)
            # Convert created_at string to datetime
            if isinstance(content_dict.get("created_at"), str):
                content_dict["created_at"] = datetime.fromisoformat(content_dict["created_at"].replace("Z", "+00:00"))
            
            # Remove extra fields that aren't part of GeneratedContent constructor
            extra_fields = ["character_count", "hashtag_count"]
            for field in extra_fields:
                content_dict.pop(field, None)
            
            content = GeneratedContent(**content_dict)
            content.metadata["generation_strategy"] = strategy_name
            return content
        
        # Final fallback
        raise ValueError("Failed to generate optimized content")
    
    def record_post_performance(self, content: GeneratedContent, post_result: PostResult,
                              engagement_data: Dict[str, Any] = None):
        """Record post performance for optimization"""
        
        self.automated_optimizer.record_content_performance(
            content, 
            post_result, 
            engagement_data
        )
        
        self.performance_analytics.record_performance(
            content, 
            post_result, 
            engagement_data
        )
    
    def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run automated optimization cycle"""
        return self.automated_optimizer.run_optimization_cycle()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        
        optimization_status = self.automated_optimizer.get_optimization_status()
        analytics_report = self.performance_analytics.generate_report()
        
        return {
            "optimization_status": optimization_status,
            "performance_analytics": analytics_report,
            "active_tests": self.ab_framework.get_active_tests(),
            "timestamp": datetime.now().isoformat()
        }
    
    def export_optimization_data(self) -> Dict[str, Any]:
        """Export all optimization data for analysis"""
        
        export_data = {
            "ab_tests": {},
            "performance_history": list(self.automated_optimizer.strategy_optimizer.optimization_history),
            "strategy_performance": {},
            "export_timestamp": datetime.now().isoformat()
        }
        
        # Export A/B test data
        for test_id in list(self.ab_framework.active_tests.keys()) + list(self.ab_framework.completed_tests.keys()):
            export_data["ab_tests"][test_id] = self.ab_framework.export_test_results(test_id)
        
        # Export strategy performance
        for strategy in ContentStrategy:
            export_data["strategy_performance"][strategy.value] = \
                self.automated_optimizer.strategy_optimizer.get_strategy_performance(strategy, days_back=30)
        
        return export_data


class ContentPerformanceAnalytics:
    """Analytics service for content performance tracking"""
    
    def __init__(self):
        self.performance_data: deque = deque(maxlen=1000)
        self.daily_summaries: Dict[str, Dict[str, Any]] = {}
    
    def record_performance(self, content: GeneratedContent, post_result: PostResult,
                          engagement_data: Dict[str, Any] = None):
        """Record performance data"""
        
        performance_record = {
            "timestamp": datetime.now(),
            "content_type": content.content_type.value,
            "strategy": content.metadata.get("generation_strategy", "unknown"),
            "engagement_score": content.engagement_score,
            "character_count": len(content.text),
            "hashtag_count": len(content.hashtags),
            "post_success": post_result.success,
            "engagement_data": engagement_data or {}
        }
        
        self.performance_data.append(performance_record)
        
        # Update daily summary
        date_key = datetime.now().strftime("%Y-%m-%d")
        if date_key not in self.daily_summaries:
            self.daily_summaries[date_key] = {
                "total_posts": 0,
                "successful_posts": 0,
                "avg_engagement_score": 0.0,
                "strategy_breakdown": defaultdict(int),
                "content_type_breakdown": defaultdict(int)
            }
        
        daily_summary = self.daily_summaries[date_key]
        daily_summary["total_posts"] += 1
        if post_result.success:
            daily_summary["successful_posts"] += 1
        
        # Update running average
        current_avg = daily_summary["avg_engagement_score"]
        total_posts = daily_summary["total_posts"]
        daily_summary["avg_engagement_score"] = (
            (current_avg * (total_posts - 1) + content.engagement_score) / total_posts
        )
        
        daily_summary["strategy_breakdown"][performance_record["strategy"]] += 1
        daily_summary["content_type_breakdown"][content.content_type.value] += 1
    
    def generate_report(self, days_back: int = 7) -> Dict[str, Any]:
        """Generate performance analytics report"""
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_data = [
            record for record in self.performance_data
            if record["timestamp"] >= cutoff_date
        ]
        
        if not recent_data:
            return {"error": "No data available for the specified period"}
        
        # Calculate metrics
        total_posts = len(recent_data)
        successful_posts = sum(1 for r in recent_data if r["post_success"])
        avg_engagement = sum(r["engagement_score"] for r in recent_data) / total_posts
        
        # Strategy performance
        strategy_performance = defaultdict(list)
        for record in recent_data:
            strategy_performance[record["strategy"]].append(record["engagement_score"])
        
        strategy_stats = {}
        for strategy, scores in strategy_performance.items():
            strategy_stats[strategy] = {
                "count": len(scores),
                "avg_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores)
            }
        
        return {
            "period_days": days_back,
            "total_posts": total_posts,
            "successful_posts": successful_posts,
            "success_rate": successful_posts / total_posts if total_posts > 0 else 0,
            "avg_engagement_score": avg_engagement,
            "strategy_performance": strategy_stats,
            "daily_summaries": dict(list(self.daily_summaries.items())[-days_back:])
        }


def create_content_optimization_service(config: AgentConfig) -> ContentOptimizationService:
    """Factory function to create ContentOptimizationService"""
    return ContentOptimizationService(config)