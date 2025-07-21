# tests/test_performance_testing.py
"""
Performance testing for scheduled execution scenarios
Tests system performance, resource usage, and scalability
"""
import pytest
import asyncio
import time
import threading
import psutil
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.config.agent_config import AgentConfig
from src.services.scheduler_service import SchedulerService
from src.models.data_models import PostResult
from tests.test_mock_services import MockServiceFactory


class PerformanceMonitor:
    """Monitor system performance during tests"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.cpu_samples = []
        self.memory_samples = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.monitoring = True
        self.cpu_samples = []
        self.memory_samples = []
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        self.end_time = time.time()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def _monitor_loop(self):
        """Monitor system resources in background thread"""
        while self.monitoring:
            try:
                # Get current process
                process = psutil.Process(os.getpid())
                
                # Sample CPU and memory usage
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                self.cpu_samples.append(cpu_percent)
                self.memory_samples.append(memory_mb)
                
                time.sleep(0.1)  # Sample every 100ms
            except:
                break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.cpu_samples or not self.memory_samples:
            return {}
        
        duration = self.end_time - self.start_time if self.end_time else 0
        
        return {
            "duration_seconds": duration,
            "cpu_usage": {
                "avg": sum(self.cpu_samples) / len(self.cpu_samples),
                "max": max(self.cpu_samples),
                "min": min(self.cpu_samples),
                "samples": len(self.cpu_samples)
            },
            "memory_usage_mb": {
                "avg": sum(self.memory_samples) / len(self.memory_samples),
                "max": max(self.memory_samples),
                "min": min(self.memory_samples),
                "samples": len(self.memory_samples)
            }
        }


class TestPerformanceScenarios:
    """Performance tests for various execution scenarios"""
    
    @pytest.fixture
    def performance_config(self):
        """Configuration optimized for performance testing"""
        return AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_password",
            posting_interval_minutes=1,  # Fast interval for testing
            max_execution_time_minutes=5,
            max_post_length=300,
            content_themes=["Bitcoin", "Ethereum", "Performance"],
            min_engagement_score=0.5,
            duplicate_threshold=0.8,
            max_retries=2
        )
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for performance testing"""
        llm = Mock()
        llm.predict = Mock(return_value="Performance test content")
        return llm
    
    @pytest.fixture
    def mock_services(self):
        """Mock services for performance testing"""
        return MockServiceFactory.create_test_suite_mocks(simulate_failures=False)
    
    @pytest.mark.asyncio
    async def test_single_workflow_performance(self, performance_config, mock_llm, mock_services):
        """Test performance of single workflow execution"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=performance_config)
        monitor = PerformanceMonitor()
        
        # Mock the tools with fast responses
        with patch.object(agent.news_tool, '_arun') as mock_news, \
             patch.object(agent.content_tool, '_arun') as mock_content, \
             patch.object(agent.social_tool, '_arun') as mock_social:
            
            # Setup fast mock responses
            mock_news.return_value = json.dumps({
                "success": True,
                "count": 1,
                "news_items": [{
                    "headline": "Test News",
                    "summary": "Test summary", 
                    "source": "Test",
                    "timestamp": "2024-01-01T00:00:00",
                    "relevance_score": 0.8,
                    "topics": ["Test"],
                    "url": None,
                    "raw_content": "test"
                }]
            })
            mock_content.return_value = json.dumps({
                "success": True,
                "content": {
                    "text": "🚀 Breaking: Test content shows significant developments in the cryptocurrency market! This could be a game-changer for institutional adoption. #test #crypto #breaking",
                    "hashtags": ["#test", "#crypto", "#breaking"],
                    "engagement_score": 0.8,
                    "content_type": "news",
                    "source_news": {
                        "headline": "Test News",
                        "summary": "Test summary",
                        "source": "Test", 
                        "timestamp": "2024-01-01T00:00:00",
                        "relevance_score": 0.8,
                        "topics": ["Test"],
                        "url": None,
                        "raw_content": "test"
                    },
                    "created_at": "2024-01-01T00:00:00"
                }
            })
            mock_social.return_value = {"success": True, "post_id": "test123", "timestamp": "2024-01-01T00:00:00", "retry_count": 0}
            
            # Start monitoring
            monitor.start_monitoring()
            
            # Execute workflow
            start_time = time.time()
            result = await agent.execute_workflow("performance test")
            end_time = time.time()
            
            # Stop monitoring
            monitor.stop_monitoring()
            
            # Verify result
            assert result.success is True
            
            # Analyze performance
            execution_time = end_time - start_time
            stats = monitor.get_stats()
            
            print(f"Single Workflow Performance:")
            print(f"  Execution Time: {execution_time:.3f}s")
            print(f"  CPU Usage: {stats.get('cpu_usage', {}).get('avg', 0):.1f}% avg")
            print(f"  Memory Usage: {stats.get('memory_usage_mb', {}).get('avg', 0):.1f}MB avg")
            
            # Performance assertions
            assert execution_time < 5.0  # Should complete within 5 seconds
            
            if stats.get('cpu_usage'):
                assert stats['cpu_usage']['avg'] < 50  # Should not use excessive CPU
            
            if stats.get('memory_usage_mb'):
                assert stats['memory_usage_mb']['max'] < 500  # Should not use excessive memory
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_performance(self, performance_config, mock_llm, mock_services):
        """Test performance with concurrent workflow executions"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=performance_config)
        monitor = PerformanceMonitor()
        
        # Mock the tools
        with patch.object(agent.news_tool, '_arun') as mock_news, \
             patch.object(agent.content_tool, '_arun') as mock_content, \
             patch.object(agent.social_tool, '_arun') as mock_social:
            
            # Setup mock responses with slight delays to simulate real API calls
            async def mock_news_with_delay(query):
                await asyncio.sleep(0.1)
                return '{"success": true, "count": 1, "news_items": [{"headline": "Concurrent Test", "summary": "Test", "source": "Test", "timestamp": "2024-01-01T00:00:00", "relevance_score": 0.8, "topics": ["Test"], "url": null, "raw_content": "test"}]}'
            
            async def mock_content_with_delay(news_data, content_type="news", target_engagement=0.7):
                await asyncio.sleep(0.2)
                return '{"success": true, "content": {"text": "Concurrent test #test", "hashtags": ["#test"], "engagement_score": 0.8, "content_type": "news", "source_news": {"headline": "Test"}, "created_at": "2024-01-01T00:00:00"}}'
            
            async def mock_social_with_delay(content, username, password):
                await asyncio.sleep(0.1)
                return {"success": True, "post_id": f"concurrent_{time.time()}", "timestamp": "2024-01-01T00:00:00", "retry_count": 0}
            
            mock_news.side_effect = mock_news_with_delay
            mock_content.side_effect = mock_content_with_delay
            mock_social.side_effect = mock_social_with_delay
            
            # Start monitoring
            monitor.start_monitoring()
            
            # Execute multiple concurrent workflows
            concurrent_count = 5
            start_time = time.time()
            
            tasks = []
            for i in range(concurrent_count):
                task = agent.execute_workflow(f"concurrent test {i}")
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Stop monitoring
            monitor.stop_monitoring()
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, PostResult) and r.success]
            failed_results = [r for r in results if isinstance(r, PostResult) and not r.success]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            total_time = end_time - start_time
            stats = monitor.get_stats()
            
            print(f"Concurrent Workflow Performance ({concurrent_count} workflows):")
            print(f"  Total Time: {total_time:.3f}s")
            print(f"  Successful: {len(successful_results)}")
            print(f"  Failed: {len(failed_results)}")
            print(f"  Exceptions: {len(exceptions)}")
            print(f"  CPU Usage: {stats.get('cpu_usage', {}).get('avg', 0):.1f}% avg, {stats.get('cpu_usage', {}).get('max', 0):.1f}% max")
            print(f"  Memory Usage: {stats.get('memory_usage_mb', {}).get('avg', 0):.1f}MB avg, {stats.get('memory_usage_mb', {}).get('max', 0):.1f}MB max")
            
            # Performance assertions
            assert len(exceptions) == 0  # No unhandled exceptions
            assert len(successful_results) >= concurrent_count * 0.8  # At least 80% success rate
            assert total_time < 10.0  # Should complete within 10 seconds
            
            # Resource usage should be reasonable
            if stats.get('cpu_usage'):
                assert stats['cpu_usage']['max'] < 80  # Should not max out CPU
            
            if stats.get('memory_usage_mb'):
                assert stats['memory_usage_mb']['max'] < 1000  # Should not use excessive memory
    
    def test_scheduler_performance(self, performance_config, mock_llm):
        """Test scheduler service performance"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=performance_config)
        scheduler = SchedulerService(agent=agent, config=performance_config)
        
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        # Test scheduler setup and teardown performance
        start_time = time.time()
        
        # Setup schedule
        scheduler._setup_schedule()
        
        # Simulate some scheduler operations
        for _ in range(10):
            scheduler._check_schedule()
            time.sleep(0.01)  # Small delay
        
        # Cleanup
        scheduler.stop()
        
        end_time = time.time()
        monitor.stop_monitoring()
        
        execution_time = end_time - start_time
        stats = monitor.get_stats()
        
        print(f"Scheduler Performance:")
        print(f"  Setup/Teardown Time: {execution_time:.3f}s")
        print(f"  CPU Usage: {stats.get('cpu_usage', {}).get('avg', 0):.1f}% avg")
        print(f"  Memory Usage: {stats.get('memory_usage_mb', {}).get('avg', 0):.1f}MB avg")
        
        # Performance assertions
        assert execution_time < 2.0  # Should be fast
        assert scheduler.is_running is False  # Should be properly stopped
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_config, mock_llm):
        """Test for memory leaks during repeated executions"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=performance_config)
        
        # Mock tools for fast execution
        with patch.object(agent.news_tool, '_arun') as mock_news, \
             patch.object(agent.content_tool, '_arun') as mock_content, \
             patch.object(agent.social_tool, '_arun') as mock_social:
            
            mock_news.return_value = '{"success": true, "count": 1, "news_items": [{"headline": "Memory Test", "summary": "Test", "source": "Test", "timestamp": "2024-01-01T00:00:00", "relevance_score": 0.8, "topics": ["Test"], "url": null, "raw_content": "test"}]}'
            mock_content.return_value = '{"success": true, "content": {"text": "Memory test #test", "hashtags": ["#test"], "engagement_score": 0.8, "content_type": "news", "source_news": {"headline": "Test"}, "created_at": "2024-01-01T00:00:00"}}'
            mock_social.return_value = {"success": True, "post_id": "memory_test", "timestamp": "2024-01-01T00:00:00", "retry_count": 0}
            
            # Measure initial memory
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            memory_samples = [initial_memory]
            
            # Execute workflows repeatedly
            iterations = 20
            for i in range(iterations):
                result = await agent.execute_workflow(f"memory test {i}")
                assert result.success is True
                
                # Sample memory every few iterations
                if i % 5 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)
                
                # Small delay to allow garbage collection
                await asyncio.sleep(0.01)
            
            # Final memory measurement
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(final_memory)
            
            # Analyze memory usage
            memory_growth = final_memory - initial_memory
            max_memory = max(memory_samples)
            avg_memory = sum(memory_samples) / len(memory_samples)
            
            print(f"Memory Leak Detection ({iterations} iterations):")
            print(f"  Initial Memory: {initial_memory:.1f}MB")
            print(f"  Final Memory: {final_memory:.1f}MB")
            print(f"  Memory Growth: {memory_growth:.1f}MB")
            print(f"  Max Memory: {max_memory:.1f}MB")
            print(f"  Avg Memory: {avg_memory:.1f}MB")
            
            # Memory leak assertions
            assert memory_growth < 50  # Should not grow more than 50MB
            assert max_memory < initial_memory + 100  # Should not exceed initial + 100MB
            
            # Check content history management
            assert len(agent.content_history) <= 50  # Should limit history size
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self, performance_config, mock_llm):
        """Test performance impact of error handling"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=performance_config)
        monitor = PerformanceMonitor()
        
        # Mock tools to simulate various error scenarios
        with patch.object(agent.news_tool, '_arun') as mock_news, \
             patch.object(agent.content_tool, '_arun') as mock_content, \
             patch.object(agent.social_tool, '_arun') as mock_social:
            
            # Setup error scenarios
            error_scenarios = [
                # News retrieval failure
                ('{"success": false, "error": "API error"}', None, None),
                # Content generation failure  
                ('{"success": true, "count": 1, "news_items": [{"headline": "Test", "summary": "Test", "source": "Test", "timestamp": "2024-01-01T00:00:00", "relevance_score": 0.8, "topics": ["Test"], "url": null, "raw_content": "test"}]}', '{"success": false, "error": "Generation failed"}', None),
                # Posting failure
                ('{"success": true, "count": 1, "news_items": [{"headline": "Test", "summary": "Test", "source": "Test", "timestamp": "2024-01-01T00:00:00", "relevance_score": 0.8, "topics": ["Test"], "url": null, "raw_content": "test"}]}', '{"success": true, "content": {"text": "Error test #test", "hashtags": ["#test"], "engagement_score": 0.8, "content_type": "news", "source_news": {"headline": "Test"}, "created_at": "2024-01-01T00:00:00"}}', {"success": False, "error_message": "Posting failed", "retry_count": 2})
            ]
            
            monitor.start_monitoring()
            start_time = time.time()
            
            results = []
            for i, (news_response, content_response, social_response) in enumerate(error_scenarios):
                mock_news.return_value = news_response
                if content_response:
                    mock_content.return_value = content_response
                if social_response:
                    mock_social.return_value = social_response
                
                result = await agent.execute_workflow(f"error test {i}")
                results.append(result)
            
            end_time = time.time()
            monitor.stop_monitoring()
            
            # Analyze error handling performance
            total_time = end_time - start_time
            stats = monitor.get_stats()
            
            failed_results = [r for r in results if not r.success]
            
            print(f"Error Handling Performance:")
            print(f"  Total Time: {total_time:.3f}s")
            print(f"  Failed Results: {len(failed_results)}/{len(results)}")
            print(f"  CPU Usage: {stats.get('cpu_usage', {}).get('avg', 0):.1f}% avg")
            print(f"  Memory Usage: {stats.get('memory_usage_mb', {}).get('avg', 0):.1f}MB avg")
            
            # Performance assertions
            assert len(failed_results) == len(error_scenarios)  # All should fail as expected
            assert total_time < 5.0  # Error handling should be fast
            
            # Verify error messages are present
            for result in failed_results:
                assert result.error_message is not None
                assert len(result.error_message) > 0
    
    @pytest.mark.asyncio
    async def test_content_filtering_performance(self, performance_config, mock_llm):
        """Test performance impact of content filtering"""
        agent = BlueskyCryptoAgent(llm=mock_llm, config=performance_config)
        monitor = PerformanceMonitor()
        
        # Create various content quality scenarios
        content_scenarios = [
            # High quality content
            {"text": "Bitcoin adoption continues to grow among institutional investors with strong technical fundamentals supporting long-term growth #bitcoin #institutional", "engagement_score": 0.9},
            # Medium quality content
            {"text": "Ethereum network upgrade shows promising results for scalability improvements #ethereum #upgrade", "engagement_score": 0.7},
            # Low quality content (should be filtered)
            {"text": "Buy crypto now! Moon! 🚀🚀🚀", "engagement_score": 0.3},
            # Duplicate-like content
            {"text": "Bitcoin adoption continues to grow among institutional investors with strong fundamentals #bitcoin", "engagement_score": 0.8},
        ]
        
        monitor.start_monitoring()
        start_time = time.time()
        
        # Test content filtering performance
        approved_count = 0
        filtered_count = 0
        
        for i, content_data in enumerate(content_scenarios):
            # Create mock generated content
            from src.models.data_models import GeneratedContent, NewsItem, ContentType
            
            news_item = NewsItem(
                headline=f"Test News {i}",
                summary="Test summary",
                source="Test",
                timestamp=datetime.now(),
                relevance_score=0.8,
                topics=["Test"],
                url=None
            )
            
            content = GeneratedContent(
                text=content_data["text"],
                hashtags=["#test"],
                engagement_score=content_data["engagement_score"],
                content_type=ContentType.NEWS,
                source_news=news_item
            )
            
            # Test filtering
            is_approved, filter_details = agent.content_filter.filter_content(content)
            
            if is_approved:
                approved_count += 1
                agent.content_filter.add_to_history(content)
            else:
                filtered_count += 1
        
        end_time = time.time()
        monitor.stop_monitoring()
        
        # Analyze filtering performance
        total_time = end_time - start_time
        stats = monitor.get_stats()
        
        print(f"Content Filtering Performance:")
        print(f"  Total Time: {total_time:.3f}s")
        print(f"  Approved: {approved_count}")
        print(f"  Filtered: {filtered_count}")
        print(f"  CPU Usage: {stats.get('cpu_usage', {}).get('avg', 0):.1f}% avg")
        print(f"  Memory Usage: {stats.get('memory_usage_mb', {}).get('avg', 0):.1f}MB avg")
        
        # Performance assertions
        assert total_time < 1.0  # Filtering should be very fast
        assert approved_count > 0  # Some content should be approved
        assert filtered_count > 0  # Some content should be filtered
        
        # Verify filtering logic worked
        assert approved_count + filtered_count == len(content_scenarios)


class TestScalabilityLimits:
    """Test system behavior at scalability limits"""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_high_volume_workflow_execution(self, performance_config, mock_llm):
        """Test system behavior with high volume of workflow executions"""
        # This test is marked as slow and may be skipped in regular test runs
        agent = BlueskyCryptoAgent(llm=mock_llm, config=performance_config)
        
        # Mock tools for fast execution
        with patch.object(agent.news_tool, '_arun') as mock_news, \
             patch.object(agent.content_tool, '_arun') as mock_content, \
             patch.object(agent.social_tool, '_arun') as mock_social:
            
            mock_news.return_value = '{"success": true, "count": 1, "news_items": [{"headline": "Volume Test", "summary": "Test", "source": "Test", "timestamp": "2024-01-01T00:00:00", "relevance_score": 0.8, "topics": ["Test"], "url": null, "raw_content": "test"}]}'
            mock_content.return_value = '{"success": true, "content": {"text": "Volume test content #test", "hashtags": ["#test"], "engagement_score": 0.8, "content_type": "news", "source_news": {"headline": "Test"}, "created_at": "2024-01-01T00:00:00"}}'
            mock_social.return_value = {"success": True, "post_id": "volume_test", "timestamp": "2024-01-01T00:00:00", "retry_count": 0}
            
            # Execute high volume of workflows
            volume = 50  # Adjust based on system capabilities
            start_time = time.time()
            
            # Use semaphore to limit concurrent executions
            semaphore = asyncio.Semaphore(10)  # Max 10 concurrent
            
            async def limited_workflow(i):
                async with semaphore:
                    return await agent.execute_workflow(f"volume test {i}")
            
            tasks = [limited_workflow(i) for i in range(volume)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, PostResult) and r.success]
            failed_results = [r for r in results if isinstance(r, PostResult) and not r.success]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            total_time = end_time - start_time
            throughput = len(successful_results) / total_time
            
            print(f"High Volume Test ({volume} workflows):")
            print(f"  Total Time: {total_time:.2f}s")
            print(f"  Successful: {len(successful_results)}")
            print(f"  Failed: {len(failed_results)}")
            print(f"  Exceptions: {len(exceptions)}")
            print(f"  Throughput: {throughput:.2f} workflows/second")
            
            # Scalability assertions
            assert len(exceptions) == 0  # No unhandled exceptions
            assert len(successful_results) >= volume * 0.9  # At least 90% success rate
            assert throughput > 1.0  # Should process at least 1 workflow per second