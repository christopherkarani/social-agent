# src/utils/log_analyzer.py
"""
Log aggregation and analysis system for the Bluesky Crypto Agent
Provides log parsing, analysis, and reporting capabilities
"""
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Iterator
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import gzip
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: LogLevel
    logger: str
    message: str
    module: str
    function: str
    line: int
    thread: str
    process: int
    extra: Dict[str, Any]
    exception: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        return data


@dataclass
class LogAnalysisReport:
    """Log analysis report"""
    time_period: str
    total_entries: int
    level_distribution: Dict[str, int]
    top_loggers: List[Tuple[str, int]]
    top_modules: List[Tuple[str, int]]
    error_patterns: List[Tuple[str, int]]
    performance_metrics: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class LogParser:
    """
    Parser for structured and unstructured log files
    """
    
    def __init__(self):
        # Regex patterns for different log formats
        self.structured_pattern = re.compile(r'^{.*}$')
        self.standard_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - '
            r'([A-Z]+) - '
            r'([^-]+) - '
            r'(.+)$'
        )
        
    def parse_log_file(self, file_path: Path) -> Iterator[LogEntry]:
        """
        Parse a log file and yield LogEntry objects
        
        Args:
            file_path: Path to log file
            
        Yields:
            LogEntry objects
        """
        try:
            # Handle compressed files
            if file_path.suffix == '.gz':
                file_opener = gzip.open
                mode = 'rt'
            else:
                file_opener = open
                mode = 'r'
            
            with file_opener(file_path, mode, encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = self._parse_log_line(line)
                        if entry:
                            yield entry
                    except Exception as e:
                        logger.debug(f"Failed to parse line {line_num} in {file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line"""
        
        # Try structured JSON format first
        if self.structured_pattern.match(line):
            return self._parse_structured_line(line)
        
        # Try standard format
        match = self.standard_pattern.match(line)
        if match:
            return self._parse_standard_line(match)
        
        # If no pattern matches, create a basic entry
        return LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            logger="unknown",
            message=line,
            module="unknown",
            function="unknown",
            line=0,
            thread="unknown",
            process=0,
            extra={}
        )
    
    def _parse_structured_line(self, line: str) -> Optional[LogEntry]:
        """Parse structured JSON log line"""
        try:
            data = json.loads(line)
            
            return LogEntry(
                timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
                level=LogLevel(data.get('level', 'INFO')),
                logger=data.get('logger', 'unknown'),
                message=data.get('message', ''),
                module=data.get('module', 'unknown'),
                function=data.get('function', 'unknown'),
                line=data.get('line', 0),
                thread=data.get('thread_name', 'unknown'),
                process=data.get('process', 0),
                extra=data.get('extra', {}),
                exception=data.get('exception')
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.debug(f"Failed to parse structured log line: {e}")
            return None
    
    def _parse_standard_line(self, match) -> LogEntry:
        """Parse standard format log line"""
        timestamp_str, level_str, logger_name, message = match.groups()
        
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
        except ValueError:
            timestamp = datetime.now()
        
        try:
            level = LogLevel(level_str)
        except ValueError:
            level = LogLevel.INFO
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            logger=logger_name.strip(),
            message=message.strip(),
            module="unknown",
            function="unknown",
            line=0,
            thread="unknown",
            process=0,
            extra={}
        )


class LogAnalyzer:
    """
    Comprehensive log analysis system
    """
    
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.parser = LogParser()
        
        # Error patterns to look for
        self.error_patterns = [
            r'failed to.*',
            r'error.*',
            r'exception.*',
            r'timeout.*',
            r'connection.*refused',
            r'authentication.*failed',
            r'rate.*limit',
            r'api.*error',
            r'network.*error'
        ]
        
        # Performance keywords
        self.performance_keywords = [
            'execution_time',
            'duration',
            'latency',
            'response_time',
            'processing_time'
        ]
    
    def analyze_logs(self, 
                    hours_back: int = 24,
                    log_files: Optional[List[str]] = None) -> LogAnalysisReport:
        """
        Analyze logs and generate comprehensive report
        
        Args:
            hours_back: How many hours back to analyze
            log_files: Specific log files to analyze (optional)
            
        Returns:
            LogAnalysisReport with analysis results
        """
        logger.info(f"Starting log analysis for last {hours_back} hours")
        
        # Collect log entries
        entries = list(self._collect_log_entries(hours_back, log_files))
        
        if not entries:
            logger.warning("No log entries found for analysis")
            return self._create_empty_report(hours_back)
        
        logger.info(f"Analyzing {len(entries)} log entries")
        
        # Perform analysis
        level_distribution = self._analyze_log_levels(entries)
        top_loggers = self._analyze_top_loggers(entries)
        top_modules = self._analyze_top_modules(entries)
        error_patterns = self._analyze_error_patterns(entries)
        performance_metrics = self._analyze_performance_metrics(entries)
        anomalies = self._detect_anomalies(entries)
        recommendations = self._generate_recommendations(entries, anomalies)
        
        return LogAnalysisReport(
            time_period=f"{hours_back} hours",
            total_entries=len(entries),
            level_distribution=level_distribution,
            top_loggers=top_loggers,
            top_modules=top_modules,
            error_patterns=error_patterns,
            performance_metrics=performance_metrics,
            anomalies=anomalies,
            recommendations=recommendations
        )
    
    def get_error_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Get summary of errors and exceptions
        
        Args:
            hours_back: Hours to look back
            
        Returns:
            Error summary dictionary
        """
        entries = list(self._collect_log_entries(hours_back))
        error_entries = [
            entry for entry in entries 
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]
        
        if not error_entries:
            return {
                "total_errors": 0,
                "error_rate": 0.0,
                "top_errors": [],
                "components_with_errors": []
            }
        
        # Count error messages
        error_messages = Counter(entry.message for entry in error_entries)
        
        # Count components with errors
        components_with_errors = Counter(entry.logger for entry in error_entries)
        
        return {
            "total_errors": len(error_entries),
            "error_rate": len(error_entries) / len(entries) if entries else 0,
            "top_errors": error_messages.most_common(10),
            "components_with_errors": components_with_errors.most_common(10),
            "recent_errors": [
                entry.to_dict() for entry in 
                sorted(error_entries, key=lambda x: x.timestamp, reverse=True)[:5]
            ]
        }
    
    def get_performance_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Get performance metrics summary
        
        Args:
            hours_back: Hours to look back
            
        Returns:
            Performance summary dictionary
        """
        entries = list(self._collect_log_entries(hours_back))
        
        # Extract performance metrics
        performance_entries = []
        for entry in entries:
            if entry.extra:
                for key, value in entry.extra.items():
                    if any(keyword in key.lower() for keyword in self.performance_keywords):
                        try:
                            numeric_value = float(value)
                            performance_entries.append({
                                "metric": key,
                                "value": numeric_value,
                                "timestamp": entry.timestamp,
                                "component": entry.logger
                            })
                        except (ValueError, TypeError):
                            continue
        
        if not performance_entries:
            return {"message": "No performance metrics found"}
        
        # Group by metric
        metrics_by_name = defaultdict(list)
        for entry in performance_entries:
            metrics_by_name[entry["metric"]].append(entry["value"])
        
        # Calculate statistics
        metric_stats = {}
        for metric_name, values in metrics_by_name.items():
            if values:
                metric_stats[metric_name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "recent_values": values[-10:]  # Last 10 values
                }
        
        return {
            "total_metrics": len(performance_entries),
            "unique_metrics": len(metrics_by_name),
            "metric_statistics": metric_stats,
            "recent_performance_entries": performance_entries[-10:]
        }
    
    def search_logs(self, 
                   query: str,
                   hours_back: int = 24,
                   case_sensitive: bool = False) -> List[LogEntry]:
        """
        Search logs for specific patterns
        
        Args:
            query: Search query (regex supported)
            hours_back: Hours to search back
            case_sensitive: Whether search is case sensitive
            
        Returns:
            List of matching log entries
        """
        entries = list(self._collect_log_entries(hours_back))
        
        # Compile regex pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error:
            # If regex fails, treat as literal string
            pattern = re.compile(re.escape(query), flags)
        
        # Search entries
        matching_entries = []
        for entry in entries:
            if (pattern.search(entry.message) or 
                pattern.search(entry.logger) or
                pattern.search(entry.module)):
                matching_entries.append(entry)
        
        return matching_entries
    
    def _collect_log_entries(self, 
                           hours_back: int,
                           log_files: Optional[List[str]] = None) -> Iterator[LogEntry]:
        """Collect log entries from files"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        if log_files:
            files_to_process = [self.log_directory / f for f in log_files]
        else:
            # Find all log files
            files_to_process = []
            if self.log_directory.exists():
                files_to_process.extend(self.log_directory.glob("*.log"))
                files_to_process.extend(self.log_directory.glob("*.log.*"))
        
        for file_path in files_to_process:
            if not file_path.exists():
                continue
                
            for entry in self.parser.parse_log_file(file_path):
                if entry.timestamp >= cutoff_time:
                    yield entry
    
    def _analyze_log_levels(self, entries: List[LogEntry]) -> Dict[str, int]:
        """Analyze distribution of log levels"""
        return dict(Counter(entry.level.value for entry in entries))
    
    def _analyze_top_loggers(self, entries: List[LogEntry]) -> List[Tuple[str, int]]:
        """Find top loggers by frequency"""
        return Counter(entry.logger for entry in entries).most_common(10)
    
    def _analyze_top_modules(self, entries: List[LogEntry]) -> List[Tuple[str, int]]:
        """Find top modules by frequency"""
        return Counter(entry.module for entry in entries).most_common(10)
    
    def _analyze_error_patterns(self, entries: List[LogEntry]) -> List[Tuple[str, int]]:
        """Analyze common error patterns"""
        error_entries = [
            entry for entry in entries 
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]
        
        pattern_counts = defaultdict(int)
        
        for entry in error_entries:
            message_lower = entry.message.lower()
            for pattern in self.error_patterns:
                if re.search(pattern, message_lower):
                    pattern_counts[pattern] += 1
        
        return sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
    
    def _analyze_performance_metrics(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Analyze performance metrics from logs"""
        performance_data = defaultdict(list)
        
        for entry in entries:
            if entry.extra:
                for key, value in entry.extra.items():
                    if any(keyword in key.lower() for keyword in self.performance_keywords):
                        try:
                            numeric_value = float(value)
                            performance_data[key].append(numeric_value)
                        except (ValueError, TypeError):
                            continue
        
        # Calculate statistics
        stats = {}
        for metric, values in performance_data.items():
            if values:
                stats[metric] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values)
                }
        
        return stats
    
    def _detect_anomalies(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Detect anomalies in log patterns"""
        anomalies = []
        
        # Check for error spikes
        error_entries = [
            entry for entry in entries 
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]
        
        if len(error_entries) > len(entries) * 0.1:  # More than 10% errors
            anomalies.append({
                "type": "high_error_rate",
                "description": f"High error rate detected: {len(error_entries)}/{len(entries)} ({len(error_entries)/len(entries)*100:.1f}%)",
                "severity": "high"
            })
        
        # Check for repeated errors
        error_messages = Counter(entry.message for entry in error_entries)
        for message, count in error_messages.most_common(5):
            if count > 10:  # Same error repeated more than 10 times
                anomalies.append({
                    "type": "repeated_error",
                    "description": f"Repeated error: '{message[:100]}...' occurred {count} times",
                    "severity": "medium"
                })
        
        # Check for missing expected log entries
        expected_loggers = ["bluesky_crypto_agent", "scheduler_service", "news_retrieval_tool"]
        active_loggers = set(entry.logger for entry in entries)
        
        for expected_logger in expected_loggers:
            if expected_logger not in active_loggers:
                anomalies.append({
                    "type": "missing_component_logs",
                    "description": f"No log entries found for expected component: {expected_logger}",
                    "severity": "medium"
                })
        
        return anomalies
    
    def _generate_recommendations(self, entries: List[LogEntry], anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Error rate recommendations
        error_rate = len([e for e in entries if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]]) / len(entries)
        if error_rate > 0.05:  # More than 5% errors
            recommendations.append(
                f"High error rate detected ({error_rate*100:.1f}%). "
                "Consider investigating root causes and implementing better error handling."
            )
        
        # Performance recommendations
        performance_entries = [e for e in entries if e.extra and 
                             any(keyword in str(e.extra).lower() for keyword in self.performance_keywords)]
        if len(performance_entries) < len(entries) * 0.1:  # Less than 10% have performance metrics
            recommendations.append(
                "Low performance metric coverage. Consider adding more performance logging "
                "to better monitor system performance."
            )
        
        # Logging level recommendations
        debug_entries = [e for e in entries if e.level == LogLevel.DEBUG]
        if len(debug_entries) > len(entries) * 0.5:  # More than 50% debug logs
            recommendations.append(
                "High volume of DEBUG logs detected. Consider adjusting log levels in production "
                "to reduce log volume and improve performance."
            )
        
        # Component coverage recommendations
        unique_loggers = len(set(entry.logger for entry in entries))
        if unique_loggers < 5:  # Fewer than 5 different components logging
            recommendations.append(
                "Limited component logging coverage. Ensure all major components are logging "
                "appropriately for better observability."
            )
        
        return recommendations
    
    def _create_empty_report(self, hours_back: int) -> LogAnalysisReport:
        """Create empty report when no logs found"""
        return LogAnalysisReport(
            time_period=f"{hours_back} hours",
            total_entries=0,
            level_distribution={},
            top_loggers=[],
            top_modules=[],
            error_patterns=[],
            performance_metrics={},
            anomalies=[{
                "type": "no_logs_found",
                "description": "No log entries found for the specified time period",
                "severity": "high"
            }],
            recommendations=[
                "No log entries found. Check if logging is properly configured and log files are accessible."
            ]
        )


# Global log analyzer instance
_global_log_analyzer: Optional[LogAnalyzer] = None


def get_log_analyzer() -> LogAnalyzer:
    """Get the global log analyzer instance"""
    global _global_log_analyzer
    if _global_log_analyzer is None:
        _global_log_analyzer = LogAnalyzer()
    return _global_log_analyzer


def initialize_log_analyzer(log_directory: str = "logs") -> LogAnalyzer:
    """
    Initialize the global log analyzer
    
    Args:
        log_directory: Directory containing log files
        
    Returns:
        Initialized LogAnalyzer instance
    """
    global _global_log_analyzer
    _global_log_analyzer = LogAnalyzer(log_directory)
    logger.info("Global log analyzer initialized")
    return _global_log_analyzer