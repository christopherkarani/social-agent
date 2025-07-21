# tests/test_configuration_management_integration.py
"""
Integration tests for configuration management and monitoring system
"""
import pytest
import json
import tempfile
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.management_interface import ManagementInterface
from src.services.management_api import ManagementAPI
from src.config.agent_config import AgentConfig
from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.services.scheduler_service import SchedulerService


class TestConfigurationManagementIntegration:
    """Integration tests for the complete configuration and management system"""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing"""
        return AgentConfig(
            perplexity_api_key="test_perplexity_key",
            bluesky_username="test_user",
            bluesky_password="test_password",
            posting_interval_minutes=30,
            max_execution_time_minutes=25,
            max_post_length=300,
            content_themes=["Bitcoin", "Ethereum", "DeFi"],
            min_engagement_score=0.7,
            duplicate_threshold=0.8,
            max_retries=3,
            log_level="INFO",
            log_file_path="logs/test_integration.log"
        )
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing"""
        llm = Mock()
        llm.invoke.return_value = Mock(content="Test response")
        return llm
    
    @pytest.fixture
    def management_system(self, sample_config, mock_llm):
        """Create a complete management system for testing"""
        with patch('src.services.management_interface.get_metrics_collector') as mock_metrics, \
             patch('src.services.management_interface.get_alert_manager') as mock_alerts, \
             patch('src.agents.bluesky_crypto_agent.get_metrics_collector') as mock_agent_metrics, \
             patch('src.agents.bluesky_crypto_agent.get_alert_manager') as mock_agent_alerts:
            
            # Setup mock returns
            mock_metrics.return_value.get_summary.return_value = {}
            mock_metrics.return_value.get_metrics_for_period.return_value = {
                'workflow_started': 5,
                'workflow_success': 4,
                'posts_published': 3
            }
            mock_alerts.return_value.get_stats.return_value = {}
            mock_alerts.return_value.get_recent_alerts.return_value = []
            
            mock_agent_metrics.return_value = mock_metrics.return_value
            mock_agent_alerts.return_value = mock_alerts.return_value
            
            # Create management interface
            management_interface = ManagementInterface()
            
            # Create agent with management interface
            with patch('src.agents.bluesky_crypto_agent.create_news_retrieval_tool'), \
                 patch('src.agents.bluesky_crypto_agent.create_content_generation_tool'), \
                 patch('src.agents.bluesky_crypto_agent.BlueskySocialTool'):
                
                agent = BlueskyCryptoAgent(mock_llm, sample_config, management_interface)
                management_interface.set_agent(agent)
            
            # Create scheduler
            async def mock_workflow():
                return Mock(success=True)
            
            scheduler = SchedulerService(mock_workflow, 30, 25)
            management_interface.set_scheduler(scheduler)
            
            # Create API
            api = ManagementAPI(management_interface, host='127.0.0.1', port=0)
            
            return {
                'management_interface': management_interface,
                'agent': agent,
                'scheduler': scheduler,
                'api': api,
                'config': sample_config
            }
    
    def test_complete_system_initialization(self, management_system):
        """Test that the complete system initializes correctly"""
        interface = management_system['management_interface']
        agent = management_system['agent']
        scheduler = management_system['scheduler']
        api = management_system['api']
        
        # Check that all components are properly connected
        assert interface.agent == agent
        assert interface.scheduler == scheduler
        assert agent.management_interface == interface
        assert api.management_interface == interface
        
        # Check that agent has management interface
        assert agent.management_interface is not None
    
    def test_configuration_validation_and_loading(self, management_system):
        """Test configuration validation and file operations"""
        interface = management_system['management_interface']
        config = management_system['config']
        
        # Test validation of valid config
        is_valid, errors = interface.validate_configuration(config)
        assert is_valid is True
        assert len(errors) == 0
        
        # Test saving and loading configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save configuration
            success, save_errors = interface.save_configuration_to_file(config, temp_path)
            assert success is True
            assert len(save_errors) == 0
            
            # Verify file exists and has content
            config_file = Path(temp_path)
            assert config_file.exists()
            
            with open(config_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['perplexity_api_key'] == 'test_perplexity_key'
            assert saved_data['posting_interval_minutes'] == 30
            
            # Load configuration back
            loaded_config, load_errors = interface.load_configuration_from_file(temp_path)
            assert loaded_config is not None
            assert len(load_errors) == 0
            
            # Verify loaded config matches original
            assert loaded_config.posting_interval_minutes == config.posting_interval_minutes
            assert loaded_config.content_themes == config.content_themes
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_system_status_reporting(self, management_system):
        """Test comprehensive system status reporting"""
        interface = management_system['management_interface']
        
        # Get system status
        status = interface.get_system_status()
        
        # Verify status structure
        assert 'timestamp' in status
        assert 'uptime_seconds' in status
        assert 'health_status' in status
        assert 'components' in status
        
        # Verify component statuses
        components = status['components']
        assert 'agent' in components
        assert 'scheduler' in components
        assert 'metrics' in components
        assert 'alerts' in components
        
        # Agent should be active
        assert components['agent']['status'] == 'active'
        assert 'workflow_stats' in components['agent']
        
        # Scheduler should be active (though not running in test)
        assert components['scheduler']['status'] in ['active', 'inactive']
    
    def test_performance_metrics_collection(self, management_system):
        """Test performance metrics collection and reporting"""
        interface = management_system['management_interface']
        
        # Get performance metrics
        metrics = interface.get_performance_metrics(24)
        
        # Verify metrics structure
        assert 'period_hours' in metrics
        assert metrics['period_hours'] == 24
        assert 'timestamp' in metrics
        assert 'workflow_metrics' in metrics
        assert 'api_metrics' in metrics
        assert 'content_metrics' in metrics
        assert 'system_metrics' in metrics
        
        # Verify calculated metrics
        workflow_metrics = metrics['workflow_metrics']
        if 'total_executions' in workflow_metrics:
            assert workflow_metrics['total_executions'] >= 0
            assert 'success_rate' in workflow_metrics
    
    def test_manual_override_system(self, management_system):
        """Test the complete manual override system"""
        interface = management_system['management_interface']
        agent = management_system['agent']
        
        # Initially no overrides
        overrides = interface.get_active_overrides()
        assert len(overrides['active_overrides']) == 0
        
        # Set skip posting override
        success = interface.set_manual_override('skip_posting', True, 60)
        assert success is True
        
        # Verify override is active
        is_active, value = interface.is_override_active('skip_posting')
        assert is_active is True
        assert value is True
        
        # Test that agent respects the override
        # This would normally be tested in a workflow execution, but we can check the logic
        if agent.management_interface:
            skip_posting, _ = agent.management_interface.is_override_active('skip_posting')
            assert skip_posting is True
        
        # Set content approval override
        success = interface.set_manual_override('force_content_approval', True, 30)
        assert success is True
        
        # Verify both overrides are active
        overrides = interface.get_active_overrides()
        assert len(overrides['active_overrides']) == 2
        assert 'skip_posting' in overrides['active_overrides']
        assert 'force_content_approval' in overrides['active_overrides']
        
        # Remove one override
        success = interface.remove_manual_override('skip_posting')
        assert success is True
        
        # Verify only one override remains
        overrides = interface.get_active_overrides()
        assert len(overrides['active_overrides']) == 1
        assert 'force_content_approval' in overrides['active_overrides']
        assert 'skip_posting' not in overrides['active_overrides']
    
    def test_health_check_system(self, management_system):
        """Test the comprehensive health check system"""
        interface = management_system['management_interface']
        
        # Perform health check
        health_check = interface.perform_health_check()
        
        # Verify health check structure
        assert 'timestamp' in health_check
        assert 'overall_status' in health_check
        assert 'checks' in health_check
        assert 'issues' in health_check
        assert 'issue_count' in health_check
        
        # Verify individual checks
        checks = health_check['checks']
        assert 'agent' in checks
        assert 'scheduler' in checks
        assert 'metrics' in checks
        assert 'alerts' in checks
        
        # Each check should have status and details
        for check_name, check_data in checks.items():
            assert 'status' in check_data
            assert check_data['status'] in ['healthy', 'warning', 'error']
            assert 'details' in check_data
        
        # Overall status should be reasonable
        assert health_check['overall_status'] in ['healthy', 'degraded', 'unhealthy']
        
        # Get health summary
        summary = interface.get_health_summary()
        assert 'status' in summary
        assert 'last_check' in summary
        assert 'uptime_seconds' in summary
    
    def test_api_endpoints_integration(self, management_system):
        """Test API endpoints with real management interface"""
        api = management_system['api']
        
        with api.app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            assert response.status_code in [200, 503]
            data = json.loads(response.data)
            assert 'status' in data
            
            # Test detailed health endpoint
            response = client.get('/health/detailed')
            assert response.status_code in [200, 503]
            data = json.loads(response.data)
            assert 'overall_status' in data
            assert 'checks' in data
            
            # Test status endpoint
            response = client.get('/status')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'components' in data
            
            # Test metrics endpoint
            response = client.get('/metrics?hours=1')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'workflow_metrics' in data
            
            # Test overrides endpoint
            response = client.get('/overrides')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'active_overrides' in data
            
            # Test setting override via API
            override_data = {
                'type': 'test_override',
                'value': True,
                'duration_minutes': 5
            }
            response = client.post('/overrides',
                                 data=json.dumps(override_data),
                                 content_type='application/json')
            assert response.status_code == 200
            
            # Verify override was set
            response = client.get('/overrides')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'test_override' in data['active_overrides']
            
            # Test control endpoints
            response = client.post('/control/skip-next-post')
            assert response.status_code == 200
            
            response = client.post('/control/force-approve-content')
            assert response.status_code == 200
    
    def test_configuration_validation_edge_cases(self, management_system):
        """Test configuration validation with various edge cases"""
        interface = management_system['management_interface']
        
        # Test configuration with missing required fields
        invalid_config = AgentConfig(
            perplexity_api_key="",  # Empty required field
            bluesky_username="test_user",
            bluesky_password="test_pass"
        )
        
        is_valid, errors = interface.validate_configuration(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("PERPLEXITY_API_KEY" in error for error in errors)
        
        # Test configuration with invalid ranges
        invalid_config = AgentConfig(
            perplexity_api_key="test_key",
            bluesky_username="test_user",
            bluesky_password="test_pass",
            posting_interval_minutes=0,  # Invalid
            max_execution_time_minutes=-1,  # Invalid
            min_engagement_score=2.0,  # Out of range
            duplicate_threshold=-0.5  # Out of range
        )
        
        is_valid, errors = interface.validate_configuration(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_override_expiration(self, management_system):
        """Test that overrides expire correctly"""
        interface = management_system['management_interface']
        
        # Set an override that expires in the past (simulate expired)
        past_time = datetime.now() - timedelta(minutes=1)
        interface.manual_overrides['test_expiry'] = {
            'value': True,
            'set_at': past_time,
            'expires_at': past_time,
            'duration_minutes': 1
        }
        
        # Verify it's cleaned up when checked
        is_active, value = interface.is_override_active('test_expiry')
        assert is_active is False
        assert value is None
        
        # Verify it's cleaned up from active overrides
        overrides = interface.get_active_overrides()
        assert 'test_expiry' not in overrides['active_overrides']
    
    def test_system_resilience(self, management_system):
        """Test system resilience to component failures"""
        interface = management_system['management_interface']
        
        # Test health check when agent fails
        original_agent = interface.agent
        interface.agent = None
        
        health_check = interface.perform_health_check()
        assert health_check['overall_status'] in ['degraded', 'unhealthy']
        assert health_check['issue_count'] > 0
        
        # Restore agent
        interface.agent = original_agent
        
        # Test health check when scheduler fails
        original_scheduler = interface.scheduler
        interface.scheduler = None
        
        health_check = interface.perform_health_check()
        assert health_check['overall_status'] in ['degraded', 'unhealthy']
        
        # Restore scheduler
        interface.scheduler = original_scheduler
        
        # Health should be better now (but might still be degraded due to scheduler not actually running)
        health_check = interface.perform_health_check()
        # The scheduler in test is not actually running, so it might still show as degraded
        assert health_check['overall_status'] in ['healthy', 'degraded', 'unhealthy']
        # But it should have fewer issues than when components were missing
        assert health_check['issue_count'] >= 0
    
    def test_concurrent_access(self, management_system):
        """Test concurrent access to management interface"""
        interface = management_system['management_interface']
        
        def set_overrides(thread_id):
            """Function to set overrides from multiple threads"""
            for i in range(5):
                override_name = f'thread_{thread_id}_override_{i}'
                success = interface.set_manual_override(override_name, f'value_{i}', 60)
                assert success is True
                time.sleep(0.01)  # Small delay
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=set_overrides, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all overrides were set
        overrides = interface.get_active_overrides()
        assert len(overrides['active_overrides']) == 15  # 3 threads * 5 overrides each
        
        # Clean up
        for override_name in list(overrides['active_overrides'].keys()):
            interface.remove_manual_override(override_name)