# src/services/ab_testing_framework.py
"""
A/B Testing Framework for content optimization and performance comparison
"""
import json
import logging
import random
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from collections import defaultdict, deque

from ..models.data_models import GeneratedContent, PostResult, ContentType

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """A/B test status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class ContentStrategy(Enum):
    """Content generation strategy enumeration"""
    VIRAL_HOOKS = "viral_hooks"
    ANALYTICAL = "analytical"
    CONTROVERSIAL = "controversial"
    EDUCATIONAL = "educational"
    MARKET_FOCUSED = "market_focused"
    COMMUNITY_DRIVEN = "community_driven"


@dataclass
class TestVariant:
    """A/B test variant configuration"""
    id: str
    name: str
    strategy: ContentStrategy
    parameters: Dict[str, Any] = field(default_factory=dict)
    weight: float = 0.5  # Traffic allocation weight
    
    def __post_init__(self):
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError("weight must be between 0.0 and 1.0")


@dataclass
class TestMetrics:
    """Performance metrics for A/B test variants"""
    variant_id: str
    impressions: int = 0
    engagements: int = 0
    likes: int = 0
    reposts: int = 0
    replies: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0
    avg_engagement_score: float = 0.0
    conversion_rate: float = 0.0
    
    def calculate_engagement_rate(self):
        """Calculate engagement rate"""
        if self.impressions > 0:
            self.engagement_rate = self.engagements / self.impressions
        else:
            self.engagement_rate = 0.0
    
    def calculate_conversion_rate(self):
        """Calculate conversion rate (clicks to impressions)"""
        if self.impressions > 0:
            self.conversion_rate = self.clicks / self.impressions
        else:
            self.conversion_rate = 0.0
    
    def update_metrics(self, post_result: PostResult, engagement_data: Dict[str, Any] = None):
        """Update metrics with new post result"""
        self.impressions += 1
        
        if engagement_data:
            self.likes += engagement_data.get('likes', 0)
            self.reposts += engagement_data.get('reposts', 0)
            self.replies += engagement_data.get('replies', 0)
            self.clicks += engagement_data.get('clicks', 0)
            self.engagements += sum([
                engagement_data.get('likes', 0),
                engagement_data.get('reposts', 0),
                engagement_data.get('replies', 0)
            ])
        
        # Update engagement score
        if post_result.content.engagement_score > 0:
            current_total = self.avg_engagement_score * (self.impressions - 1)
            self.avg_engagement_score = (current_total + post_result.content.engagement_score) / self.impressions
        
        self.calculate_engagement_rate()
        self.calculate_conversion_rate()


@dataclass
class ABTest:
    """A/B test configuration and state"""
    id: str
    name: str
    description: str
    variants: List[TestVariant]
    status: TestStatus = TestStatus.ACTIVE
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    min_sample_size: int = 100
    confidence_level: float = 0.95
    metrics: Dict[str, TestMetrics] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Initialize metrics for each variant
        for variant in self.variants:
            if variant.id not in self.metrics:
                self.metrics[variant.id] = TestMetrics(variant_id=variant.id)
        
        # Validate weights sum to 1.0
        total_weight = sum(variant.weight for variant in self.variants)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError("Variant weights must sum to 1.0")
    
    def is_active(self) -> bool:
        """Check if test is currently active"""
        return (self.status == TestStatus.ACTIVE and 
                (self.end_date is None or datetime.now() < self.end_date))
    
    def get_sample_size(self) -> int:
        """Get total sample size across all variants"""
        return sum(metrics.impressions for metrics in self.metrics.values())
    
    def has_sufficient_data(self) -> bool:
        """Check if test has sufficient data for statistical significance"""
        return self.get_sample_size() >= self.min_sample_size
    
    def select_variant(self) -> TestVariant:
        """Select a variant based on weights"""
        if not self.is_active():
            return None
        
        rand = random.random()
        cumulative_weight = 0.0
        
        for variant in self.variants:
            cumulative_weight += variant.weight
            if rand <= cumulative_weight:
                return variant
        
        # Fallback to last variant
        return self.variants[-1]


class StatisticalAnalyzer:
    """Statistical analysis for A/B test results"""
    
    @staticmethod
    def calculate_confidence_interval(data: List[float], confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for a dataset"""
        if len(data) < 2:
            return (0.0, 0.0)
        
        mean = statistics.mean(data)
        std_dev = statistics.stdev(data)
        n = len(data)
        
        # Use t-distribution for small samples
        if n < 30:
            # Simplified t-value approximation
            t_value = 2.0 if confidence_level >= 0.95 else 1.65
        else:
            # Normal distribution z-values
            t_value = 1.96 if confidence_level >= 0.95 else 1.65
        
        margin_of_error = t_value * (std_dev / (n ** 0.5))
        
        return (mean - margin_of_error, mean + margin_of_error)
    
    @staticmethod
    def calculate_statistical_significance(variant_a_data: List[float], 
                                         variant_b_data: List[float],
                                         confidence_level: float = 0.95) -> Dict[str, Any]:
        """Calculate statistical significance between two variants"""
        if len(variant_a_data) < 2 or len(variant_b_data) < 2:
            return {
                "is_significant": False,
                "p_value": 1.0,
                "confidence_level": confidence_level,
                "error": "Insufficient data for statistical analysis"
            }
        
        mean_a = statistics.mean(variant_a_data)
        mean_b = statistics.mean(variant_b_data)
        
        # Simplified statistical test (in practice, would use proper t-test)
        # This is a basic implementation for demonstration
        std_a = statistics.stdev(variant_a_data) if len(variant_a_data) > 1 else 0
        std_b = statistics.stdev(variant_b_data) if len(variant_b_data) > 1 else 0
        
        n_a = len(variant_a_data)
        n_b = len(variant_b_data)
        
        # Pooled standard error
        pooled_se = ((std_a ** 2 / n_a) + (std_b ** 2 / n_b)) ** 0.5
        
        if pooled_se == 0:
            return {
                "is_significant": abs(mean_a - mean_b) > 0,
                "p_value": 0.0 if abs(mean_a - mean_b) > 0 else 1.0,
                "confidence_level": confidence_level,
                "mean_difference": mean_a - mean_b,
                "effect_size": 0.0
            }
        
        # T-statistic
        t_stat = abs(mean_a - mean_b) / pooled_se
        
        # Simplified p-value calculation (approximation)
        if t_stat > 2.0:
            p_value = 0.05
        elif t_stat > 1.65:
            p_value = 0.1
        else:
            p_value = 0.2
        
        is_significant = p_value < (1 - confidence_level)
        effect_size = abs(mean_a - mean_b) / max(std_a, std_b, 0.1)
        
        return {
            "is_significant": is_significant,
            "p_value": p_value,
            "confidence_level": confidence_level,
            "mean_difference": mean_a - mean_b,
            "effect_size": effect_size,
            "t_statistic": t_stat
        }


