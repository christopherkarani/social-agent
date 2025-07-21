# tests/test_log_analyzer.py
"""
Unit tests for log analyzer functionality
"""
import unittest
import tempfile
import json
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

from src.utils.log_analyzer import (
    LogParser, LogAnalyzer, LogEntry, LogLevel, LogAnalysisReport,
    get_log_analyzer, initialize_log_analyzer
)


class TestLogParser(unittest.TestCase):
    """Test cases for LogParser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = LogParser()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_structured_log_line(self):
        """Test parsing structured JSON log line"""
        log_line = json.dumps({
            "timestamp": "2024-01-01T12:00:00",
            "level": "INFO",
            "logger": "test_logger",
            "message": "Test message",
            "module": "test_module",
            "function": "test_function",
            "line": 42,
            "thread_name": "MainThread",
            "process": 12345,
            "extra": {"key": "value"}
        })
        
        entry = self.parser._parse_log_line(log_line)
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.logger, "test_logger")
        self.assertEqual(entry.message, "Test message")
        self.assertEqual(entry.module, "test_module")
        self.assertEqual(entry.function, "test_function")
        self.assertEqual(entry.line, 42)
        self.assertEqual(entry.extra["key"], "value")
    
    def test_parse_standard_log_line(self):
        """Test parsing standard format log line"""
        log_line = "2024-01-01 12:00:00,123 - INFO - test_logger - Test message"
        
        entry = self.parser._parse_log_line(log_line)
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.logger, "test_logger")
        self.assertEqual(entry.message, "Test message")
    
    def test_parse_log_file(self):
        """Test parsing a complete log file"""
        log_file = self.temp_dir / "test.log"
        
        # Create test log content
        log_content = [
            json.dumps({
                "timestamp": "2024-01-01T12:00:00",
                "level": "INFO",
                "logger": "test_logger",
                "message": "First message",
                "module": "test_module",
                "function": "test_function",
                "line": 10,
                "thread_name": "MainThread",
                "process": 12345
            }),
            json.dumps({
                "timestamp": "2024-01-01T12:01:00",
                "level": "ERROR",
                "logger": "test_logger",
                "message": "Error message",
                "module": "test_module",
                "function": "test_function",
                "line": 20,
                "thread_name": "MainThread",
                "process": 12345
            })
        ]
        
        with open(log_file, 'w') as f:
            f.write('\n'.join(log_content))
        
        # Parse the file
        entries = list(self.parser.parse_log_file(log_file))
        
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].message, "First message")
        self.assertEqual(entries[1].message, "Error message")
        self.assertEqual(entries[1].level, LogLevel.ERROR)
    
    def test_parse_compressed_log_file(self):
        """Test parsing compressed log file"""
        log_file = self.temp_dir / "test.log.gz"
        
        log_content = json.dumps({
            "timestamp": "2024-01-01T12:00:00",
            "level": "INFO",
            "logger": "test_logger",
            "message": "Compressed message",
            "module": "test_module",
            "function": "test_function",
            "line": 10,
            "thread_name": "MainThread",
            "process": 12345
        })
        
        # Write compressed content
        with gzip.open(log_file, 'wt') as f:
            f.write(log_content)
        
        # Parse the compressed file
        entries = list(self.parser.parse_log_file(log_file))
        
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].message, "Compressed message")


class TestLogAnalyzer(unittest.TestCase):
    """Test cases for LogAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.analyzer = LogAnalyzer(str(self.temp_dir))
        
        # Create test log files
        self._create_test_logs()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_logs(self):
        """Create test log files"""
        log_file = self.temp_dir / "test.log"
        
        # Create log entries with different levels and timestamps
        now = datetime.now()
        log_entries = [
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "level": "INFO",
                "logger": "test_component",
                "message": "Normal operation",
                "module": "test_module",
                "function": "test_function",
                "line": 10,
                "thread_name": "MainThread",
                "process": 12345
            },
            {
                "timestamp": (now - timedelta(minutes=30)).isoformat(),
                "level": "ERROR",
                "logger": "test_component",
                "message": "API connection failed",
                "module": "test_module",
                "function": "api_call",
                "line": 25,
                "thread_name": "MainThread",
                "process": 12345
            },
            {
                "timestamp": (now - timedelta(minutes=15)).isoformat(),
                "level": "WARNING",
                "logger": "another_component",
                "message": "Rate limit approaching",
                "module": "rate_limiter",
                "function": "check_limit",
                "line": 50,
                "thread_name": "MainThread",
                "process": 12345
            },
            {
                "timestamp": now.isoformat(),
                "level": "INFO",
                "logger": "test_component",
                "message": "Operation completed",
                "module": "test_module",
                "function": "complete_task",
                "line": 100,
                "thread_name": "MainThread",
                "process": 12345,
                "extra": {
                    "execution_time": 2.5,
                    "duration": 1.8
                }
            }
        ]
        
        with open(log_file, 'w') as f:
            for entry in log_entries:
                f.write(json.dumps(entry) + '\n')
    
    def test_analyze_logs(self):
        """Test comprehensive log analysis"""
        report = self.analyzer.analyze_logs(hours_back=2)
        
        self.assertIsInstance(report, LogAnalysisReport)
        self.assertEqual(report.total_entries, 4)
        self.assertIn("INFO", report.level_distribution)
        self.assertIn("ERROR", report.level_distribution)
        self.assertEqual(report.level_distribution["INFO"], 2)
        self.assertEqual(report.level_distribution["ERROR"], 1)
        
        # Check top loggers
        self.assertTrue(len(report.top_loggers) > 0)
        self.assertEqual(report.top_loggers[0][0], "test_component")  # Most frequent logger
        
        # Check recommendations
        self.assertIsInstance(report.recommendations, list)
    
    def test_get_error_summary(self):
        """Test error summary generation"""
        summary = self.analyzer.get_error_summary(hours_back=2)
        
        self.assertEqual(summary["total_errors"], 1)
        self.assertGreater(summary["error_rate"], 0)
        self.assertEqual(len(summary["top_errors"]), 1)
        self.assertEqual(summary["top_errors"][0][0], "API connection failed")
    
    def test_get_performance_summary(self):
        """Test performance summary generation"""
        summary = self.analyzer.get_performance_summary(hours_back=2)
        
        self.assertIn("total_metrics", summary)
        self.assertIn("metric_statistics", summary)
        
        # Should find execution_time and duration metrics
        if "metric_statistics" in summary:
            self.assertGreater(summary["total_metrics"], 0)
    
    def test_search_logs(self):
        """Test log search functionality"""
        # Search for error messages
        results = self.analyzer.search_logs("API.*failed", hours_back=2)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].message, "API connection failed")
        self.assertEqual(results[0].level, LogLevel.ERROR)
    
    def test_search_logs_case_insensitive(self):
        """Test case-insensitive log search"""
        results = self.analyzer.search_logs("api connection", hours_back=2, case_sensitive=False)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].message, "API connection failed")
    
    def test_analyze_empty_logs(self):
        """Test analysis with no log entries"""
        # Create empty log directory
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()
        
        empty_analyzer = LogAnalyzer(str(empty_dir))
        report = empty_analyzer.analyze_logs(hours_back=1)
        
        self.assertEqual(report.total_entries, 0)
        self.assertEqual(len(report.anomalies), 1)
        self.assertEqual(report.anomalies[0]["type"], "no_logs_found")


