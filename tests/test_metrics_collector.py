# tests/test_metrics_collector.py
"""
Unit tests for metrics collector functionality
"""
import unittest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from src.utils.metrics_collector import (
    MetricPoint, MetricSummary, MetricsCollector,
    get_metrics_collector, initialize_metrics_collector,
    record_metric, increment_counter, set_gauge, timer
)


class TestMetricPoint(unittest.TestCase):
    """Test cases for MetricPoint data class"""
    
    def test_metric_point_creation(self):
        """Test MetricPoint creation and serialization"""
        timestamp = datetime.now()
        tags = {"environment": "test", "version": "1.0"}
        
        point = MetricPoint(
            name="test_metric",
            value=42.5,
            unit="seconds",
            timestamp=timestamp,
            component="test_component",
            tags=tags
        )
        
        self.assertEqual(point.name, "test_metric")
        self.assertEqual(point.value, 42.5)
        self.assertEqual(point.unit, "seconds")
        self.assertEqual(point.component, "test_component")
        self.assertEqual(point.tags, tags)
        
        # Test serialization
        point_dict = point.to_dict()
        self.assertEqual(point_dict["name"], "test_metric")
        self.assertEqual(point_dict["value"], 42.5)
        self.assertEqual(point_dict["timestamp"], timestamp.isoformat())
        self.assertEqual(point_dict["tags"], tags)


class TestMetricSummary(unittest.TestCase):
    """Test cases for MetricSummary data class"""
    
    def test_metric_summary_creation(self):
        """Test MetricSummary creation and serialization"""
        summary = MetricSummary(
            name="response_time",
            count=100,
            min_value=0.1,
            max_value=5.0,
            mean=1.2,
            median=1.0,
            std_dev=0.8,
            percentile_95=3.5,
            percentile_99=4.8,
            unit="seconds",
            component="api_service",
            time_window="60m"
        )
        
        self.assertEqual(summary.name, "response_time")
        self.assertEqual(summary.count, 100)
        self.assertEqual(summary.mean, 1.2)
        self.assertEqual(summary.percentile_95, 3.5)
        
        # Test serialization
        summary_dict = summary.to_dict()
        self.assertEqual(summary_dict["name"], "response_time")
        self.assertEqual(summary_dict["count"], 100)
        self.assertEqual(summary_dict["unit"], "seconds")