class ABTestingFramework:
    """Main A/B testing framework for content optimization"""
    
    def __init__(self, max_concurrent_tests: int = 5):
        self.active_tests: Dict[str, ABTest] = {}
        self.completed_tests: Dict[str, ABTest] = {}
        self.max_concurrent_tests = max_concurrent_tests
        self.analyzer = StatisticalAnalyzer()
        self.performance_history: deque = deque(maxlen=1000)
        
    def create_test(self, 
                   name: str,
                   description: str,
                   variants: List[TestVariant],
                   duration_days: Optional[int] = None,
                   min_sample_size: int = 100) -> str:
        """Create a new A/B test"""
        
        if len(self.active_tests) >= self.max_concurrent_tests:
            raise ValueError(f"Maximum concurrent tests ({self.max_concurrent_tests}) reached")
        
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_tests)}"
        
        end_date = None
        if duration_days:
            end_date = datetime.now() + timedelta(days=duration_days)
        
        test = ABTest(
            id=test_id,
            name=name,
            description=description,
            variants=variants,
            end_date=end_date,
            min_sample_size=min_sample_size
        )
        
        self.active_tests[test_id] = test
        
        logger.info(f"Created A/B test: {name} (ID: {test_id}) with {len(variants)} variants")
        
        return test_id
    
    def get_variant_for_content(self, test_id: str) -> Optional[TestVariant]:
        """Get variant for content generation"""
        if test_id not in self.active_tests:
            return None
        
        test = self.active_tests[test_id]
        if not test.is_active():
            return None
        
        return test.select_variant()
    
    def record_result(self, test_id: str, variant_id: str, post_result: PostResult, 
                     engagement_data: Dict[str, Any] = None):
        """Record A/B test result"""
        if test_id not in self.active_tests:
            logger.warning(f"Test {test_id} not found in active tests")
            return
        
        test = self.active_tests[test_id]
        if variant_id not in test.metrics:
            logger.warning(f"Variant {variant_id} not found in test {test_id}")
            return
        
        # Update metrics
        test.metrics[variant_id].update_metrics(post_result, engagement_data)
        
        # Store performance history
        self.performance_history.append({
            "timestamp": datetime.now(),
            "test_id": test_id,
            "variant_id": variant_id,
            "engagement_score": post_result.content.engagement_score,
            "success": post_result.success,
            "engagement_data": engagement_data or {}
        })
        
        logger.info(f"Recorded result for test {test_id}, variant {variant_id}")
        
        # Check if test should be completed
        self._check_test_completion(test_id)
    
    def _check_test_completion(self, test_id: str):
        """Check if test should be completed based on criteria"""
        test = self.active_tests[test_id]
        
        # Check if test has ended by date
        if test.end_date and datetime.now() >= test.end_date:
            self._complete_test(test_id, "Test duration completed")
            return
        
        # Check if test has sufficient data and significant results
        if test.has_sufficient_data():
            analysis = self.analyze_test(test_id)
            if analysis and analysis.get("has_winner", False):
                significance = analysis.get("statistical_significance", {})
                if significance.get("is_significant", False):
                    self._complete_test(test_id, "Statistical significance achieved")
    
    def _complete_test(self, test_id: str, reason: str):
        """Complete an A/B test"""
        if test_id not in self.active_tests:
            return
        
        test = self.active_tests[test_id]
        test.status = TestStatus.COMPLETED
        test.metadata["completion_reason"] = reason
        test.metadata["completion_date"] = datetime.now().isoformat()
        
        # Move to completed tests
        self.completed_tests[test_id] = test
        del self.active_tests[test_id]
        
        logger.info(f"Completed A/B test {test_id}: {reason}")
    
    def analyze_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Analyze A/B test results"""
        test = self.active_tests.get(test_id) or self.completed_tests.get(test_id)
        if not test:
            return None
        
        analysis = {
            "test_id": test_id,
            "test_name": test.name,
            "status": test.status.value,
            "sample_size": test.get_sample_size(),
            "has_sufficient_data": test.has_sufficient_data(),
            "variants": {},
            "winner": None,
            "has_winner": False,
            "statistical_significance": {}
        }
        
        # Analyze each variant
        best_variant = None
        best_score = 0.0
        
        variant_scores = []
        for variant in test.variants:
            metrics = test.metrics[variant.id]
            
            variant_analysis = {
                "id": variant.id,
                "name": variant.name,
                "strategy": variant.strategy.value,
                "impressions": metrics.impressions,
                "engagement_rate": metrics.engagement_rate,
                "avg_engagement_score": metrics.avg_engagement_score,
                "conversion_rate": metrics.conversion_rate,
                "total_engagements": metrics.engagements
            }
            
            analysis["variants"][variant.id] = variant_analysis
            
            # Track best performing variant
            if metrics.avg_engagement_score > best_score:
                best_score = metrics.avg_engagement_score
                best_variant = variant
            
            # Collect scores for statistical analysis
            if metrics.impressions > 0:
                variant_scores.append({
                    "variant_id": variant.id,
                    "scores": [metrics.avg_engagement_score] * metrics.impressions
                })
        
        # Determine winner
        if best_variant and len(test.variants) >= 2:
            analysis["winner"] = {
                "variant_id": best_variant.id,
                "variant_name": best_variant.name,
                "strategy": best_variant.strategy.value,
                "avg_engagement_score": best_score
            }
            analysis["has_winner"] = True
            
            # Statistical significance analysis
            if len(variant_scores) >= 2 and all(len(vs["scores"]) >= 2 for vs in variant_scores):
                # Compare top 2 variants
                sorted_variants = sorted(variant_scores, 
                                       key=lambda x: sum(x["scores"])/len(x["scores"]), 
                                       reverse=True)
                
                if len(sorted_variants) >= 2:
                    significance = self.analyzer.calculate_statistical_significance(
                        sorted_variants[0]["scores"],
                        sorted_variants[1]["scores"]
                    )
                    analysis["statistical_significance"] = significance
        
        return analysis
    
    def get_optimization_recommendations(self, test_id: str) -> Dict[str, Any]:
        """Get optimization recommendations based on test results"""
        analysis = self.analyze_test(test_id)
        if not analysis:
            return {"error": "Test not found"}
        
        recommendations = {
            "test_id": test_id,
            "recommendations": [],
            "next_steps": [],
            "performance_insights": []
        }
        
        if analysis["has_winner"]:
            winner = analysis["winner"]
            recommendations["recommendations"].append({
                "type": "strategy_optimization",
                "message": f"Use {winner['strategy']} strategy as primary approach",
                "confidence": "high" if analysis.get("statistical_significance", {}).get("is_significant", False) else "medium",
                "expected_improvement": f"{winner['avg_engagement_score']:.2f} avg engagement score"
            })
        
        # Performance insights
        variant_performances = []
        for variant_id, variant_data in analysis["variants"].items():
            variant_performances.append({
                "strategy": variant_data["strategy"],
                "engagement_rate": variant_data["engagement_rate"],
                "avg_score": variant_data["avg_engagement_score"]
            })
        
        # Sort by performance
        variant_performances.sort(key=lambda x: x["avg_score"], reverse=True)
        
        recommendations["performance_insights"] = [
            f"{perf['strategy']} strategy: {perf['avg_score']:.2f} avg score, {perf['engagement_rate']:.2%} engagement rate"
            for perf in variant_performances
        ]
        
        # Next steps
        if not analysis["has_sufficient_data"]:
            recommendations["next_steps"].append("Continue test to gather more data for statistical significance")
        elif analysis["has_winner"]:
            recommendations["next_steps"].append("Implement winning strategy in production")
            recommendations["next_steps"].append("Design follow-up tests to optimize winning strategy further")
        
        return recommendations
    
    def get_active_tests(self) -> List[Dict[str, Any]]:
        """Get list of active tests"""
        return [
            {
                "id": test.id,
                "name": test.name,
                "description": test.description,
                "status": test.status.value,
                "sample_size": test.get_sample_size(),
                "start_date": test.start_date.isoformat(),
                "variants": len(test.variants)
            }
            for test in self.active_tests.values()
        ]
    
    def export_test_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Export complete test results"""
        test = self.active_tests.get(test_id) or self.completed_tests.get(test_id)
        if not test:
            return None
        
        return {
            "test_config": {
                "id": test.id,
                "name": test.name,
                "description": test.description,
                "status": test.status.value,
                "start_date": test.start_date.isoformat(),
                "end_date": test.end_date.isoformat() if test.end_date else None,
                "min_sample_size": test.min_sample_size,
                "variants": [
                    {
                        "id": v.id,
                        "name": v.name,
                        "strategy": v.strategy.value,
                        "parameters": v.parameters,
                        "weight": v.weight
                    }
                    for v in test.variants
                ]
            },
            "results": {
                "sample_size": test.get_sample_size(),
                "metrics": {
                    variant_id: {
                        "impressions": metrics.impressions,
                        "engagements": metrics.engagements,
                        "engagement_rate": metrics.engagement_rate,
                        "avg_engagement_score": metrics.avg_engagement_score,
                        "conversion_rate": metrics.conversion_rate,
                        "likes": metrics.likes,
                        "reposts": metrics.reposts,
                        "replies": metrics.replies,
                        "clicks": metrics.clicks
                    }
                    for variant_id, metrics in test.metrics.items()
                }
            },
            "analysis": self.analyze_test(test_id),
            "recommendations": self.get_optimization_recommendations(test_id)
        }


def create_ab_testing_framework(max_concurrent_tests: int = 5) -> ABTestingFramework:
    """Factory function to create ABTestingFramework instance"""
    return ABTestingFramework(max_concurrent_tests)