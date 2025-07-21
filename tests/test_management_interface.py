# tests/test_management_interface.py
"""
Tests for the management interface functionality
"""
import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.management_interface import ManagementInterface
from src.config.agent_config import AgentConfig
from src.models.data_models import GeneratedContent, NewsItem, ContentType


class TestManagementInterface:
    """Test cases for ManagementInterface"""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing"""
        return AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_pass",
            posting_interval_minutes=30,
            max_execution_time_minutes=25,
            max_post_length=300,
            content_themes=["Bitcoin", "Ethereum"],
            min_engagement_score=0.7,
            duplicate_threshold=0.8,
            max_retries=3,
            log_level="INFO",
            log_file_path="logs/test.log"
        )
    
    @pytest.fixture
    def mock_agent(self, sample_config):
        """Create a mock agent for testing"""
        agent = Mock()
        agent.config = sample_config
        agent.content_history = []
        agent.tools = []
        agent.get_workflow_stats.return_value = {
            'total_executions': 10,
            'successful_posts': 8,
            'failed_posts': 2,
            'filtered_content': 1,
            'success_rate': 0.8,
            'content_filter_stats': {},
            'content_history_size': 5
        }
        agent.get_recent_content.return_value = []
        return agent
    
    @pytest.fixture
    def mock_scheduler(self):
        """Create a mock scheduler for testing"""
        scheduler = Mock()
        scheduler.get_status.return_value = {
            'is_running': True,
            'interval_minutes': 30,
            'max_execution_time_minutes': 25,
            'execution_count': 5,
            'last_execution_time': datetime.now(),
            'last_execution_success': True,
            'next_run': datetime.now() + timedelta(minutes=30)
        }
        return scheduler
    
    @pytest.fixture
    def management_interface(self, mock_agent, mock_scheduler):
        """Create a management interface instance for testing"""
        with patch('src.services.management_interface.get_metrics_collector'), \
             patch('src.services.management_interface.get_alert_manager'):
            interface = ManagementInterface(mock_agent, mock_scheduler)
            return interface
    
    def test_initialization(self):
        """Test management interface initialization"""
        interface = ManagementInterface()
        
        assert interface.agent is None
        assert interface.scheduler is None
        assert interface.manual_overrides == {}
        assert 'initialized_at' in interface.system_status
        assert interface.system_status['health_status'] == 'unknown'
    
    def test_set_agent_and_scheduler(self, mock_agent, mock_scheduler):
        """Test setting agent and scheduler instances"""
        interface = ManagementInterface()
        
        interface.set_agent(mock_agent)
        assert interface.agent == mock_agent
        
        interface.set_scheduler(mock_scheduler)
        assert interface.scheduler == mock_scheduler
    
    def test_validate_configuration_valid(self, management_interface, sample_config):
        """Test configuration validation with valid config"""
        is_valid, errors = management_interface.validate_configuration(sample_config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_configuration_invalid(self, management_interface):
        """Test configuration validation with invalid config"""
        invalid_config = AgentConfig(
            perplexity_api_key="",  # Missing required key
            bluesky_username="",    # Missing required username
            bluesky_password="test_pass",
            posting_interval_minutes=1,  # Too short
            max_execution_time_minutes=30,  # Greater than interval
            max_post_length=10,  # Too short
            min_engagement_score=1.5,  # Out of range
            duplicate_threshold=-0.1,  # Out of range
            max_retries=-1  # Negative
        )
        
        is_valid, errors = management_interface.validate_configuration(invalid_config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("PERPLEXITY_API_KEY" in error for error in errors)
    
    def test_load_configuration_from_file_success(self, management_interface, sample_config):
        """Test loading configuration from file successfully"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                'perplexity_api_key': 'test_key',
                'bluesky_username': 'test_user',
                'bluesky_password': 'test_pass',
                'posting_interval_minutes': 30,
                'max_execution_time_minutes': 25
            }
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config, errors = management_interface.load_configuration_from_file(temp_path)
            
            assert config is not None
            assert len(errors) == 0
            assert config.perplexity_api_key == 'test_key'
            assert config.bluesky_username == 'test_user'
        finally:
            Path(temp_path).unlink()
    
    def test_load_configuration_from_file_not_found(self, management_interface):
        """Test loading configuration from non-existent file"""
        config, errors = management_interface.load_configuration_from_file('nonexistent.json')
        
        assert config is None
        assert len(errors) == 1
        assert 'not found' in errors[0]
    
    def test_load_configuration_from_file_invalid_json(self, management_interface):
        """Test loading configuration from invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json content')
            temp_path = f.name
        
        try:
            config, errors = management_interface.load_configuration_from_file(temp_path)
            
            assert config is None
            assert len(errors) == 1
            assert 'Invalid JSON' in errors[0]
        finally:
            Path(temp_path).unlink()
    
    def test_save_configuration_to_file_success(self, management_interface, sample_config):
        """Test saving configuration to file successfully"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            success, errors = management_interface.save_configuration_to_file(sample_config, temp_path)
            
            assert success is True
            assert len(errors) == 0
            
            # Verify file was created and contains correct data
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['perplexity_api_key'] == 'test_key'
            assert saved_data['bluesky_username'] == 'test_user'
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_get_system_status(self, management_interface):
        """Test getting system status"""
        status = management_interface.get_system_status()
        
        assert 'timestamp' in status
        assert 'uptime_seconds' in status
        assert 'health_status' in status
        assert 'components' in status
        
        # Check component statuses
        assert 'agent' in status['components']
        assert 'scheduler' in status['components']
        assert 'metrics' in status['components']
        assert 'alerts' in status['components']
        
        assert status['components']['agent']['status'] == 'active'
        assert status['components']['scheduler']['status'] == 'active'
    
    def test_get_performance_metrics(self, management_interface):
        """Test getting performance metrics"""
        with patch.object(management_interface.metrics_collector, 'get_metrics_for_period') as mock_get_metrics:
            mock_get_metrics.return_value = {
                'workflow_started': 10,
                'workflow_success': 8,
                'workflow_exceptions': 1,
                'news_retrieval_success': 9,
                'posts_published': 7
            }
            
            metrics = management_interface.get_performance_metrics(24)
            
            assert 'period_hours' in metrics
            assert metrics['period_hours'] == 24
            assert 'workflow_metrics' in metrics
            assert 'api_metrics' in metrics
            
            # Check calculated metrics
            workflow_metrics = metrics['workflow_metrics']
            assert workflow_metrics['total_executions'] == 10
            assert workflow_metrics['successful_executions'] == 8
            assert workflow_metrics['success_rate'] == 0.8
    
    def test_get_recent_activity(self, management_interface):
        """Test getting recent activity"""
        with patch.object(management_interface.alert_manager, 'get_recent_alerts') as mock_get_alerts:
            mock_get_alerts.return_value = []
            
            activity = management_interface.get_recent_activity(20)
            
            assert 'timestamp' in activity
            assert 'limit' in activity
            assert activity['limit'] == 20
            assert 'recent_posts' in activity
            assert 'recent_alerts' in activity
    
    def test_set_manual_override(self, management_interface):
        """Test setting manual override"""
        success = management_interface.set_manual_override('skip_posting', True, 60)
        
        assert success is True
        assert 'skip_posting' in management_interface.manual_overrides
        
        override = management_interface.manual_overrides['skip_posting']
        assert override['value'] is True
        assert override['duration_minutes'] == 60
        assert 'set_at' in override
        assert 'expires_at' in override
    
    def test_remove_manual_override(self, management_interface):
        """Test removing manual override"""
        # First set an override
        management_interface.set_manual_override('skip_posting', True, 60)
        assert 'skip_posting' in management_interface.manual_overrides
        
        # Then remove it
        success = management_interface.remove_manual_override('skip_posting')
        
        assert success is True
        assert 'skip_posting' not in management_interface.manual_overrides
    
    def test_remove_nonexistent_override(self, management_interface):
        """Test removing non-existent override"""
        success = management_interface.remove_manual_override('nonexistent')
        
        assert success is False
    
    def test_get_active_overrides(self, management_interface):
        """Test getting active overrides"""
        # Set some overrides
        management_interface.set_manual_override('skip_posting', True, 60)
        management_interface.set_manual_override('force_content_approval', True, 30)
        
        overrides = management_interface.get_active_overrides()
        
        assert 'timestamp' in overrides
        assert 'active_overrides' in overrides
        assert len(overrides['active_overrides']) == 2
        assert 'skip_posting' in overrides['active_overrides']
        assert 'force_content_approval' in overrides['active_overrides']
    
    def test_is_override_active(self, management_interface):
        """Test checking if override is active"""
        # Test non-existent override
        is_active, value = management_interface.is_override_active('nonexistent')
        assert is_active is False
        assert value is None
        
        # Set an override and test
        management_interface.set_manual_override('skip_posting', True, 60)
        is_active, value = management_interface.is_override_active('skip_posting')
        assert is_active is True
        assert value is True
    
    def test_cleanup_expired_overrides(self, management_interface):
        """Test cleanup of expired overrides"""
        # Set an override that expires immediately
        past_time = datetime.now() - timedelta(minutes=1)
        management_interface.manual_overrides['expired_override'] = {
            'value': True,
            'set_at': past_time,
            'expires_at': past_time,
            'duration_minutes': 1
        }
        
        # Set a valid override
        management_interface.set_manual_override('valid_override', True, 60)
        
        # Check that expired override is cleaned up
        management_interface._cleanup_expired_overrides()
        
        assert 'expired_override' not in management_interface.manual_overrides
        assert 'valid_override' in management_interface.manual_overrides
    
    def test_perform_health_check(self, management_interface):
        """Test performing health check"""
        health_check = management_interface.perform_health_check()
        
        assert 'timestamp' in health_check
        assert 'overall_status' in health_check
        assert 'checks' in health_check
        assert 'issues' in health_check
        assert 'issue_count' in health_check
        
        # Check individual component checks
        checks = health_check['checks']
        assert 'agent' in checks
        assert 'scheduler' in checks
        assert 'metrics' in checks
        assert 'alerts' in checks
        
        # Since we have mocked components, health should be good
        assert health_check['overall_status'] in ['healthy', 'degraded']
    
    def test_get_health_summary(self, management_interface):
        """Test getting health summary"""
        # First perform a health check to set status
        management_interface.perform_health_check()
        
        summary = management_interface.get_health_summary()
        
        assert 'status' in summary
        assert 'last_check' in summary
        assert 'uptime_seconds' in summary
        assert 'timestamp' in summary
        
        assert summary['status'] in ['healthy', 'degraded', 'unhealthy']
    
    def test_health_check_with_unhealthy_components(self, management_interface):
        """Test health check when components are unhealthy"""
        # Make scheduler appear unhealthy
        management_interface.scheduler.get_status.return_value = {
            'is_running': False,
            'interval_minutes': 30,
            'max_execution_time_minutes': 25,
            'execution_count': 0,
            'last_execution_time': None,
            'last_execution_success': None,
            'next_run': None
        }
        
        health_check = management_interface.perform_health_check()
        
        assert health_check['overall_status'] == 'unhealthy'
        assert health_check['issue_count'] > 0
        assert any('Scheduler is not running' in issue for issue in health_check['issues'])
    
    def test_health_check_with_low_success_rate(self, management_interface):
        """Test health check when agent has low success rate"""
        # Make agent appear to have low success rate
        management_interface.agent.get_workflow_stats.return_value = {
            'total_executions': 10,
            'successful_posts': 3,  # Low success rate
            'failed_posts': 7,
            'filtered_content': 1,
            'success_rate': 0.3,
            'content_filter_stats': {},
            'content_history_size': 5
        }
        
        health_check = management_interface.perform_health_check()
        
        assert health_check['overall_status'] in ['degraded', 'unhealthy']
        assert health_check['issue_count'] > 0
        assert any('Low agent success rate' in issue for issue in health_check['issues'])


