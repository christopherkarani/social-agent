# src/services/management_interface.py
"""
Management interface for configuration, monitoring, and control of the Bluesky crypto agent
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict
from pathlib import Path

from ..config.agent_config import AgentConfig
from ..utils.metrics_collector import get_metrics_collector
from ..utils.alert_system import get_alert_manager
from ..models.data_models import GeneratedContent, PostResult

logger = logging.getLogger(__name__)


class ManagementInterface:
    """
    Provides configuration management, status reporting, and control capabilities
    for the Bluesky crypto agent system
    """
    
    def __init__(self, agent=None, scheduler=None):
        """
        Initialize the management interface
        
        Args:
            agent: BlueskyCryptoAgent instance (optional)
            scheduler: SchedulerService instance (optional)
        """
        self.agent = agent
        self.scheduler = scheduler
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
        self.manual_overrides = {}
        self.system_status = {
            'initialized_at': datetime.now(),
            'last_health_check': None,
            'health_status': 'unknown'
        }
        
        logger.info("ManagementInterface initialized")
    
    def set_agent(self, agent):
        """Set the agent instance"""
        self.agent = agent
        logger.info("Agent instance set in management interface")
    
    def set_scheduler(self, scheduler):
        """Set the scheduler instance"""
        self.scheduler = scheduler
        logger.info("Scheduler instance set in management interface")
    
    # Configuration Management
    def validate_configuration(self, config: AgentConfig) -> Tuple[bool, List[str]]:
        """
        Validate agent configuration
        
        Args:
            config: AgentConfig instance to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        logger.info("Validating agent configuration")
        
        errors = []
        
        try:
            # Check required API keys
            if not config.perplexity_api_key:
                errors.append("PERPLEXITY_API_KEY is required")
                
            if not config.bluesky_username:
                errors.append("BLUESKY_USERNAME is required")
                
            if not config.bluesky_password:
                errors.append("BLUESKY_PASSWORD is required")
                
            # Validate numeric ranges
            if config.posting_interval_minutes < 1:
                errors.append("posting_interval_minutes must be at least 1")
                
            if config.max_execution_time_minutes < 1:
                errors.append("max_execution_time_minutes must be at least 1")
                
            if config.max_post_length < 50:
                errors.append("max_post_length must be at least 50 characters")
                
            if not (0.0 <= config.min_engagement_score <= 1.0):
                errors.append("min_engagement_score must be between 0.0 and 1.0")
                
            if not (0.0 <= config.duplicate_threshold <= 1.0):
                errors.append("duplicate_threshold must be between 0.0 and 1.0")
                
            if config.max_retries < 0:
                errors.append("max_retries must be non-negative")
                
            # Validate content themes
            if not config.content_themes:
                errors.append("content_themes cannot be empty")
            
            # Additional custom validations
            if config.posting_interval_minutes < 5:
                errors.append("Posting interval should be at least 5 minutes for rate limiting")
            
            if config.max_execution_time_minutes >= config.posting_interval_minutes:
                errors.append("Max execution time should be less than posting interval")
            
            # Validate log file path
            try:
                log_path = Path(config.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Invalid log file path: {str(e)}")
            
            # Check content themes
            if len(config.content_themes) > 10:
                errors.append("Too many content themes (max 10 recommended)")
            
            is_valid = len(errors) == 0
            
            logger.info(f"Configuration validation completed: {'valid' if is_valid else 'invalid'}")
            return is_valid, errors
            
        except Exception as e:
            error_msg = f"Configuration validation error: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]
    
    def load_configuration_from_file(self, config_path: str) -> Tuple[Optional[AgentConfig], List[str]]:
        """
        Load configuration from JSON file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (config_object, list_of_errors)
        """
        logger.info(f"Loading configuration from file: {config_path}")
        
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return None, [f"Configuration file not found: {config_path}"]
            
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Create AgentConfig from loaded data
            config = AgentConfig(**config_data)
            
            # Validate the loaded configuration
            is_valid, errors = self.validate_configuration(config)
            
            if is_valid:
                logger.info("Configuration loaded and validated successfully")
                return config, []
            else:
                logger.error(f"Loaded configuration is invalid: {errors}")
                return config, errors
                
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file: {str(e)}"
            logger.error(error_msg)
            return None, [error_msg]
        except Exception as e:
            error_msg = f"Error loading configuration: {str(e)}"
            logger.error(error_msg)
            return None, [error_msg]
    
    def save_configuration_to_file(self, config: AgentConfig, config_path: str) -> Tuple[bool, List[str]]:
        """
        Save configuration to JSON file
        
        Args:
            config: AgentConfig instance to save
            config_path: Path where to save the configuration
            
        Returns:
            Tuple of (success, list_of_errors)
        """
        logger.info(f"Saving configuration to file: {config_path}")
        
        try:
            # Validate configuration before saving
            is_valid, errors = self.validate_configuration(config)
            if not is_valid:
                return False, errors
            
            # Convert to dictionary and sanitize sensitive data
            config_dict = asdict(config)
            
            # Create backup of existing config if it exists
            config_file = Path(config_path)
            if config_file.exists():
                backup_path = config_file.with_suffix('.bak')
                config_file.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")
            
            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save configuration
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            logger.info("Configuration saved successfully")
            return True, []
            
        except Exception as e:
            error_msg = f"Error saving configuration: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]
    
    # Status Reporting and Monitoring
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status
        
        Returns:
            Dictionary containing system status information
        """
        logger.debug("Generating system status report")
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - self.system_status['initialized_at']).total_seconds(),
            'health_status': self.system_status['health_status'],
            'last_health_check': self.system_status['last_health_check'].isoformat() if self.system_status['last_health_check'] else None,
            'components': {}
        }
        
        # Agent status
        if self.agent:
            agent_stats = self.agent.get_workflow_stats()
            status['components']['agent'] = {
                'status': 'active',
                'workflow_stats': agent_stats,
                'content_history_size': len(self.agent.content_history),
                'tools_count': len(self.agent.tools)
            }
        else:
            status['components']['agent'] = {'status': 'not_initialized'}
        
        # Scheduler status
        if self.scheduler:
            scheduler_status = self.scheduler.get_status()
            status['components']['scheduler'] = {
                'status': 'active' if scheduler_status['is_running'] else 'inactive',
                'details': scheduler_status
            }
        else:
            status['components']['scheduler'] = {'status': 'not_initialized'}
        
        # Metrics status
        try:
            metrics_summary = self.metrics_collector.get_summary()
            status['components']['metrics'] = {
                'status': 'active',
                'summary': metrics_summary
            }
        except Exception as e:
            status['components']['metrics'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Alert system status
        try:
            alert_stats = self.alert_manager.get_stats()
            status['components']['alerts'] = {
                'status': 'active',
                'stats': alert_stats
            }
        except Exception as e:
            status['components']['alerts'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Manual overrides status
        status['manual_overrides'] = {
            'active_count': len(self.manual_overrides),
            'overrides': list(self.manual_overrides.keys())
        }
        
        return status
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance metrics for the specified time period
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Dictionary containing performance metrics
        """
        logger.debug(f"Generating performance metrics for last {hours} hours")
        
        try:
            # Get metrics from collector
            metrics = self.metrics_collector.get_metrics_for_period(hours)
            
            # Calculate derived metrics
            performance_summary = {
                'period_hours': hours,
                'timestamp': datetime.now().isoformat(),
                'workflow_metrics': {},
                'api_metrics': {},
                'content_metrics': {},
                'system_metrics': {}
            }
            
            # Process workflow metrics
            if 'workflow_started' in metrics:
                workflow_started = metrics['workflow_started']
                workflow_success = metrics.get('workflow_success', 0)
                workflow_exceptions = metrics.get('workflow_exceptions', 0)
                
                performance_summary['workflow_metrics'] = {
                    'total_executions': workflow_started,
                    'successful_executions': workflow_success,
                    'failed_executions': workflow_started - workflow_success,
                    'exception_count': workflow_exceptions,
                    'success_rate': workflow_success / workflow_started if workflow_started > 0 else 0
                }
            
            # Process API metrics
            performance_summary['api_metrics'] = {
                'news_retrieval_success': metrics.get('news_retrieval_success', 0),
                'news_retrieval_failures': metrics.get('news_retrieval_failures', 0),
                'content_generation_success': metrics.get('content_generation_success', 0),
                'content_generation_failures': metrics.get('content_generation_failures', 0),
                'posting_failures': metrics.get('posting_failures', 0),
                'posts_published': metrics.get('posts_published', 0)
            }
            
            # Process content metrics
            performance_summary['content_metrics'] = {
                'content_approved': metrics.get('content_approved', 0),
                'content_filtered': metrics.get('content_filtered', 0),
                'avg_engagement_score': metrics.get('avg_content_engagement_score', 0)
            }
            
            # Add timing metrics if available
            if 'avg_workflow_duration' in metrics:
                performance_summary['system_metrics']['avg_workflow_duration_seconds'] = metrics['avg_workflow_duration']
            
            return performance_summary
            
        except Exception as e:
            logger.error(f"Error generating performance metrics: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_recent_activity(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get recent system activity
        
        Args:
            limit: Maximum number of activities to return
            
        Returns:
            Dictionary containing recent activity information
        """
        logger.debug(f"Getting recent activity (limit: {limit})")
        
        activity = {
            'timestamp': datetime.now().isoformat(),
            'limit': limit,
            'recent_posts': [],
            'recent_alerts': [],
            'recent_errors': []
        }
        
        # Get recent posts from agent
        if self.agent:
            try:
                recent_content = self.agent.get_recent_content(limit)
                activity['recent_posts'] = recent_content
            except Exception as e:
                logger.error(f"Error getting recent posts: {str(e)}")
                activity['recent_posts'] = []
        
        # Get recent alerts
        try:
            recent_alerts = self.alert_manager.get_recent_alerts(limit)
            activity['recent_alerts'] = [alert.to_dict() for alert in recent_alerts]
        except Exception as e:
            logger.error(f"Error getting recent alerts: {str(e)}")
            activity['recent_alerts'] = []
        
        return activity
    
    # Manual Override Capabilities
    def set_manual_override(self, override_type: str, value: Any, duration_minutes: int = 60) -> bool:
        """
        Set a manual override for system behavior
        
        Args:
            override_type: Type of override ('skip_posting', 'force_content_approval', etc.)
            value: Override value
            duration_minutes: How long the override should last
            
        Returns:
            True if override was set successfully
        """
        logger.info(f"Setting manual override: {override_type} = {value} for {duration_minutes} minutes")
        
        try:
            expiry_time = datetime.now() + timedelta(minutes=duration_minutes)
            
            self.manual_overrides[override_type] = {
                'value': value,
                'set_at': datetime.now(),
                'expires_at': expiry_time,
                'duration_minutes': duration_minutes
            }
            
            # Log the override for audit purposes
            logger.warning(f"Manual override activated: {override_type} = {value} (expires: {expiry_time})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting manual override: {str(e)}")
            return False
    
    def remove_manual_override(self, override_type: str) -> bool:
        """
        Remove a manual override
        
        Args:
            override_type: Type of override to remove
            
        Returns:
            True if override was removed successfully
        """
        logger.info(f"Removing manual override: {override_type}")
        
        try:
            if override_type in self.manual_overrides:
                del self.manual_overrides[override_type]
                logger.info(f"Manual override removed: {override_type}")
                return True
            else:
                logger.warning(f"Manual override not found: {override_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing manual override: {str(e)}")
            return False
    
    def get_active_overrides(self) -> Dict[str, Any]:
        """
        Get all active manual overrides
        
        Returns:
            Dictionary of active overrides
        """
        logger.debug("Getting active manual overrides")
        
        # Clean up expired overrides
        self._cleanup_expired_overrides()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'active_overrides': self.manual_overrides.copy()
        }
    
    def is_override_active(self, override_type: str) -> Tuple[bool, Any]:
        """
        Check if a specific override is active
        
        Args:
            override_type: Type of override to check
            
        Returns:
            Tuple of (is_active, override_value)
        """
        self._cleanup_expired_overrides()
        
        if override_type in self.manual_overrides:
            return True, self.manual_overrides[override_type]['value']
        else:
            return False, None
    
    def _cleanup_expired_overrides(self):
        """Clean up expired manual overrides"""
        now = datetime.now()
        expired_keys = []
        
        for key, override in self.manual_overrides.items():
            if now > override['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            logger.info(f"Manual override expired: {key}")
            del self.manual_overrides[key]
    
    # Health Check Endpoints
    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Dictionary containing health check results
        """
        logger.info("Performing system health check")
        
        health_check = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        issues = []
        
        # Check agent health
        try:
            if self.agent:
                agent_stats = self.agent.get_workflow_stats()
                
                # Check if agent has been successful recently
                if agent_stats['total_executions'] > 0:
                    success_rate = agent_stats['success_rate']
                    if success_rate < 0.5:
                        issues.append(f"Low agent success rate: {success_rate:.2%}")
                
                health_check['checks']['agent'] = {
                    'status': 'healthy' if len(issues) == 0 else 'warning',
                    'details': agent_stats
                }
            else:
                issues.append("Agent not initialized")
                health_check['checks']['agent'] = {
                    'status': 'error',
                    'details': 'Agent not initialized'
                }
        except Exception as e:
            issues.append(f"Agent health check failed: {str(e)}")
            health_check['checks']['agent'] = {
                'status': 'error',
                'details': str(e)
            }
        
        # Check scheduler health
        try:
            if self.scheduler:
                scheduler_status = self.scheduler.get_status()
                
                if not scheduler_status['is_running']:
                    issues.append("Scheduler is not running")
                
                health_check['checks']['scheduler'] = {
                    'status': 'healthy' if scheduler_status['is_running'] else 'error',
                    'details': scheduler_status
                }
            else:
                issues.append("Scheduler not initialized")
                health_check['checks']['scheduler'] = {
                    'status': 'error',
                    'details': 'Scheduler not initialized'
                }
        except Exception as e:
            issues.append(f"Scheduler health check failed: {str(e)}")
            health_check['checks']['scheduler'] = {
                'status': 'error',
                'details': str(e)
            }
        
        # Check metrics collector health
        try:
            metrics_summary = self.metrics_collector.get_summary()
            health_check['checks']['metrics'] = {
                'status': 'healthy',
                'details': metrics_summary
            }
        except Exception as e:
            issues.append(f"Metrics collector health check failed: {str(e)}")
            health_check['checks']['metrics'] = {
                'status': 'error',
                'details': str(e)
            }
        
        # Check alert system health
        try:
            alert_stats = self.alert_manager.get_stats()
            health_check['checks']['alerts'] = {
                'status': 'healthy',
                'details': alert_stats
            }
        except Exception as e:
            issues.append(f"Alert system health check failed: {str(e)}")
            health_check['checks']['alerts'] = {
                'status': 'error',
                'details': str(e)
            }
        
        # Check disk space for logs
        try:
            if self.agent and hasattr(self.agent, 'config'):
                log_path = Path(self.agent.config.log_file_path)
                if log_path.exists():
                    # Simple disk space check (this is basic - could be enhanced)
                    stat = log_path.stat()
                    health_check['checks']['disk_space'] = {
                        'status': 'healthy',
                        'details': f'Log file size: {stat.st_size} bytes'
                    }
                else:
                    health_check['checks']['disk_space'] = {
                        'status': 'warning',
                        'details': 'Log file does not exist yet'
                    }
        except Exception as e:
            health_check['checks']['disk_space'] = {
                'status': 'error',
                'details': str(e)
            }
        
        # Determine overall status
        if any(check['status'] == 'error' for check in health_check['checks'].values()):
            health_check['overall_status'] = 'unhealthy'
        elif any(check['status'] == 'warning' for check in health_check['checks'].values()):
            health_check['overall_status'] = 'degraded'
        
        health_check['issues'] = issues
        health_check['issue_count'] = len(issues)
        
        # Update system status
        self.system_status['last_health_check'] = datetime.now()
        self.system_status['health_status'] = health_check['overall_status']
        
        logger.info(f"Health check completed: {health_check['overall_status']} ({len(issues)} issues)")
        
        return health_check
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a simple health summary for quick checks
        
        Returns:
            Dictionary containing basic health information
        """
        return {
            'status': self.system_status['health_status'],
            'last_check': self.system_status['last_health_check'].isoformat() if self.system_status['last_health_check'] else None,
            'uptime_seconds': (datetime.now() - self.system_status['initialized_at']).total_seconds(),
            'timestamp': datetime.now().isoformat()
        }