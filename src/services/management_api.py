# src/services/management_api.py
"""
HTTP API endpoints for the management interface
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, jsonify, request, Response
from werkzeug.exceptions import BadRequest
import threading
import time

from .management_interface import ManagementInterface
from ..config.agent_config import AgentConfig

logger = logging.getLogger(__name__)


class ManagementAPI:
    """
    HTTP API server for management interface endpoints
    """
    
    def __init__(self, management_interface: ManagementInterface, host: str = '0.0.0.0', port: int = 8080):
        """
        Initialize the management API server
        
        Args:
            management_interface: ManagementInterface instance
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 8080)
        """
        self.management_interface = management_interface
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.server_thread = None
        self.is_running = False
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"ManagementAPI initialized on {host}:{port}")
    
    def _setup_routes(self):
        """Setup all API routes"""
        
        # Health check endpoints
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Simple health check endpoint"""
            try:
                health_summary = self.management_interface.get_health_summary()
                status_code = 200 if health_summary['status'] in ['healthy', 'degraded'] else 503
                return jsonify(health_summary), status_code
            except Exception as e:
                logger.error(f"Health check endpoint error: {str(e)}")
                return jsonify({'status': 'error', 'error': str(e)}), 500
        
        @self.app.route('/health/detailed', methods=['GET'])
        def detailed_health_check():
            """Detailed health check endpoint"""
            try:
                health_check = self.management_interface.perform_health_check()
                status_code = 200 if health_check['overall_status'] in ['healthy', 'degraded'] else 503
                return jsonify(health_check), status_code
            except Exception as e:
                logger.error(f"Detailed health check endpoint error: {str(e)}")
                return jsonify({'status': 'error', 'error': str(e)}), 500
        
        # Status and monitoring endpoints
        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Get system status"""
            try:
                status = self.management_interface.get_system_status()
                return jsonify(status), 200
            except Exception as e:
                logger.error(f"Status endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/metrics', methods=['GET'])
        def get_metrics():
            """Get performance metrics"""
            try:
                hours = request.args.get('hours', 24, type=int)
                if hours <= 0 or hours > 168:  # Max 1 week
                    return jsonify({'error': 'Hours must be between 1 and 168'}), 400
                
                metrics = self.management_interface.get_performance_metrics(hours)
                return jsonify(metrics), 200
            except Exception as e:
                logger.error(f"Metrics endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/activity', methods=['GET'])
        def get_activity():
            """Get recent activity"""
            try:
                limit = request.args.get('limit', 20, type=int)
                if limit <= 0 or limit > 100:
                    return jsonify({'error': 'Limit must be between 1 and 100'}), 400
                
                activity = self.management_interface.get_recent_activity(limit)
                return jsonify(activity), 200
            except Exception as e:
                logger.error(f"Activity endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        # Configuration endpoints
        @self.app.route('/config', methods=['GET'])
        def get_config():
            """Get current configuration (sanitized)"""
            try:
                if self.management_interface.agent and hasattr(self.management_interface.agent, 'config'):
                    config_dict = self.management_interface.agent.config.to_dict()
                    return jsonify(config_dict), 200
                else:
                    return jsonify({'error': 'Agent configuration not available'}), 404
            except Exception as e:
                logger.error(f"Config get endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/config/validate', methods=['POST'])
        def validate_config():
            """Validate configuration"""
            try:
                config_data = request.get_json()
                if not config_data:
                    return jsonify({'error': 'No configuration data provided'}), 400
                
                # Create AgentConfig from provided data
                config = AgentConfig(**config_data)
                
                # Validate configuration
                is_valid, errors = self.management_interface.validate_configuration(config)
                
                return jsonify({
                    'valid': is_valid,
                    'errors': errors,
                    'timestamp': datetime.now().isoformat()
                }), 200
                
            except Exception as e:
                logger.error(f"Config validation endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 400
        
        # Manual override endpoints
        @self.app.route('/overrides', methods=['GET'])
        def get_overrides():
            """Get active manual overrides"""
            try:
                overrides = self.management_interface.get_active_overrides()
                return jsonify(overrides), 200
            except Exception as e:
                logger.error(f"Get overrides endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/overrides', methods=['POST'])
        def set_override():
            """Set a manual override"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No override data provided'}), 400
                
                override_type = data.get('type')
                value = data.get('value')
                duration_minutes = data.get('duration_minutes', 60)
                
                if not override_type:
                    return jsonify({'error': 'Override type is required'}), 400
                
                success = self.management_interface.set_manual_override(
                    override_type, value, duration_minutes
                )
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Override set: {override_type}',
                        'timestamp': datetime.now().isoformat()
                    }), 200
                else:
                    return jsonify({'error': 'Failed to set override'}), 500
                    
            except Exception as e:
                logger.error(f"Set override endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 400
        
        @self.app.route('/overrides/<override_type>', methods=['DELETE'])
        def remove_override(override_type: str):
            """Remove a manual override"""
            try:
                success = self.management_interface.remove_manual_override(override_type)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Override removed: {override_type}',
                        'timestamp': datetime.now().isoformat()
                    }), 200
                else:
                    return jsonify({'error': f'Override not found: {override_type}'}), 404
                    
            except Exception as e:
                logger.error(f"Remove override endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        # Control endpoints
        @self.app.route('/control/skip-next-post', methods=['POST'])
        def skip_next_post():
            """Skip the next scheduled post"""
            try:
                duration_minutes = 30  # default
                if request.is_json and request.json:
                    duration_minutes = request.json.get('duration_minutes', 30)
                
                success = self.management_interface.set_manual_override(
                    'skip_posting', True, duration_minutes
                )
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Next post will be skipped for {duration_minutes} minutes',
                        'timestamp': datetime.now().isoformat()
                    }), 200
                else:
                    return jsonify({'error': 'Failed to set skip override'}), 500
                    
            except Exception as e:
                logger.error(f"Skip next post endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/control/force-approve-content', methods=['POST'])
        def force_approve_content():
            """Force approve content (bypass quality filters)"""
            try:
                duration_minutes = 60  # default
                if request.is_json and request.json:
                    duration_minutes = request.json.get('duration_minutes', 60)
                
                success = self.management_interface.set_manual_override(
                    'force_content_approval', True, duration_minutes
                )
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Content approval forced for {duration_minutes} minutes',
                        'timestamp': datetime.now().isoformat()
                    }), 200
                else:
                    return jsonify({'error': 'Failed to set approval override'}), 500
                    
            except Exception as e:
                logger.error(f"Force approve content endpoint error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        # API info endpoint
        @self.app.route('/', methods=['GET'])
        def api_info():
            """API information endpoint"""
            return jsonify({
                'name': 'Bluesky Crypto Agent Management API',
                'version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'endpoints': {
                    'health': {
                        'GET /health': 'Simple health check',
                        'GET /health/detailed': 'Detailed health check'
                    },
                    'monitoring': {
                        'GET /status': 'System status',
                        'GET /metrics?hours=24': 'Performance metrics',
                        'GET /activity?limit=20': 'Recent activity'
                    },
                    'configuration': {
                        'GET /config': 'Get current configuration',
                        'POST /config/validate': 'Validate configuration'
                    },
                    'overrides': {
                        'GET /overrides': 'Get active overrides',
                        'POST /overrides': 'Set manual override',
                        'DELETE /overrides/<type>': 'Remove override'
                    },
                    'control': {
                        'POST /control/skip-next-post': 'Skip next post',
                        'POST /control/force-approve-content': 'Force approve content'
                    }
                }
            }), 200
        
        # Error handlers
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Endpoint not found'}), 404
        
        @self.app.errorhandler(405)
        def method_not_allowed(error):
            return jsonify({'error': 'Method not allowed'}), 405
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500
    
    def start(self, threaded: bool = True):
        """
        Start the API server
        
        Args:
            threaded: Whether to run in a separate thread (default: True)
        """
        logger.info(f"Starting Management API server on {self.host}:{self.port}")
        
        if threaded:
            self.server_thread = threading.Thread(
                target=self._run_server,
                name="management-api-server"
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Wait a moment for server to start
            time.sleep(1)
            
            if self.is_running:
                logger.info("Management API server started successfully")
            else:
                logger.error("Failed to start Management API server")
        else:
            self._run_server()
    
    def _run_server(self):
        """Run the Flask server"""
        try:
            self.is_running = True
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Management API server error: {str(e)}")
            self.is_running = False
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the API server"""
        logger.info("Stopping Management API server")
        self.is_running = False
        
        if self.server_thread and self.server_thread.is_alive():
            # Note: Flask doesn't have a clean shutdown method
            # In production, you'd want to use a proper WSGI server like Gunicorn
            logger.warning("Flask server cannot be cleanly stopped - use proper WSGI server in production")
    
    def is_server_running(self) -> bool:
        """Check if the server is running"""
        return self.is_running