class TestManagementInterfaceIntegration:
    """Integration tests for management interface"""
    
    @pytest.fixture
    def real_config(self):
        """Create a real configuration for integration testing"""
        return AgentConfig.from_env()
    
    def test_configuration_roundtrip(self, real_config):
        """Test saving and loading configuration"""
        interface = ManagementInterface()
        
        # Create a valid config for testing (since real_config from env might be empty)
        valid_config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user", 
            bluesky_password="test_pass",
            posting_interval_minutes=30,
            max_execution_time_minutes=25,
            content_themes=["Bitcoin", "Ethereum"]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save configuration
            success, errors = interface.save_configuration_to_file(valid_config, temp_path)
            assert success is True
            assert len(errors) == 0
            
            # Load configuration back
            loaded_config, load_errors = interface.load_configuration_from_file(temp_path)
            assert loaded_config is not None
            assert len(load_errors) == 0
            
            # Compare key fields (excluding sensitive data)
            assert loaded_config.posting_interval_minutes == valid_config.posting_interval_minutes
            assert loaded_config.max_execution_time_minutes == valid_config.max_execution_time_minutes
            assert loaded_config.content_themes == valid_config.content_themes
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_override_lifecycle(self):
        """Test complete override lifecycle"""
        interface = ManagementInterface()
        
        # Initially no overrides
        overrides = interface.get_active_overrides()
        assert len(overrides['active_overrides']) == 0
        
        # Set an override
        success = interface.set_manual_override('test_override', 'test_value', 1)
        assert success is True
        
        # Check it's active
        is_active, value = interface.is_override_active('test_override')
        assert is_active is True
        assert value == 'test_value'
        
        # Check it appears in active overrides
        overrides = interface.get_active_overrides()
        assert len(overrides['active_overrides']) == 1
        assert 'test_override' in overrides['active_overrides']
        
        # Remove the override
        success = interface.remove_manual_override('test_override')
        assert success is True
        
        # Check it's no longer active
        is_active, value = interface.is_override_active('test_override')
        assert is_active is False
        assert value is None
    
    @patch('src.services.management_interface.get_metrics_collector')
    @patch('src.services.management_interface.get_alert_manager')
    def test_system_status_without_components(self, mock_alert_manager, mock_metrics_collector):
        """Test system status when no components are set"""
        # Setup mocks
        mock_metrics_collector.return_value.get_summary.return_value = {}
        mock_alert_manager.return_value.get_stats.return_value = {}
        
        interface = ManagementInterface()
        status = interface.get_system_status()
        
        assert status['components']['agent']['status'] == 'not_initialized'
        assert status['components']['scheduler']['status'] == 'not_initialized'
        assert status['components']['metrics']['status'] == 'active'
        assert status['components']['alerts']['status'] == 'active'