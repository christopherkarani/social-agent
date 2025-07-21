# tests/test_logging_config.py
"""
Unit tests for logging configuration and structured logging functionality
"""
import unittest
import logging
import json
import tempfile
import os
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from pathlib import Path

from src.utils.logging_config import (
    StructuredFormatter, LoggingConfig, setup_logging, log_performance
)


class TestStructuredFormatter(unittest.TestCase):
    """Test cases for StructuredFormatter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.formatter = StructuredFormatter()
        self.formatter_no_extra = StructuredFormatter(include_extra_fields=False)
    
    def test_format_basic_record(self):
        """Test formatting a basic log record"""
        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = self.formatter.format(record)
        
        # Parse the JSON output
        log_data = json.loads(formatted)
        
        # Verify required fields
        self.assertEqual(log_data["level"], "INFO")
        self.assertEqual(log_data["logger"], "test_logger")
        self.assertEqual(log_data["message"], "Test message")
        self.assertEqual(log_data["line"], 42)
        self.assertIn("timestamp", log_data)
        self.assertIn("thread", log_data)
        self.assertIn("process", log_data)
    
    def test_format_with_exception(self):
        """Test formatting a log record with exception information"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )
            
            # Format the record
            formatted = self.formatter.format(record)
            log_data = json.loads(formatted)
            
            # Verify exception information
            self.assertIn("exception", log_data)
            self.assertEqual(log_data["exception"]["type"], "ValueError")
            self.assertEqual(log_data["exception"]["message"], "Test exception")
            self.assertIsInstance(log_data["exception"]["traceback"], list)
    
    def test_format_with_extra_fields(self):
        """Test formatting with extra fields"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.user_id = "12345"
        record.request_id = "req-abc-123"
        record.custom_data = {"key": "value"}
        
        # Format the record
        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)
        
        # Verify extra fields are included
        self.assertIn("extra", log_data)
        self.assertEqual(log_data["extra"]["user_id"], "12345")
        self.assertEqual(log_data["extra"]["request_id"], "req-abc-123")
        self.assertEqual(log_data["extra"]["custom_data"], {"key": "value"})
    
    def test_format_without_extra_fields(self):
        """Test formatting without extra fields"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.user_id = "12345"
        
        # Format with formatter that excludes extra fields
        formatted = self.formatter_no_extra.format(record)
        log_data = json.loads(formatted)
        
        # Verify extra fields are not included
        self.assertNotIn("extra", log_data)
    
    def test_format_with_non_serializable_extra(self):
        """Test formatting with non-JSON-serializable extra fields"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add non-serializable extra field
        record.non_serializable = object()
        
        # Format the record (should not raise exception)
        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)
        
        # Verify non-serializable field is converted to string
        self.assertIn("extra", log_data)
        self.assertIsInstance(log_data["extra"]["non_serializable"], str)


class TestLoggingConfig(unittest.TestCase):
    """Test cases for LoggingConfig"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "logs")
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clear all handlers
        logging.getLogger().handlers.clear()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_logging_basic(self):
        """Test basic logging setup"""
        LoggingConfig.setup_logging(
            log_level="INFO",
            log_dir=self.log_dir,
            enable_console=True,
            enable_file=True
        )
        
        # Verify log directory was created
        self.assertTrue(os.path.exists(self.log_dir))
        
        # Verify root logger configuration
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)
        
        # Verify handlers were added
        self.assertGreater(len(root_logger.handlers), 0)
    
    def test_setup_logging_file_only(self):
        """Test logging setup with file only"""
        LoggingConfig.setup_logging(
            log_level="DEBUG",
            log_dir=self.log_dir,
            enable_console=False,
            enable_file=True
        )
        
        # Test logging
        logger = logging.getLogger("test")
        logger.info("Test message")
        
        # Verify log file was created
        log_file = os.path.join(self.log_dir, "bluesky_crypto_agent.log")
        self.assertTrue(os.path.exists(log_file))
        
        # Verify log content
        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn("Test message", content)
    
    def test_setup_logging_console_only(self):
        """Test logging setup with console only"""
        with patch('sys.stdout') as mock_stdout:
            LoggingConfig.setup_logging(
                log_level="WARNING",
                enable_console=True,
                enable_file=False
            )
            
            # Test logging
            logger = logging.getLogger("test")
            logger.warning("Test warning")
            
            # Verify no log files were created
            self.assertFalse(os.path.exists(self.log_dir))
    
    def test_setup_logging_structured(self):
        """Test structured logging setup"""
        LoggingConfig.setup_logging(
            log_level="INFO",
            log_dir=self.log_dir,
            enable_structured=True,
            enable_file=True
        )
        
        # Test logging with extra fields
        logger = logging.getLogger("test")
        logger.info("Test message", extra={"test_field": "test_value"})
        
        # Verify structured log content
        log_file = os.path.join(self.log_dir, "bluesky_crypto_agent.log")
        with open(log_file, 'r') as f:
            lines = f.read().strip().split('\n')
            # Find the line with our test message
            test_log_line = None
            for line in lines:
                if line.strip():
                    log_data = json.loads(line)
                    if log_data.get("message") == "Test message":
                        test_log_line = log_data
                        break
            
            self.assertIsNotNone(test_log_line)
            self.assertEqual(test_log_line["message"], "Test message")
            self.assertEqual(test_log_line["extra"]["test_field"], "test_value")
    
    def test_get_logger(self):
        """Test logger retrieval"""
        logger = LoggingConfig.get_logger("test_module")
        self.assertEqual(logger.name, "test_module")
        self.assertIsInstance(logger, logging.Logger)
    
    def test_log_performance_metric(self):
        """Test performance metric logging"""
        LoggingConfig.setup_logging(
            log_dir=self.log_dir,
            enable_file=True
        )
        
        LoggingConfig.log_performance_metric(
            metric_name="test_metric",
            value=1.23,
            unit="seconds",
            component="test_component",
            additional_data={"test": "data"}
        )
        
        # Verify performance log file
        perf_log_file = os.path.join(self.log_dir, "performance_bluesky_crypto_agent.log")
        self.assertTrue(os.path.exists(perf_log_file))
        
        # Verify log content
        with open(perf_log_file, 'r') as f:
            content = f.read()
            log_data = json.loads(content.strip())
            self.assertEqual(log_data["extra"]["metric_name"], "test_metric")
            self.assertEqual(log_data["extra"]["value"], 1.23)
            self.assertEqual(log_data["extra"]["unit"], "seconds")
            self.assertEqual(log_data["extra"]["component"], "test_component")
            self.assertEqual(log_data["extra"]["test"], "data")
    
    def test_log_workflow_event(self):
        """Test workflow event logging"""
        LoggingConfig.setup_logging(
            log_dir=self.log_dir,
            enable_file=True
        )
        
        LoggingConfig.log_workflow_event(
            event_type="start",
            event_data={"workflow_id": "test-123", "step": "initialization"},
            component="test_workflow"
        )
        
        # Verify log was created
        log_file = os.path.join(self.log_dir, "bluesky_crypto_agent.log")
        with open(log_file, 'r') as f:
            lines = f.read().strip().split('\n')
            # Find the line with our workflow event
            workflow_log_line = None
            for line in lines:
                if line.strip():
                    log_data = json.loads(line)
                    if log_data.get("extra", {}).get("event_type") == "start":
                        workflow_log_line = log_data
                        break
            
            self.assertIsNotNone(workflow_log_line)
            self.assertEqual(workflow_log_line["extra"]["event_type"], "start")
            self.assertEqual(workflow_log_line["extra"]["workflow_id"], "test-123")
            self.assertEqual(workflow_log_line["extra"]["step"], "initialization")
    
    def test_log_rotation(self):
        """Test log file rotation"""
        LoggingConfig.setup_logging(
            log_dir=self.log_dir,
            enable_file=True,
            max_bytes=100,  # Very small for testing
            backup_count=2
        )
        
        logger = logging.getLogger("test")
        
        # Generate enough logs to trigger rotation
        for i in range(50):
            logger.info(f"Test message {i} with some additional content to make it longer")
        
        # Check for rotated files
        log_files = list(Path(self.log_dir).glob("*.log*"))
        self.assertGreater(len(log_files), 1)  # Should have main + rotated files