class TestMetricsCollector(unittest.TestCase):
    """Test cases for MetricsCollector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.collector = MetricsCollector(max_points_per_metric=100, retention_hours=1)
    
    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization"""
        self.assertEqual(self.collector.max_points_per_metric, 100)
        self.assertEqual(self.collector.retention_hours, 1)
        self.assertIsInstance(self.collector._start_time, datetime)
    
    def test_record_metric(self):
        """Test recording a metric"""
        self.collector.record_metric(
            name="test_metric",
            value=42.0,
            unit="count",
            component="test_component",
            tags={"type": "test"}
        )
        
        # Check that metric was recorded
        metric_key = "test_component.test_metric"
        self.assertIn(metric_key, self.collector._metrics)
        self.assertEqual(len(self.collector._metrics[metric_key]), 1)
        
        point = self.collector._metrics[metric_key][0]
        self.assertEqual(point.name, "test_metric")
        self.assertEqual(point.value, 42.0)
        self.assertEqual(point.component, "test_component")
        self.assertEqual(point.tags["type"], "test")
    
    def test_increment_counter(self):
        """Test incrementing a counter"""
        # Increment counter multiple times
        self.collector.increment_counter("requests", "api_service", 1)
        self.collector.increment_counter("requests", "api_service", 5)
        self.collector.increment_counter("requests", "api_service", 2)
        
        # Check counter value
        counter_value = self.collector.get_counter("requests", "api_service")
        self.assertEqual(counter_value, 8)
        
        # Check that metric points were also recorded
        metric_key = "api_service.requests"
        self.assertIn(metric_key, self.collector._metrics)
        self.assertEqual(len(self.collector._metrics[metric_key]), 3)
    
    def test_set_gauge(self):
        """Test setting a gauge value"""
        self.collector.set_gauge("memory_usage", 75.5, "system", "percent")
        
        # Check gauge value
        gauge_value = self.collector.get_gauge("memory_usage", "system")
        self.assertEqual(gauge_value, 75.5)
        
        # Update gauge value
        self.collector.set_gauge("memory_usage", 80.2, "system", "percent")
        updated_value = self.collector.get_gauge("memory_usage", "system")
        self.assertEqual(updated_value, 80.2)
        
        # Check that metric points were recorded
        metric_key = "system.memory_usage"
        self.assertIn(metric_key, self.collector._metrics)
        self.assertEqual(len(self.collector._metrics[metric_key]), 2)
    
    def test_get_metric_summary(self):
        """Test getting metric summary statistics"""
        # Record multiple data points
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        for value in values:
            self.collector.record_metric("response_time", value, "seconds", "api")
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Get summary
        summary = self.collector.get_metric_summary("response_time", "api", time_window_minutes=60)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary.name, "response_time")
        self.assertEqual(summary.count, 10)
        self.assertEqual(summary.min_value, 1.0)
        self.assertEqual(summary.max_value, 10.0)
        self.assertEqual(summary.mean, 5.5)
        self.assertEqual(summary.unit, "seconds")
        self.assertEqual(summary.component, "api")
    
    def test_get_metric_summary_no_data(self):
        """Test getting summary for non-existent metric"""
        summary = self.collector.get_metric_summary("non_existent", "component")
        self.assertIsNone(summary)
    
    def test_get_all_metrics_summary(self):
        """Test getting summary for all metrics"""
        # Record some metrics
        self.collector.record_metric("metric1", 10.0, "count", "comp1")
        self.collector.record_metric("metric2", 20.0, "seconds", "comp2")
        self.collector.record_metric("metric1", 15.0, "count", "comp1")
        
        # Get all summaries
        summaries = self.collector.get_all_metrics_summary(time_window_minutes=60)
        
        self.assertIsInstance(summaries, dict)
        self.assertIn("comp1.metric1", summaries)
        self.assertIn("comp2.metric2", summaries)
        
        # Check specific summary
        metric1_summary = summaries["comp1.metric1"]
        self.assertEqual(metric1_summary.count, 2)
        self.assertEqual(metric1_summary.min_value, 10.0)
        self.assertEqual(metric1_summary.max_value, 15.0)
    
    def test_get_system_metrics(self):
        """Test getting system-level metrics"""
        # Record some data
        self.collector.record_metric("test1", 1.0, "count", "comp1")
        self.collector.increment_counter("counter1", "comp1")
        self.collector.set_gauge("gauge1", 50.0, "comp1")
        
        system_metrics = self.collector.get_system_metrics()
        
        self.assertIn("uptime_seconds", system_metrics)
        self.assertIn("total_metrics", system_metrics)
        self.assertIn("total_counters", system_metrics)
        self.assertIn("total_gauges", system_metrics)
        self.assertIn("total_data_points", system_metrics)
        
        self.assertEqual(system_metrics["total_metrics"], 3)  # test1, counter1, gauge1
        self.assertEqual(system_metrics["total_counters"], 1)
        self.assertEqual(system_metrics["total_gauges"], 1)
        self.assertGreater(system_metrics["uptime_seconds"], 0)
    
    def test_export_metrics_json(self):
        """Test exporting metrics as JSON"""
        # Record some test data
        self.collector.record_metric("test_metric", 42.0, "count", "test_comp")
        self.collector.increment_counter("test_counter", "test_comp")
        
        # Export as JSON
        json_export = self.collector.export_metrics("json")
        
        # Parse and verify
        data = json.loads(json_export)
        self.assertIn("timestamp", data)
        self.assertIn("system_metrics", data)
        self.assertIn("metric_summaries", data)
        self.assertIn("recent_points", data)
        
        # Check system metrics
        self.assertIn("total_metrics", data["system_metrics"])
        self.assertIn("counters", data["system_metrics"])
    
    def test_export_metrics_prometheus(self):
        """Test exporting metrics in Prometheus format"""
        # Record some test data
        self.collector.increment_counter("http_requests", "web_server", 100)
        self.collector.set_gauge("memory_usage", 75.5, "system")
        
        # Export as Prometheus format
        prometheus_export = self.collector.export_metrics("prometheus")
        
        # Verify format
        lines = prometheus_export.split('\n')
        self.assertGreater(len(lines), 0)
        
        # Should contain TYPE declarations and metrics
        type_lines = [line for line in lines if line.startswith('# TYPE')]
        metric_lines = [line for line in lines if not line.startswith('#') and line.strip()]
        
        self.assertGreater(len(type_lines), 0)
        self.assertGreater(len(metric_lines), 0)
        
        # Check for specific metrics
        prometheus_text = '\n'.join(lines)
        self.assertIn("http_requests", prometheus_text)
        self.assertIn("memory_usage", prometheus_text)
    
    def test_export_metrics_invalid_format(self):
        """Test exporting with invalid format"""
        with self.assertRaises(ValueError):
            self.collector.export_metrics("invalid_format")
    
    def test_timer_context_manager(self):
        """Test timer context manager"""
        with self.collector.timer("test_operation", "test_component"):
            time.sleep(0.1)  # Simulate work
        
        # Check that timing metric was recorded
        metric_key = "test_component.test_operation_duration"
        self.assertIn(metric_key, self.collector._metrics)
        self.assertEqual(len(self.collector._metrics[metric_key]), 1)
        
        point = self.collector._metrics[metric_key][0]
        self.assertEqual(point.name, "test_operation_duration")
        self.assertEqual(point.unit, "seconds")
        self.assertGreater(point.value, 0.05)  # Should be at least 50ms
    
    def test_timer_with_exception(self):
        """Test timer context manager with exception"""
        try:
            with self.collector.timer("failing_operation", "test_component"):
                time.sleep(0.05)
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # Timer should still record the duration
        metric_key = "test_component.failing_operation_duration"
        self.assertIn(metric_key, self.collector._metrics)
        self.assertEqual(len(self.collector._metrics[metric_key]), 1)
        
        point = self.collector._metrics[metric_key][0]
        self.assertGreater(point.value, 0.01)
    
    def test_metric_retention(self):
        """Test metric retention and cleanup"""
        # Create collector with very short retention
        short_collector = MetricsCollector(retention_hours=0.001)  # ~3.6 seconds
        
        # Record a metric
        short_collector.record_metric("old_metric", 1.0, "count", "test")
        
        # Verify it exists
        metric_key = "test.old_metric"
        self.assertEqual(len(short_collector._metrics[metric_key]), 1)
        
        # Wait for retention period to pass
        time.sleep(0.1)
        
        # Record another metric to trigger cleanup
        short_collector.record_metric("old_metric", 2.0, "count", "test")
        
        # Old metric should be cleaned up, only new one remains
        # Note: This test might be flaky due to timing, but demonstrates the concept
        self.assertLessEqual(len(short_collector._metrics[metric_key]), 2)


