# src/utils/logging_config.py
"""
Comprehensive logging configuration for the Bluesky Crypto Agent
Provides structured logging, performance metrics, and monitoring capabilities
"""
import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import traceback


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs
    """
    
    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log structure
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra_fields:
            # Add any extra fields from the log record
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    try:
                        # Only include JSON-serializable values
                        json.dumps(value)
                        extra_fields[key] = value
                    except (TypeError, ValueError):
                        extra_fields[key] = str(value)
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, ensure_ascii=False)


class LoggingConfig:
    """
    Centralized logging configuration for the Bluesky Crypto Agent
    """
    
    DEFAULT_LOG_LEVEL = logging.INFO
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_LOG_FILE = "bluesky_crypto_agent.log"
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    DEFAULT_BACKUP_COUNT = 5
    
    @classmethod
    def setup_logging(cls, 
                     log_level: str = "INFO",
                     log_dir: str = DEFAULT_LOG_DIR,
                     log_file: str = DEFAULT_LOG_FILE,
                     enable_console: bool = True,
                     enable_file: bool = True,
                     enable_structured: bool = True,
                     max_bytes: int = DEFAULT_MAX_BYTES,
                     backup_count: int = DEFAULT_BACKUP_COUNT) -> None:
        """
        Setup comprehensive logging configuration
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            log_file: Name of the main log file
            enable_console: Enable console logging
            enable_file: Enable file logging
            enable_structured: Use structured JSON logging
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
        """
        
        # Convert string level to logging constant
        numeric_level = getattr(logging, log_level.upper(), cls.DEFAULT_LOG_LEVEL)
        
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set root logger level
        root_logger.setLevel(numeric_level)
        
        # Setup formatters
        if enable_structured:
            structured_formatter = StructuredFormatter()
            console_formatter = StructuredFormatter(include_extra_fields=False)
        else:
            # Standard formatters
            detailed_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
            )
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            )
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)
            console_handler.setFormatter(console_formatter if enable_structured else console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if enable_file:
            file_path = log_path / log_file
            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(file_path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(structured_formatter if enable_structured else detailed_formatter)
            root_logger.addHandler(file_handler)
        
        # Error file handler (separate file for errors)
        if enable_file:
            error_file_path = log_path / f"error_{log_file}"
            error_handler = logging.handlers.RotatingFileHandler(
                filename=str(error_file_path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(structured_formatter if enable_structured else detailed_formatter)
            root_logger.addHandler(error_handler)
        
        # Performance log handler (separate file for performance metrics)
        if enable_file:
            perf_file_path = log_path / f"performance_{log_file}"
            perf_handler = logging.handlers.RotatingFileHandler(
                filename=str(perf_file_path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            perf_handler.setLevel(logging.INFO)
            perf_handler.setFormatter(structured_formatter if enable_structured else detailed_formatter)
            
            # Create performance logger
            perf_logger = logging.getLogger('performance')
            perf_logger.addHandler(perf_handler)
            perf_logger.setLevel(logging.INFO)
            perf_logger.propagate = False  # Don't propagate to root logger
        
        logging.info("Logging configuration completed successfully")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)
    
    @classmethod
    def log_performance_metric(cls, 
                              metric_name: str, 
                              value: float, 
                              unit: str = "seconds",
                              component: str = "unknown",
                              additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a performance metric
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            component: Component that generated the metric
            additional_data: Additional metadata
        """
        perf_logger = logging.getLogger('performance')
        
        metric_data = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "component": component,
            "timestamp": datetime.now().isoformat()
        }
        
        if additional_data:
            metric_data.update(additional_data)
        
        perf_logger.info("Performance metric recorded", extra=metric_data)
    
    @classmethod
    def log_workflow_event(cls,
                          event_type: str,
                          event_data: Dict[str, Any],
                          component: str = "workflow") -> None:
        """
        Log a workflow event with structured data
        
        Args:
            event_type: Type of event (start, complete, error, etc.)
            event_data: Event-specific data
            component: Component that generated the event
        """
        logger = logging.getLogger(component)
        
        event_log = {
            "event_type": event_type,
            "component": component,
            "timestamp": datetime.now().isoformat(),
            **event_data
        }
        
        if event_type == "error":
            logger.error(f"Workflow event: {event_type}", extra=event_log)
        elif event_type in ["start", "complete"]:
            logger.info(f"Workflow event: {event_type}", extra=event_log)
        else:
            logger.debug(f"Workflow event: {event_type}", extra=event_log)


# Convenience function for easy setup
def setup_logging(config_dict: Optional[Dict[str, Any]] = None) -> None:
    """
    Setup logging with optional configuration dictionary
    
    Args:
        config_dict: Optional configuration dictionary
    """
    if config_dict is None:
        config_dict = {}
    
    # Default configuration
    default_config = {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_dir": os.getenv("LOG_DIR", "logs"),
        "enable_structured": os.getenv("STRUCTURED_LOGGING", "true").lower() == "true",
        "enable_console": os.getenv("CONSOLE_LOGGING", "true").lower() == "true",
        "enable_file": os.getenv("FILE_LOGGING", "true").lower() == "true"
    }
    
    # Merge with provided config
    final_config = {**default_config, **config_dict}
    
    LoggingConfig.setup_logging(**final_config)


# Performance monitoring decorator
def log_performance(metric_name: str = None, component: str = None):
    """
    Decorator to automatically log performance metrics for functions
    
    Args:
        metric_name: Custom metric name (defaults to function name)
        component: Component name (defaults to module name)
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = metric_name or func.__name__
            component_name = component or func.__module__
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                LoggingConfig.log_performance_metric(
                    metric_name=f"{function_name}_execution_time",
                    value=execution_time,
                    unit="seconds",
                    component=component_name,
                    additional_data={
                        "function": func.__name__,
                        "success": True
                    }
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                LoggingConfig.log_performance_metric(
                    metric_name=f"{function_name}_execution_time",
                    value=execution_time,
                    unit="seconds",
                    component=component_name,
                    additional_data={
                        "function": func.__name__,
                        "success": False,
                        "error": str(e)
                    }
                )
                
                raise
        
        return wrapper
    return decorator