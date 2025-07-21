# tests/test_management_api.py
"""
Tests for the management API endpoints
"""
import pytest
import json
import time
import threading
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.services.management_api import ManagementAPI
from src.services.management_interface import ManagementInterface
from src.config.agent_config import AgentConfig


class TestManagementAPI:
    """Test cases for ManagementAPI"""
    
    @pytest.fixture
    def mock_management_interface(self):
        """Create a mock management interface for testing"""
        interface = Mock(spec=ManagementInterface)
        
        # Setup default return values
        interface.get_health_summary.return_value = {
            'status': 'healthy',
            'last_check': datetime.now().isoformat(),
            'uptime_seconds': 3600,
            'timestamp': datetime.now().isoformat()
        }
        
        interface.perform_health_check.return_value = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {
                'agent': {'status': 'healthy', 'details': {}},
                'scheduler': {'status': 'healthy', 'details': {}},
                'metrics': {'status': 'healthy', 'details': {}},
                'alerts': {'status': 'healthy', 'details': {}}
            },
            'issues': [],
            'issue_count': 0
        }
        
        interface.get_system_status.return_value = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': 3600,
            'health_status': 'healthy',
            'components': {
                'agent': {'status': 'active'},
                'scheduler': {'status': 'active'},
                'metrics': {'status': 'active'},
                'alerts': {'status': 'active'}
            },
            'manual_overrides': {'active_count': 0, 'overrides': []}
        }
        
        def get_performance_metrics(hours):
            return {
                'period_hours': hours,
                'timestamp': datetime.now().isoformat(),
                'workflow_metrics': {'total_executions': 10, 'success_rate': 0.8},
                'api_metrics': {'posts_published': 8},
                'content_metrics': {'content_approved': 9},
                'system_metrics': {}
            }
        
        def get_recent_activity(limit):
            return {
                'timestamp': datetime.now().isoformat(),
                'limit': limit,
                'recent_posts': [],
                'recent_alerts': [],
                'recent_errors': []
            }
        
        interface.get_performance_metrics.side_effect = get_performance_metrics
        interface.get_recent_activity.side_effect = get_recent_activity
        
        interface.validate_configuration.return_value = (True, [])
        
        interface.get_active_overrides.return_value = {
            'timestamp': datetime.now().isoformat(),
            'active_overrides': {}
        }
        
        interface.set_manual_override.return_value = True
        interface.remove_manual_override.return_value = True
        
        return interface
    
    @pytest.fixture
    def management_api(self, mock_management_interface):
        """Create a management API instance for testing"""
        return ManagementAPI(mock_management_interface, host='127.0.0.1', port=0)  # Port 0 for testing
    
    @pytest.fixture
    def client(self, management_api):
        """Create a test client for the Flask app"""
        management_api.app.config['TESTING'] = True
        with management_api.app.test_client() as client:
            yield client
    
    def test_initialization(self, mock_management_interface):
        """Test API initialization"""
        api = ManagementAPI(mock_management_interface, host='localhost', port=8080)
        
        assert api.management_interface == mock_management_interface
        assert api.host == 'localhost'
        assert api.port == 8080
        assert api.app is not None
        assert api.is_running is False
    
    def test_api_info_endpoint(self, client):
        """Test the API info endpoint"""
        response = client.get('/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'name' in data
        assert 'version' in data
        assert 'timestamp' in data
        assert 'endpoints' in data
        assert data['name'] == 'Bluesky Crypto Agent Management API'
    
    def test_health_check_endpoint(self, client, mock_management_interface):
        """Test the health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'status' in data
        assert 'timestamp' in data
        assert data['status'] == 'healthy'
        
        mock_management_interface.get_health_summary.assert_called_once()
    
    def test_health_check_endpoint_unhealthy(self, client, mock_management_interface):
        """Test health check endpoint when system is unhealthy"""
        mock_management_interface.get_health_summary.return_value = {
            'status': 'unhealthy',
            'last_check': datetime.now().isoformat(),
            'uptime_seconds': 3600,
            'timestamp': datetime.now().isoformat()
        }
        
        response = client.get('/health')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'unhealthy'
    
    def test_detailed_health_check_endpoint(self, client, mock_management_interface):
        """Test the detailed health check endpoint"""
        response = client.get('/health/detailed')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'timestamp' in data
        assert 'overall_status' in data
        assert 'checks' in data
        assert data['overall_status'] == 'healthy'
        
        mock_management_interface.perform_health_check.assert_called_once()
    
    def test_status_endpoint(self, client, mock_management_interface):
        """Test the status endpoint"""
        response = client.get('/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'timestamp' in data
        assert 'components' in data
        assert 'health_status' in data
        
        mock_management_interface.get_system_status.assert_called_once()
    
    def test_metrics_endpoint(self, client, mock_management_interface):
        """Test the metrics endpoint"""
        response = client.get('/metrics')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'period_hours' in data
        assert 'workflow_metrics' in data
        assert data['period_hours'] == 24
        
        mock_management_interface.get_performance_metrics.assert_called_once_with(24)
    
    def test_metrics_endpoint_with_custom_hours(self, client, mock_management_interface):
        """Test metrics endpoint with custom hours parameter"""
        response = client.get('/metrics?hours=48')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['period_hours'] == 48
        mock_management_interface.get_performance_metrics.assert_called_once_with(48)
    
    def test_metrics_endpoint_invalid_hours(self, client):
        """Test metrics endpoint with invalid hours parameter"""
        response = client.get('/metrics?hours=0')
        assert response.status_code == 400
        
        response = client.get('/metrics?hours=200')
        assert response.status_code == 400
    
    def test_activity_endpoint(self, client, mock_management_interface):
        """Test the activity endpoint"""
        response = client.get('/activity')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'timestamp' in data
        assert 'recent_posts' in data
        assert 'recent_alerts' in data
        assert data['limit'] == 20
        
        mock_management_interface.get_recent_activity.assert_called_once_with(20)
    
    def test_activity_endpoint_with_custom_limit(self, client, mock_management_interface):
        """Test activity endpoint with custom limit parameter"""
        response = client.get('/activity?limit=50')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['limit'] == 50
        mock_management_interface.get_recent_activity.assert_called_once_with(50)
    
    def test_config_endpoint(self, client, mock_management_interface):
        """Test the config endpoint"""
        # Mock agent with config
        mock_agent = Mock()
        mock_agent.config.to_dict.return_value = {
            'posting_interval_minutes': 30,
            'max_post_length': 300,
            'content_themes': ['Bitcoin', 'Ethereum']
        }
        mock_management_interface.agent = mock_agent
        
        response = client.get('/config')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'posting_interval_minutes' in data
        assert data['posting_interval_minutes'] == 30
    
    def test_config_endpoint_no_agent(self, client, mock_management_interface):
        """Test config endpoint when no agent is available"""
        mock_management_interface.agent = None
        
        response = client.get('/config')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_validate_config_endpoint(self, client, mock_management_interface):
        """Test the config validation endpoint"""
        config_data = {
            'perplexity_api_key': 'test_key',
            'bluesky_username': 'test_user',
            'bluesky_password': 'test_pass',
            'posting_interval_minutes': 30
        }
        
        response = client.post('/config/validate', 
                             data=json.dumps(config_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'valid' in data
        assert 'errors' in data
        assert data['valid'] is True
        
        mock_management_interface.validate_configuration.assert_called_once()
    
    def test_validate_config_endpoint_no_data(self, client):
        """Test config validation endpoint with no data"""
        response = client.post('/config/validate')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_get_overrides_endpoint(self, client, mock_management_interface):
        """Test the get overrides endpoint"""
        response = client.get('/overrides')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'timestamp' in data
        assert 'active_overrides' in data
        
        mock_management_interface.get_active_overrides.assert_called_once()
    
    def test_set_override_endpoint(self, client, mock_management_interface):
        """Test the set override endpoint"""
        override_data = {
            'type': 'skip_posting',
            'value': True,
            'duration_minutes': 60
        }
        
        response = client.post('/overrides',
                             data=json.dumps(override_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'success' in data
        assert data['success'] is True
        
        mock_management_interface.set_manual_override.assert_called_once_with(
            'skip_posting', True, 60
        )
    
    def test_set_override_endpoint_no_type(self, client):
        """Test set override endpoint without type"""
        override_data = {
            'value': True,
            'duration_minutes': 60
        }
        
        response = client.post('/overrides',
                             data=json.dumps(override_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_remove_override_endpoint(self, client, mock_management_interface):
        """Test the remove override endpoint"""
        response = client.delete('/overrides/skip_posting')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'success' in data
        assert data['success'] is True
        
        mock_management_interface.remove_manual_override.assert_called_once_with('skip_posting')
    
    def test_remove_override_endpoint_not_found(self, client, mock_management_interface):
        """Test remove override endpoint when override not found"""
        mock_management_interface.remove_manual_override.return_value = False
        
        response = client.delete('/overrides/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_skip_next_post_endpoint(self, client, mock_management_interface):
        """Test the skip next post endpoint"""
        response = client.post('/control/skip-next-post',
                             data=json.dumps({'duration_minutes': 45}),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'success' in data
        assert data['success'] is True
        assert '45 minutes' in data['message']
        
        mock_management_interface.set_manual_override.assert_called_once_with(
            'skip_posting', True, 45
        )
    
    def test_skip_next_post_endpoint_default_duration(self, client, mock_management_interface):
        """Test skip next post endpoint with default duration"""
        response = client.post('/control/skip-next-post')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'success' in data
        assert '30 minutes' in data['message']
        
        mock_management_interface.set_manual_override.assert_called_once_with(
            'skip_posting', True, 30
        )
    
    def test_force_approve_content_endpoint(self, client, mock_management_interface):
        """Test the force approve content endpoint"""
        response = client.post('/control/force-approve-content',
                             data=json.dumps({'duration_minutes': 90}),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'success' in data
        assert data['success'] is True
        assert '90 minutes' in data['message']
        
        mock_management_interface.set_manual_override.assert_called_once_with(
            'force_content_approval', True, 90
        )
    
    def test_error_handlers(self, client):
        """Test error handlers"""
        # Test 404
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        
        # Test 405
        response = client.post('/health')
        assert response.status_code == 405
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_endpoint_error_handling(self, client, mock_management_interface):
        """Test error handling in endpoints"""
        # Make health check raise an exception
        mock_management_interface.get_health_summary.side_effect = Exception("Test error")
        
        response = client.get('/health')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Test error' in data['error']


class TestManagementAPIIntegration:
    """Integration tests for the management API"""
    
    @pytest.fixture
    def real_management_interface(self):
        """Create a real management interface for integration testing"""
        with patch('src.services.management_interface.get_metrics_collector') as mock_metrics, \
             patch('src.services.management_interface.get_alert_manager') as mock_alerts:
            
            # Setup proper mock returns
            mock_metrics_instance = Mock()
            mock_metrics_instance.get_summary.return_value = {'total_metrics': 0}
            mock_metrics_instance.get_metrics_for_period.return_value = {}
            mock_metrics.return_value = mock_metrics_instance
            
            mock_alerts_instance = Mock()
            mock_alerts_instance.get_stats.return_value = {'total_alerts': 0}
            mock_alerts_instance.get_recent_alerts.return_value = []
            mock_alerts.return_value = mock_alerts_instance
            
            interface = ManagementInterface()
            # Perform a health check to initialize the status
            interface.perform_health_check()
            return interface
    
    def test_api_server_lifecycle(self, real_management_interface):
        """Test starting and stopping the API server"""
        api = ManagementAPI(real_management_interface, host='127.0.0.1', port=0)
        
        # Initially not running
        assert api.is_server_running() is False
        
        # Start server in thread
        api.start(threaded=True)
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Should be running now
        assert api.is_server_running() is True
        
        # Stop server
        api.stop()
        
        # Should not be running
        assert api.is_server_running() is False
    
    def test_health_check_integration(self, real_management_interface):
        """Test health check with real management interface"""
        api = ManagementAPI(real_management_interface)
        
        with api.app.test_client() as client:
            response = client.get('/health')
            
            assert response.status_code in [200, 503]  # Depends on system state
            data = json.loads(response.data)
            
            assert 'status' in data
            assert 'timestamp' in data
            assert data['status'] in ['healthy', 'degraded', 'unhealthy']
    
    def test_status_integration(self, real_management_interface):
        """Test status endpoint with real management interface"""
        api = ManagementAPI(real_management_interface)
        
        with api.app.test_client() as client:
            response = client.get('/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'timestamp' in data
            assert 'components' in data
            assert 'health_status' in data
            
            # Components should show not_initialized since no agent/scheduler set
            assert data['components']['agent']['status'] == 'not_initialized'
            assert data['components']['scheduler']['status'] == 'not_initialized'
    
    def test_override_integration(self, real_management_interface):
        """Test override functionality with real management interface"""
        api = ManagementAPI(real_management_interface)
        
        with api.app.test_client() as client:
            # Initially no overrides
            response = client.get('/overrides')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['active_overrides']) == 0
            
            # Set an override
            override_data = {
                'type': 'test_override',
                'value': 'test_value',
                'duration_minutes': 1
            }
            response = client.post('/overrides',
                                 data=json.dumps(override_data),
                                 content_type='application/json')
            assert response.status_code == 200
            
            # Check override is active
            response = client.get('/overrides')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['active_overrides']) == 1
            assert 'test_override' in data['active_overrides']
            
            # Remove override
            response = client.delete('/overrides/test_override')
            assert response.status_code == 200
            
            # Check override is gone
            response = client.get('/overrides')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['active_overrides']) == 0