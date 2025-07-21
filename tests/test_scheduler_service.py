# tests/test_scheduler_service.py
"""
Unit tests for SchedulerService
"""
import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.scheduler_service import SchedulerService


class TestSchedulerService:
    """Test cases for SchedulerService"""
    
    @pytest.fixture
    def mock_workflow(self):
        """Mock async workflow function"""
        async def mock_async_workflow():
            await asyncio.sleep(0.1)  # Simulate some work
            return "success"
        return mock_async_workflow
    
    @pytest.fixture
    def scheduler(self, mock_workflow):
        """Create scheduler instance for testing"""
        return SchedulerService(
            agent_workflow=mock_workflow,
            interval_minutes=1,  # Short interval for testing
            max_execution_time_minutes=1
        )
    
    def test_scheduler_initialization(self, mock_workflow):
        """Test scheduler initialization with default and custom parameters"""
        # Test default parameters
        scheduler = SchedulerService(mock_workflow)
        assert scheduler.interval_minutes == 30
        assert scheduler.max_execution_time_minutes == 25
        assert scheduler.is_running is False
        assert scheduler.execution_count == 0
        
        # Test custom parameters
        scheduler = SchedulerService(mock_workflow, interval_minutes=15, max_execution_time_minutes=20)
        assert scheduler.interval_minutes == 15
        assert scheduler.max_execution_time_minutes == 20
    
    def test_get_status(self, scheduler):
        """Test status reporting functionality"""
        status = scheduler.get_status()
        
        expected_keys = [
            "is_running", "interval_minutes", "max_execution_time_minutes",
            "execution_count", "last_execution_time", "last_execution_success", "next_run"
        ]
        
        for key in expected_keys:
            assert key in status
            
        assert status["is_running"] is False
        assert status["interval_minutes"] == 1
        assert status["execution_count"] == 0
    
    def test_update_schedule(self, scheduler):
        """Test schedule interval updates"""
        # Test valid update
        scheduler.update_schedule(45)
        assert scheduler.interval_minutes == 45
        
        # Test invalid update
        with pytest.raises(ValueError, match="Interval must be positive"):
            scheduler.update_schedule(0)
            
        with pytest.raises(ValueError, match="Interval must be positive"):
            scheduler.update_schedule(-5)
    
    @patch('src.services.scheduler_service.schedule')
    def test_start_stop_scheduler(self, mock_schedule, scheduler):
        """Test starting and stopping the scheduler"""
        # Mock schedule methods
        mock_schedule.every.return_value.minutes.do = Mock()
        mock_schedule.clear = Mock()
        mock_schedule.run_pending = Mock()
        mock_schedule.next_run.return_value = datetime.now() + timedelta(minutes=1)
        
        # Test start in a separate thread to avoid blocking
        def start_scheduler():
            scheduler.start()
            
        scheduler_thread = threading.Thread(target=start_scheduler)
        scheduler_thread.start()
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Verify scheduler is running
        assert scheduler.is_running is True
        
        # Stop the scheduler
        scheduler.stop()
        scheduler_thread.join(timeout=2)
        
        # Verify scheduler stopped
        assert scheduler.is_running is False
        mock_schedule.clear.assert_called()
    
    def test_run_once(self, scheduler):
        """Test manual single execution"""
        with patch.object(scheduler, '_run_workflow') as mock_run:
            scheduler.run_once()
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self, mock_workflow):
        """Test successful workflow execution"""
        scheduler = SchedulerService(mock_workflow, interval_minutes=1, max_execution_time_minutes=1)
        
        # Run workflow once
        scheduler._run_workflow()
        
        # Verify execution tracking
        assert scheduler.execution_count == 1
        assert scheduler.last_execution_success is True
        assert scheduler.last_execution_time is not None
    
    @pytest.mark.asyncio
    async def test_workflow_execution_timeout(self):
        """Test workflow timeout handling"""
        async def slow_workflow():
            await asyncio.sleep(2)  # Longer than timeout
            
        scheduler = SchedulerService(
            agent_workflow=slow_workflow,
            interval_minutes=1,
            max_execution_time_minutes=0.02  # Very short timeout for testing
        )
        
        # Run workflow once
        scheduler._run_workflow()
        
        # Verify timeout was handled
        assert scheduler.execution_count == 1
        assert scheduler.last_execution_success is False
    
    @pytest.mark.asyncio
    async def test_workflow_execution_error(self):
        """Test workflow error handling"""
        async def failing_workflow():
            raise Exception("Test error")
            
        scheduler = SchedulerService(
            agent_workflow=failing_workflow,
            interval_minutes=1,
            max_execution_time_minutes=1
        )
        
        # Run workflow once
        scheduler._run_workflow()
        
        # Verify error was handled
        assert scheduler.execution_count == 1
        assert scheduler.last_execution_success is False
    
    def test_concurrent_execution_prevention(self, scheduler):
        """Test that concurrent executions are prevented"""
        # Mock a long-running thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        scheduler.current_execution_thread = mock_thread
        
        with patch.object(scheduler, '_run_workflow') as mock_run:
            scheduler._run_workflow_wrapper()
            # Should not run because previous execution is still active
            mock_run.assert_not_called()
    
    @patch('src.services.scheduler_service.signal.signal')
    def test_signal_handlers(self, mock_signal, mock_workflow):
        """Test signal handler setup"""
        scheduler = SchedulerService(mock_workflow)
        
        # Verify signal handlers were set up
        assert mock_signal.call_count >= 2  # SIGTERM and SIGINT
    
    def test_graceful_shutdown_with_running_thread(self, scheduler):
        """Test graceful shutdown when execution thread is running"""
        # Mock a running thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        scheduler.current_execution_thread = mock_thread
        
        scheduler.stop()
        
        # Verify thread join was called
        mock_thread.join.assert_called_with(timeout=30)
        assert scheduler.is_running is False
    
    @patch('src.services.scheduler_service.schedule')
    def test_update_schedule_while_running(self, mock_schedule, scheduler):
        """Test updating schedule while scheduler is running"""
        # Mock schedule methods
        mock_schedule.clear = Mock()
        mock_schedule.every.return_value.minutes.do = Mock()
        
        scheduler.is_running = True
        scheduler.update_schedule(60)
        
        # Verify schedule was cleared and recreated
        mock_schedule.clear.assert_called_once()
        assert scheduler.interval_minutes == 60
    
    def test_async_workflow_execution(self, mock_workflow):
        """Test async workflow execution in separate event loop"""
        scheduler = SchedulerService(mock_workflow)
        
        # This should not raise an exception
        scheduler._run_async_workflow()
    
    def test_async_workflow_execution_with_error(self):
        """Test async workflow execution error handling"""
        async def failing_workflow():
            raise ValueError("Test async error")
            
        scheduler = SchedulerService(failing_workflow)
        
        # Should raise the exception
        with pytest.raises(ValueError, match="Test async error"):
            scheduler._run_async_workflow()


