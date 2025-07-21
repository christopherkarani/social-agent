# src/services/scheduler_service.py
"""
Scheduling service for automated Bluesky crypto agent execution
"""
import schedule
import time
import logging
import asyncio
import signal
import threading
from typing import Callable, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from ..utils.logging_config import log_performance
from ..utils.metrics_collector import get_metrics_collector, timer
from ..utils.alert_system import get_alert_manager, AlertSeverity

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Handles scheduling and automated execution of the Bluesky crypto agent
    with configurable intervals, timeout handling, and graceful shutdown
    """
    
    def __init__(self, agent_workflow: Callable, interval_minutes: int = 30, 
                 max_execution_time_minutes: int = 25):
        """
        Initialize the scheduler service
        
        Args:
            agent_workflow: The async workflow function to execute
            interval_minutes: How often to run the workflow (default: 30)
            max_execution_time_minutes: Maximum execution time before timeout (default: 25)
        """
        self.agent_workflow = agent_workflow
        self.interval_minutes = interval_minutes
        self.max_execution_time_minutes = max_execution_time_minutes
        self.is_running = False
        self.current_execution_thread = None
        self.execution_count = 0
        self.last_execution_time = None
        self.last_execution_success = None
        self.shutdown_event = threading.Event()
        
        # Monitoring and metrics
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
        self.start_time = datetime.now()
        
        # Execution statistics
        self.success_count = 0
        self.failure_count = 0
        self.timeout_count = 0
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info("SchedulerService initialized", extra={
            "interval_minutes": interval_minutes,
            "max_execution_time_minutes": max_execution_time_minutes
        })
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.stop()
            
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
    def start(self):
        """Start the scheduler with configurable interval support"""
        logger.info(f"Starting scheduler with {self.interval_minutes} minute intervals", extra={
            "component": "scheduler_service",
            "action": "start",
            "interval_minutes": self.interval_minutes,
            "max_execution_time_minutes": self.max_execution_time_minutes
        })
        
        # Record scheduler start metrics
        self.metrics_collector.increment_counter("scheduler_starts", "scheduler_service")
        self.metrics_collector.set_gauge("scheduler_running", 1, "scheduler_service")
        self.metrics_collector.record_metric("configured_interval_minutes", self.interval_minutes, "minutes", "scheduler_service")
        
        # Clear any existing schedules
        schedule.clear()
        
        # Schedule the workflow with configurable interval
        schedule.every(self.interval_minutes).minutes.do(self._run_workflow_wrapper)
        
        self.is_running = True
        
        # Run the scheduler loop
        try:
            while self.is_running and not self.shutdown_event.is_set():
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down gracefully")
        finally:
            self._cleanup()
            
    def stop(self):
        """Stop the scheduler gracefully"""
        logger.info("Initiating graceful shutdown of scheduler")
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for current execution to complete if running
        if self.current_execution_thread and self.current_execution_thread.is_alive():
            logger.info("Waiting for current execution to complete...")
            self.current_execution_thread.join(timeout=30)  # Wait up to 30 seconds
            
        schedule.clear()
        logger.info("Scheduler stopped gracefully")
        
    def _cleanup(self):
        """Cleanup resources"""
        if self.current_execution_thread and self.current_execution_thread.is_alive():
            logger.warning("Forcefully terminating current execution thread")
            
    def get_status(self) -> dict:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "interval_minutes": self.interval_minutes,
            "max_execution_time_minutes": self.max_execution_time_minutes,
            "execution_count": self.execution_count,
            "last_execution_time": self.last_execution_time,
            "last_execution_success": self.last_execution_success,
            "next_run": schedule.next_run() if schedule.jobs else None
        }
        
    def _run_workflow_wrapper(self):
        """Wrapper to run workflow in a separate thread with timeout"""
        if self.current_execution_thread and self.current_execution_thread.is_alive():
            logger.warning("Previous execution still running, skipping this cycle")
            return
            
        self.current_execution_thread = threading.Thread(
            target=self._run_workflow,
            name=f"workflow-execution-{self.execution_count + 1}"
        )
        self.current_execution_thread.start()
        
    def _run_workflow(self):
        """Execute the agent workflow with comprehensive timeout and error handling"""
        start_time = datetime.now()
        self.execution_count += 1
        self.last_execution_time = start_time
        
        logger.info(f"Starting scheduled workflow execution #{self.execution_count} at {start_time}")
        
        try:
            # Use ThreadPoolExecutor for better timeout control
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._run_async_workflow)
                
                try:
                    # Wait for completion with timeout
                    future.result(timeout=self.max_execution_time_minutes * 60)
                    
                    execution_time = datetime.now() - start_time
                    logger.info(f"Workflow #{self.execution_count} completed successfully in {execution_time}")
                    self.last_execution_success = True
                    
                except FutureTimeoutError:
                    logger.error(f"Workflow #{self.execution_count} timed out after {self.max_execution_time_minutes} minutes")
                    self.last_execution_success = False
                    
                    # Cancel the future to clean up resources
                    future.cancel()
                    
        except Exception as e:
            logger.error(f"Workflow #{self.execution_count} execution failed: {e}", exc_info=True)
            self.last_execution_success = False
            
        finally:
            execution_time = datetime.now() - start_time
            logger.info(f"Workflow #{self.execution_count} finished after {execution_time}")
            
            # Continue with next scheduled run regardless of errors (requirement 4.5)
            if self.is_running:
                next_run = schedule.next_run()
                if next_run:
                    logger.info(f"Next execution scheduled for {next_run}")
                    
    def _run_async_workflow(self):
        """Run the async workflow in a new event loop"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the workflow
            loop.run_until_complete(self.agent_workflow())
            
        except Exception as e:
            logger.error(f"Error in async workflow execution: {e}", exc_info=True)
            raise
        finally:
            # Clean up the event loop
            try:
                loop.close()
            except Exception as e:
                logger.warning(f"Error closing event loop: {e}")
                
    def run_once(self):
        """Run the workflow once immediately (for testing/manual execution)"""
        logger.info("Running workflow once immediately")
        self._run_workflow()
        
    def update_schedule(self, new_interval_minutes: int):
        """Update the scheduling interval"""
        if new_interval_minutes <= 0:
            raise ValueError("Interval must be positive")
            
        logger.info(f"Updating schedule interval from {self.interval_minutes} to {new_interval_minutes} minutes")
        
        self.interval_minutes = new_interval_minutes
        
        # Clear and reschedule if running
        if self.is_running:
            schedule.clear()
            schedule.every(self.interval_minutes).minutes.do(self._run_workflow_wrapper)
            logger.info("Schedule updated successfully")