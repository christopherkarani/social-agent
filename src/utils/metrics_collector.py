# src/utils/metrics_collector.py
"""
Performance metrics collection and reporting system for the Bluesky Crypto Agent
"""
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import json
import statistics
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    component: str
    tags: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "tags": self.tags
        }


@dataclass
class MetricSummary:
    """Summary statistics for a metric"""
    name: str
    count: int
    min_value: float
    max_value: float
    mean: float
    median: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    unit: str
    component: str
    time_window: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class MetricsCollector:
    """
    Thread-safe metrics collection system with aggregation and reporting
    """
    
    def __init__(self, max_points_per_metric: int = 1000, retention_hours: int = 24):
        """
        Initialize metrics collector
        
        Args:
            max_points_per_metric: Maximum number of points to keep per metric
            retention_hours: How long to retain metrics data
        """
        self.max_points_per_metric = max_points_per_metric
        self.retention_hours = retention_hours
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self._lock = threading.RLock()
        self._start_time = datetime.now()
        
        # Performance counters
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        
        logger.info(f"MetricsCollector initialized with retention: {retention_hours}h, max points: {max_points_per_metric}")
    
    def record_metric(self, 
                     name: str, 
                     value: float, 
                     unit: str = "count",
                     component: str = "unknown",
                     tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a metric data point
        
        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            component: Component that generated the metric
            tags: Additional tags for the metric
        """
        if tags is None:
            tags = {}
        
        metric_point = MetricPoint(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            component=component,
            tags=tags
        )
        
        with self._lock:
            metric_key = f"{component}.{name}"
            self._metrics[metric_key].append(metric_point)
            
            # Clean up old metrics
            self._cleanup_old_metrics(metric_key)
        
        logger.debug(f"Recorded metric: {name}={value} {unit} from {component}")
    
    def increment_counter(self, name: str, component: str = "unknown", increment: int = 1) -> None:
        """
        Increment a counter metric
        
        Args:
            name: Counter name
            component: Component name
            increment: Amount to increment by
        """
        with self._lock:
            counter_key = f"{component}.{name}"
            self._counters[counter_key] += increment
        
        # Also record as a metric point
        self.record_metric(name, increment, "count", component, {"type": "counter"})
    
    def set_gauge(self, name: str, value: float, component: str = "unknown", unit: str = "value") -> None:
        """
        Set a gauge metric value
        
        Args:
            name: Gauge name
            value: Current value
            component: Component name
            unit: Unit of measurement
        """
        with self._lock:
            gauge_key = f"{component}.{name}"
            self._gauges[gauge_key] = value
        
        # Also record as a metric point
        self.record_metric(name, value, unit, component, {"type": "gauge"})
    
    def get_counter(self, name: str, component: str = "unknown") -> int:
        """Get current counter value"""
        with self._lock:
            counter_key = f"{component}.{name}"
            return self._counters.get(counter_key, 0)
    
    def get_gauge(self, name: str, component: str = "unknown") -> Optional[float]:
        """Get current gauge value"""
        with self._lock:
            gauge_key = f"{component}.{name}"
            return self._gauges.get(gauge_key)
    
    def get_metric_summary(self, 
                          name: str, 
                          component: str = "unknown",
                          time_window_minutes: int = 60) -> Optional[MetricSummary]:
        """
        Get summary statistics for a metric within a time window
        
        Args:
            name: Metric name
            component: Component name
            time_window_minutes: Time window in minutes
            
        Returns:
            MetricSummary or None if no data
        """
        with self._lock:
            metric_key = f"{component}.{name}"
            if metric_key not in self._metrics:
                return None
            
            # Filter points within time window
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            recent_points = [
                point for point in self._metrics[metric_key]
                if point.timestamp >= cutoff_time
            ]
            
            if not recent_points:
                return None
            
            values = [point.value for point in recent_points]
            
            # Calculate statistics
            try:
                return MetricSummary(
                    name=name,
                    count=len(values),
                    min_value=min(values),
                    max_value=max(values),
                    mean=statistics.mean(values),
                    median=statistics.median(values),
                    std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
                    percentile_95=self._percentile(values, 0.95),
                    percentile_99=self._percentile(values, 0.99),
                    unit=recent_points[0].unit,
                    component=component,
                    time_window=f"{time_window_minutes}m"
                )
            except Exception as e:
                logger.error(f"Error calculating metric summary: {e}")
                return None
    
    def get_all_metrics_summary(self, time_window_minutes: int = 60) -> Dict[str, MetricSummary]:
        """
        Get summary for all metrics
        
        Args:
            time_window_minutes: Time window in minutes
            
        Returns:
            Dictionary of metric summaries
        """
        summaries = {}
        
        with self._lock:
            for metric_key in self._metrics.keys():
                component, name = metric_key.split('.', 1)
                summary = self.get_metric_summary(name, component, time_window_minutes)
                if summary:
                    summaries[metric_key] = summary
        
        return summaries
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system-level metrics and statistics
        
        Returns:
            Dictionary containing system metrics
        """
        with self._lock:
            uptime = datetime.now() - self._start_time
            
            return {
                "uptime_seconds": uptime.total_seconds(),
                "total_metrics": len(self._metrics),
                "total_counters": len(self._counters),
                "total_gauges": len(self._gauges),
                "total_data_points": sum(len(points) for points in self._metrics.values()),
                "memory_usage": {
                    "metrics_count": len(self._metrics),
                    "avg_points_per_metric": sum(len(points) for points in self._metrics.values()) / max(len(self._metrics), 1)
                },
                "counters": dict(self._counters),
                "gauges": dict(self._gauges)
            }
    
    def export_metrics(self, format_type: str = "json") -> str:
        """
        Export all metrics in specified format
        
        Args:
            format_type: Export format ("json", "prometheus")
            
        Returns:
            Formatted metrics string
        """
        if format_type.lower() == "json":
            return self._export_json()
        elif format_type.lower() == "prometheus":
            return self._export_prometheus()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_json(self) -> str:
        """Export metrics as JSON"""
        with self._lock:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "system_metrics": self.get_system_metrics(),
                "metric_summaries": {
                    key: summary.to_dict() 
                    for key, summary in self.get_all_metrics_summary().items()
                },
                "recent_points": {}
            }
            
            # Include recent points for each metric
            for metric_key, points in self._metrics.items():
                recent_points = list(points)[-10:]  # Last 10 points
                export_data["recent_points"][metric_key] = [
                    point.to_dict() for point in recent_points
                ]
            
            return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        timestamp = int(time.time() * 1000)  # Prometheus uses milliseconds
        
        with self._lock:
            # Export counters
            for counter_key, value in self._counters.items():
                component, name = counter_key.split('.', 1)
                metric_name = f"bluesky_agent_{name.replace('.', '_').replace('-', '_')}"
                lines.append(f'# TYPE {metric_name} counter')
                lines.append(f'{metric_name}{{component="{component}"}} {value} {timestamp}')
            
            # Export gauges
            for gauge_key, value in self._gauges.items():
                component, name = gauge_key.split('.', 1)
                metric_name = f"bluesky_agent_{name.replace('.', '_').replace('-', '_')}"
                lines.append(f'# TYPE {metric_name} gauge')
                lines.append(f'{metric_name}{{component="{component}"}} {value} {timestamp}')
        
        return '\n'.join(lines)
    
    def _cleanup_old_metrics(self, metric_key: str) -> None:
        """Remove old metric points beyond retention period"""
        if metric_key not in self._metrics:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        points = self._metrics[metric_key]
        
        # Remove old points from the left
        while points and points[0].timestamp < cutoff_time:
            points.popleft()
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(percentile * (len(sorted_values) - 1))
        return sorted_values[index]
    
    @contextmanager
    def timer(self, name: str, component: str = "unknown", tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing operations
        
        Usage:
            with metrics_collector.timer("api_call", "news_service"):
                # timed operation
                pass
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_metric(
                name=f"{name}_duration",
                value=duration,
                unit="seconds",
                component=component,
                tags=tags or {}
            )


# Global metrics collector instance
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector


def initialize_metrics_collector(max_points_per_metric: int = 1000, retention_hours: int = 24) -> MetricsCollector:
    """
    Initialize the global metrics collector
    
    Args:
        max_points_per_metric: Maximum points per metric
        retention_hours: Data retention period
        
    Returns:
        Initialized MetricsCollector instance
    """
    global _global_metrics_collector
    _global_metrics_collector = MetricsCollector(max_points_per_metric, retention_hours)
    logger.info("Global metrics collector initialized")
    return _global_metrics_collector


# Convenience functions
def record_metric(name: str, value: float, unit: str = "count", component: str = "unknown", tags: Optional[Dict[str, str]] = None) -> None:
    """Record a metric using the global collector"""
    get_metrics_collector().record_metric(name, value, unit, component, tags)


def increment_counter(name: str, component: str = "unknown", increment: int = 1) -> None:
    """Increment a counter using the global collector"""
    get_metrics_collector().increment_counter(name, component, increment)


def set_gauge(name: str, value: float, component: str = "unknown", unit: str = "value") -> None:
    """Set a gauge using the global collector"""
    get_metrics_collector().set_gauge(name, value, component, unit)


def timer(name: str, component: str = "unknown", tags: Optional[Dict[str, str]] = None):
    """Timer context manager using the global collector"""
    return get_metrics_collector().timer(name, component, tags)