class TestSchedulerServiceIntegration:
    """Integration tests for SchedulerService"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_cycle(self):
        """Test a complete workflow execution cycle"""
        execution_log = []
        
        async def test_workflow():
            execution_log.append(datetime.now())
            await asyncio.sleep(0.1)
            return "completed"
            
        scheduler = SchedulerService(
            agent_workflow=test_workflow,
            interval_minutes=1,
            max_execution_time_minutes=1
        )
        
        # Run workflow once
        scheduler.run_once()
        
        # Verify execution occurred
        assert len(execution_log) == 1
        assert scheduler.execution_count == 1
        assert scheduler.last_execution_success is True
    
    def test_scheduler_reliability_under_errors(self):
        """Test scheduler continues running despite workflow errors"""
        error_count = 0
        
        async def unreliable_workflow():
            nonlocal error_count
            error_count += 1
            if error_count <= 2:
                raise Exception(f"Error #{error_count}")
            return "success"
            
        scheduler = SchedulerService(
            agent_workflow=unreliable_workflow,
            interval_minutes=1,
            max_execution_time_minutes=1
        )
        
        # Run multiple times
        for _ in range(3):
            scheduler._run_workflow()
            
        # Verify all executions were attempted
        assert scheduler.execution_count == 3
        # Last execution should succeed
        assert scheduler.last_execution_success is True
    
    @pytest.mark.asyncio
    async def test_timeout_handling_reliability(self):
        """Test timeout handling doesn't break scheduler"""
        async def timeout_workflow():
            await asyncio.sleep(10)  # Will timeout
            
        scheduler = SchedulerService(
            agent_workflow=timeout_workflow,
            interval_minutes=1,
            max_execution_time_minutes=0.01  # Very short timeout
        )
        
        # Run workflow that will timeout
        scheduler._run_workflow()
        
        # Verify timeout was handled gracefully
        assert scheduler.execution_count == 1
        assert scheduler.last_execution_success is False
        
        # Scheduler should still be able to run again
        async def quick_workflow():
            return "quick"
            
        scheduler.agent_workflow = quick_workflow
        scheduler._run_workflow()
        
        assert scheduler.execution_count == 2
        assert scheduler.last_execution_success is True


if __name__ == "__main__":
    pytest.main([__file__])