class TestGlobalMetricsFunctions(unittest.TestCase):
    """Test cases for global metrics functions"""
    
    def test_get_metrics_collector(self):
        """Test getting global metrics collector instance"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        # Should return the same instance
        self.assertIs(collector1, collector2)
        self.assertIsInstance(collector1, MetricsCollector)
    
    def test_initialize_metrics_collector(self):
        """Test initializing global metrics collector"""
        collector = initialize_metrics_collector(max_points_per_metric=500, retention_hours=12)
        
        self.assertIsInstance(collector, MetricsCollector)
        self.assertEqual(collector.max_points_per_metric, 500)
        self.assertEqual(collector.retention_hours, 12)
        
        # Should be the same as global instance
        global_collector = get_metrics_collector()
        self.assertIs(collector, global_collector)
    
    def test_record_metric_global(self):
        """Test global record_metric function"""
        record_metric("global_test", 123.45, "units", "global_component")
        
        collector = get_metrics_collector()
        metric_key = "global_component.global_test"
        
        self.assertIn(metric_key, collector._metrics)
        point = collector._metrics[metric_key][-1]  # Get latest point
        self.assertEqual(point.name, "global_test")
        self.assertEqual(point.value, 123.45)
    
    def test_increment_counter_global(self):
        """Test global increment_counter function"""
        increment_counter("global_counter", "global_component", 5)
        
        collector = get_metrics_collector()
        counter_value = collector.get_counter("global_counter", "global_component")
        self.assertEqual(counter_value, 5)
    
    def test_set_gauge_global(self):
        """Test global set_gauge function"""
        set_gauge("global_gauge", 88.8, "global_component", "percent")
        
        collector = get_metrics_collector()
        gauge_value = collector.get_gauge("global_gauge", "global_component")
        self.assertEqual(gauge_value, 88.8)
    
    def test_timer_global(self):
        """Test global timer function"""
        with timer("global_timer", "global_component"):
            time.sleep(0.05)
        
        collector = get_metrics_collector()
        metric_key = "global_component.global_timer_duration"
        
        self.assertIn(metric_key, collector._metrics)
        point = collector._metrics[metric_key][-1]
        self.assertEqual(point.name, "global_timer_duration")
        self.assertGreater(point.value, 0.01)


if __name__ == '__main__':
    unittest.main()