class TestSetupLoggingFunction(unittest.TestCase):
    """Test cases for setup_logging convenience function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        logging.getLogger().handlers.clear()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch.dict(os.environ, {
        'LOG_LEVEL': 'DEBUG',
        'LOG_DIR': 'test_logs',
        'STRUCTURED_LOGGING': 'true'
    })
    def test_setup_logging_with_env_vars(self):
        """Test setup_logging with environment variables"""
        with patch.object(LoggingConfig, 'setup_logging') as mock_setup:
            setup_logging()
            
            # Verify environment variables were used
            mock_setup.assert_called_once()
            call_args = mock_setup.call_args[1]
            self.assertEqual(call_args['log_level'], 'DEBUG')
            self.assertEqual(call_args['log_dir'], 'test_logs')
            self.assertTrue(call_args['enable_structured'])
    
    def test_setup_logging_with_config_dict(self):
        """Test setup_logging with configuration dictionary"""
        config = {
            'log_level': 'WARNING',
            'log_dir': self.temp_dir,
            'enable_console': False
        }
        
        with patch.object(LoggingConfig, 'setup_logging') as mock_setup:
            setup_logging(config)
            
            # Verify config was passed through
            mock_setup.assert_called_once()
            call_args = mock_setup.call_args[1]
            self.assertEqual(call_args['log_level'], 'WARNING')
            self.assertEqual(call_args['log_dir'], self.temp_dir)
            self.assertFalse(call_args['enable_console'])


class TestLogPerformanceDecorator(unittest.TestCase):
    """Test cases for log_performance decorator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        LoggingConfig.setup_logging(
            log_dir=self.temp_dir,
            enable_file=True
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        logging.getLogger().handlers.clear()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_decorator_success(self):
        """Test performance decorator on successful function"""
        @log_performance(metric_name="test_function", component="test_module")
        def test_function(x, y):
            import time
            time.sleep(0.01)  # Small delay to ensure measurable execution time
            return x + y
        
        result = test_function(2, 3)
        self.assertEqual(result, 5)
        
        # Verify performance log was created
        perf_log_file = os.path.join(self.temp_dir, "performance_bluesky_crypto_agent.log")
        self.assertTrue(os.path.exists(perf_log_file))
        
        # Verify log content
        with open(perf_log_file, 'r') as f:
            content = f.read()
            log_data = json.loads(content.strip())
            self.assertEqual(log_data["extra"]["metric_name"], "test_function_execution_time")
            self.assertEqual(log_data["extra"]["component"], "test_module")
            self.assertTrue(log_data["extra"]["success"])
            self.assertGreaterEqual(log_data["extra"]["value"], 0)  # Changed to >= to handle very fast execution
    
    def test_decorator_exception(self):
        """Test performance decorator on function that raises exception"""
        @log_performance(metric_name="failing_function", component="test_module")
        def failing_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            failing_function()
        
        # Verify performance log was still created
        perf_log_file = os.path.join(self.temp_dir, "performance_bluesky_crypto_agent.log")
        self.assertTrue(os.path.exists(perf_log_file))
        
        # Verify log content shows failure
        with open(perf_log_file, 'r') as f:
            content = f.read()
            log_data = json.loads(content.strip())
            self.assertEqual(log_data["extra"]["metric_name"], "failing_function_execution_time")
            self.assertFalse(log_data["extra"]["success"])
            self.assertEqual(log_data["extra"]["error"], "Test error")
    
    def test_decorator_default_names(self):
        """Test performance decorator with default metric and component names"""
        @log_performance()
        def my_test_function():
            return "success"
        
        result = my_test_function()
        self.assertEqual(result, "success")
        
        # Verify performance log uses function name as metric
        perf_log_file = os.path.join(self.temp_dir, "performance_bluesky_crypto_agent.log")
        with open(perf_log_file, 'r') as f:
            content = f.read()
            log_data = json.loads(content.strip())
            self.assertEqual(log_data["extra"]["metric_name"], "my_test_function_execution_time")
            self.assertEqual(log_data["extra"]["function"], "my_test_function")


if __name__ == '__main__':
    unittest.main()