#!/usr/bin/env python3
"""
Example usage of the A/B Testing and Content Optimization Framework
"""
import json
from datetime import datetime

from src.config.agent_config import AgentConfig
from src.models.data_models import NewsItem, PostResult, ContentType
from src.services.content_optimization_service import create_content_optimization_service
from src.services.ab_testing_framework import ContentStrategy, TestVariant
from src.tools.content_generation_tool import create_content_generation_tool


def main():
    """Demonstrate A/B testing and content optimization"""
    
    # Create configuration
    config = AgentConfig(
        perplexity_api_key="demo_key",
        bluesky_username="demo_user", 
        bluesky_password="demo_pass",
        max_post_length=300
    )
    
    # Create services
    optimization_service = create_content_optimization_service(config)
    content_tool = create_content_generation_tool(config)
    
    print("🚀 Content Optimization & A/B Testing Demo")
    print("=" * 50)
    
    # Initialize default A/B tests
    print("\n1. Initializing A/B Testing Framework...")
    test_id = optimization_service.initialize_default_tests()
    print(f"   ✅ Created A/B test: {test_id}")
    
    # Show active tests
    active_tests = optimization_service.ab_framework.get_active_tests()
    print(f"   📊 Active tests: {len(active_tests)}")
    for test in active_tests:
        print(f"      - {test['name']}: {test['variants']} variants")
    
    # Create sample news items
    sample_news = [
        NewsItem(
            headline="Bitcoin Reaches New All-Time High of $80,000",
            summary="Bitcoin has surged to a new record high of $80,000, driven by institutional adoption and ETF approvals.",
            source="CryptoNews",
            timestamp=datetime.now(),
            relevance_score=0.95,
            topics=["Bitcoin", "Price", "ATH", "Institutional"]
        ),
        NewsItem(
            headline="Ethereum 2.0 Staking Rewards Increase to 5.2%",
            summary="Ethereum staking rewards have increased to 5.2% APY as more validators join the network.",
            source="EthereumDaily",
            timestamp=datetime.now(),
            relevance_score=0.88,
            topics=["Ethereum", "Staking", "Rewards", "ETH2"]
        ),
        NewsItem(
            headline="DeFi Protocol Launches Revolutionary Yield Farming",
            summary="A new DeFi protocol has launched with innovative yield farming mechanisms offering up to 15% APY.",
            source="DeFiTimes",
            timestamp=datetime.now(),
            relevance_score=0.82,
            topics=["DeFi", "Yield Farming", "Innovation"]
        )
    ]
    
    print(f"\n2. Generating Optimized Content for {len(sample_news)} News Items...")
    
    # Generate content using A/B testing
    generated_contents = []
    for i, news_item in enumerate(sample_news):
        print(f"\n   📰 News {i+1}: {news_item.headline[:50]}...")
        
        # Generate optimized content
        content = optimization_service.generate_optimized_content(news_item, content_tool)
        generated_contents.append(content)
        
        # Show which strategy was used
        strategy = content.metadata.get("generation_strategy", "unknown")
        ab_test_info = ""
        if "ab_test_variant_id" in content.metadata:
            ab_test_info = f" (A/B Test: {content.metadata['ab_test_variant_id']})"
        
        print(f"   🎯 Strategy: {strategy}{ab_test_info}")
        print(f"   📝 Content: {content.text}")
        print(f"   📊 Engagement Score: {content.engagement_score:.2f}")
        print(f"   🏷️  Hashtags: {', '.join(content.hashtags)}")
        
        # Simulate posting and record performance
        post_result = PostResult(
            success=True,
            post_id=f"post_{i+1}",
            timestamp=datetime.now(),
            content=content
        )
        
        # Simulate engagement data
        engagement_data = {
            "likes": 15 + (i * 5),
            "reposts": 8 + (i * 2),
            "replies": 3 + i,
            "clicks": 12 + (i * 3)
        }
        
        # Record performance
        optimization_service.record_post_performance(content, post_result, engagement_data)
        print(f"   📈 Simulated Engagement: {engagement_data}")
    
    print(f"\n3. Running Optimization Cycle...")
    
    # Run optimization cycle
    optimization_result = optimization_service.run_optimization_cycle()
    print(f"   ✅ Optimization Status: {optimization_result['status']}")
    print(f"   🔧 Actions Taken: {len(optimization_result['actions'])}")
    
    for action in optimization_result['actions']:
        print(f"      - {action['rule']}: {action['action']} for {action['strategy']}")
    
    print(f"\n4. Performance Analytics...")
    
    # Get performance report
    report = optimization_service.get_performance_report()
    analytics = report['performance_analytics']
    
    print(f"   📊 Total Posts: {analytics['total_posts']}")
    print(f"   ✅ Success Rate: {analytics['success_rate']:.1%}")
    print(f"   🎯 Avg Engagement: {analytics['avg_engagement_score']:.2f}")
    
    print(f"\n   📈 Strategy Performance:")
    for strategy, stats in analytics['strategy_performance'].items():
        if stats['count'] > 0:
            print(f"      - {strategy}: {stats['avg_score']:.2f} avg ({stats['count']} posts)")
    
    print(f"\n5. A/B Test Analysis...")
    
    # Analyze A/B test results
    if active_tests:
        test_id = active_tests[0]['id']
        analysis = optimization_service.ab_framework.analyze_test(test_id)
        
        print(f"   🧪 Test: {analysis['test_name']}")
        print(f"   📊 Sample Size: {analysis['sample_size']}")
        print(f"   ✅ Sufficient Data: {analysis['has_sufficient_data']}")
        
        print(f"\n   🏆 Variant Performance:")
        for variant_id, variant_data in analysis['variants'].items():
            print(f"      - {variant_data['name']}: {variant_data['avg_engagement_score']:.2f} avg score")
            print(f"        ({variant_data['impressions']} impressions, {variant_data['engagement_rate']:.1%} engagement)")
        
        if analysis['has_winner']:
            winner = analysis['winner']
            print(f"\n   🥇 Winner: {winner['variant_name']} ({winner['strategy']})")
            print(f"      Score: {winner['avg_engagement_score']:.2f}")
        
        # Get recommendations
        recommendations = optimization_service.ab_framework.get_optimization_recommendations(test_id)
        if recommendations['recommendations']:
            print(f"\n   💡 Recommendations:")
            for rec in recommendations['recommendations']:
                print(f"      - {rec['message']}")
    
    print(f"\n6. Export Data...")
    
    # Export optimization data
    export_data = optimization_service.export_optimization_data()
    print(f"   📁 Exported {len(export_data['performance_history'])} performance records")
    print(f"   📁 Exported {len(export_data['ab_tests'])} A/B tests")
    print(f"   📁 Exported {len(export_data['strategy_performance'])} strategy performance records")
    
    print(f"\n✨ Demo Complete!")
    print(f"   The A/B testing framework is continuously optimizing content strategies")
    print(f"   based on engagement performance to maximize viral potential! 🚀")


if __name__ == "__main__":
    main()