class TestLogAnalyzerGlobalFunctions(unittest.TestCase):
    """Test cases for global log analyzer functions"""
    
    def test_get_log_analyzer(self):
        """Test getting global log analyzer instance"""
        analyzer1 = get_log_analyzer()
        analyzer2 = get_log_analyzer()
        
        # Should return the same instance
        self.assertIs(analyzer1, analyzer2)
        self.assertIsInstance(analyzer1, LogAnalyzer)
    
    def test_initialize_log_analyzer(self):
        """Test initializing global log analyzer"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            analyzer = initialize_log_analyzer(temp_dir)
            
            self.assertIsInstance(analyzer, LogAnalyzer)
            self.assertEqual(str(analyzer.log_directory), temp_dir)
            
            # Should be the same as global instance
            global_analyzer = get_log_analyzer()
            self.assertIs(analyzer, global_analyzer)
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestLogEntry(unittest.TestCase):
    """Test cases for LogEntry data class"""
    
    def test_log_entry_creation(self):
        """Test LogEntry creation and serialization"""
        timestamp = datetime.now()
        
        entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.INFO,
            logger="test_logger",
            message="Test message",
            module="test_module",
            function="test_function",
            line=42,
            thread="MainThread",
            process=12345,
            extra={"key": "value"}
        )
        
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.message, "Test message")
        self.assertEqual(entry.extra["key"], "value")
        
        # Test serialization
        entry_dict = entry.to_dict()
        self.assertEqual(entry_dict["level"], "INFO")
        self.assertEqual(entry_dict["message"], "Test message")
        self.assertEqual(entry_dict["timestamp"], timestamp.isoformat())


if __name__ == '__main__':
    unittest.main()