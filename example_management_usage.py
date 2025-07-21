#!/usr/bin/env python3
"""
Example usage of the Bluesky Crypto Agent Management Interface

This script demonstrates how to use the configuration and management interface
to monitor and control the Bluesky crypto agent system.
"""
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock

from src.config.agent_config import AgentConfig
from src.services.management_interface import ManagementInterface
from src.services.management_api import ManagementAPI
from src.agents.bluesky_crypto_agent import BlueskyCryptoAgent
from src.services.scheduler_service import SchedulerService


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")


async def main():
    """Main demonstration function"""
    print_section("Bluesky Crypto Agent Management Interface Demo")
    
    # 1. Configuration Management
    print_subsection("1. Configuration Management")
    
    # Create a sample configuration
    config = AgentConfig(
        perplexity_api_key="demo_perplexity_key",
        bluesky_username="demo_user",
        bluesky_password="demo_password",
        posting_interval_minutes=30,
        max_execution_time_minutes=25,
        max_post_length=300,
        content_themes=["Bitcoin", "Ethereum", "DeFi"],
        min_engagement_score=0.7,
        duplicate_threshold=0.8,
        max_retries=3,
        log_level="INFO",
        log_file_path="logs/demo_agent.log"
    )
    
    print(f"Created configuration with themes: {config.content_themes}")
    print(f"Posting interval: {config.posting_interval_minutes} minutes")
    
    # 2. Initialize Management Interface
    print_subsection("2. Management Interface Initialization")
    
    # Create management interface
    management_interface = ManagementInterface()
    
    # Create mock LLM for demo
    mock_llm = Mock()
    mock_llm.invoke.return_value = Mock(content="Demo response")
    
    # Create agent with management interface
    try:
        agent = BlueskyCryptoAgent(mock_llm, config, management_interface)
        management_interface.set_agent(agent)
        print("✓ Agent initialized and connected to management interface")
    except Exception as e:
        print(f"⚠ Agent initialization failed (expected in demo): {e}")
        # Continue with demo using mock agent
        mock_agent = Mock()
        mock_agent.config = config
        mock_agent.get_workflow_stats.return_value = {
            'total_executions': 5,
            'successful_posts': 4,
            'failed_posts': 1,
            'success_rate': 0.8
        }
        mock_agent.get_recent_content.return_value = []
        management_interface.set_agent(mock_agent)
        print("✓ Mock agent connected for demo purposes")
    
    # Create scheduler
    async def demo_workflow():
        print("Demo workflow executed")
        return Mock(success=True)
    
    scheduler = SchedulerService(demo_workflow, 30, 25)
    management_interface.set_scheduler(scheduler)
    print("✓ Scheduler initialized")
    
    # 3. Configuration Validation
    print_subsection("3. Configuration Validation")
    
    is_valid, errors = management_interface.validate_configuration(config)
    print(f"Configuration valid: {is_valid}")
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ No validation errors")
    
    # Test invalid configuration
    invalid_config = AgentConfig(
        perplexity_api_key="",  # Missing required field
        bluesky_username="demo_user",
        bluesky_password="demo_password",
        posting_interval_minutes=1,  # Too short
        max_post_length=10  # Too short
    )
    
    is_valid, errors = management_interface.validate_configuration(invalid_config)
    print(f"\nInvalid configuration test - Valid: {is_valid}")
    print(f"Found {len(errors)} validation errors:")
    for error in errors[:3]:  # Show first 3 errors
        print(f"  - {error}")
    
    # 4. System Status Reporting
    print_subsection("4. System Status Reporting")
    
    status = management_interface.get_system_status()
    print(f"System uptime: {status['uptime_seconds']:.1f} seconds")
    print(f"Health status: {status['health_status']}")
    print("Component statuses:")
    for component, info in status['components'].items():
        print(f"  - {component}: {info['status']}")
    
    # 5. Performance Metrics
    print_subsection("5. Performance Metrics")
    
    try:
        metrics = management_interface.get_performance_metrics(24)
        print(f"Metrics for last {metrics['period_hours']} hours:")
        
        if 'workflow_metrics' in metrics:
            wf_metrics = metrics['workflow_metrics']
            print(f"  Workflow executions: {wf_metrics.get('total_executions', 0)}")
            print(f"  Success rate: {wf_metrics.get('success_rate', 0):.1%}")
        
        if 'api_metrics' in metrics:
            api_metrics = metrics['api_metrics']
            print(f"  Posts published: {api_metrics.get('posts_published', 0)}")
    except Exception as e:
        print(f"⚠ Metrics collection failed (expected in demo): {e}")
    
    # 6. Manual Overrides
    print_subsection("6. Manual Override System")
    
    # Set a manual override
    success = management_interface.set_manual_override('skip_posting', True, 60)
    print(f"Set skip posting override: {'✓' if success else '✗'}")
    
    # Check if override is active
    is_active, value = management_interface.is_override_active('skip_posting')
    print(f"Skip posting override active: {is_active} (value: {value})")
    
    # Set another override
    success = management_interface.set_manual_override('force_content_approval', True, 30)
    print(f"Set force approval override: {'✓' if success else '✗'}")
    
    # Get all active overrides
    overrides = management_interface.get_active_overrides()
    print(f"Active overrides: {len(overrides['active_overrides'])}")
    for override_name in overrides['active_overrides']:
        print(f"  - {override_name}")
    
    # Remove an override
    success = management_interface.remove_manual_override('skip_posting')
    print(f"Removed skip posting override: {'✓' if success else '✗'}")
    
    # 7. Health Check System
    print_subsection("7. Health Check System")
    
    health_check = management_interface.perform_health_check()
    print(f"Overall health status: {health_check['overall_status']}")
    print(f"Issues found: {health_check['issue_count']}")
    
    print("Component health checks:")
    for component, check in health_check['checks'].items():
        status_icon = "✓" if check['status'] == 'healthy' else "⚠" if check['status'] == 'warning' else "✗"
        print(f"  {status_icon} {component}: {check['status']}")
    
    if health_check['issues']:
        print("Issues:")
        for issue in health_check['issues'][:3]:  # Show first 3 issues
            print(f"  - {issue}")
    
    # Get health summary
    summary = management_interface.get_health_summary()
    print(f"\nHealth summary: {summary['status']}")
    
    # 8. Management API Demo
    print_subsection("8. Management API Demo")
    
    # Create API server
    api = ManagementAPI(management_interface, host='127.0.0.1', port=8080)
    print("Management API created")
    print("Available endpoints:")
    print("  - GET  /health - Simple health check")
    print("  - GET  /health/detailed - Detailed health check")
    print("  - GET  /status - System status")
    print("  - GET  /metrics?hours=24 - Performance metrics")
    print("  - GET  /overrides - Active overrides")
    print("  - POST /overrides - Set override")
    print("  - POST /control/skip-next-post - Skip next post")
    print("  - POST /control/force-approve-content - Force approve content")
    
    # Start API server in background (for demo)
    try:
        api.start(threaded=True)
        time.sleep(1)  # Give server time to start
        
        if api.is_server_running():
            print("✓ Management API server started on http://127.0.0.1:8080")
            print("  Try: curl http://127.0.0.1:8080/health")
            print("  Try: curl http://127.0.0.1:8080/status")
            
            # Keep server running for a moment
            print("\nAPI server running for 5 seconds...")
            time.sleep(5)
            
            api.stop()
            print("✓ API server stopped")
        else:
            print("⚠ API server failed to start")
    except Exception as e:
        print(f"⚠ API server demo failed: {e}")
    
    # 9. Configuration File Operations
    print_subsection("9. Configuration File Operations")
    
    # Save configuration to file
    config_file = "demo_config.json"
    success, errors = management_interface.save_configuration_to_file(config, config_file)
    print(f"Save configuration to {config_file}: {'✓' if success else '✗'}")
    
    if success:
        # Load configuration from file
        loaded_config, errors = management_interface.load_configuration_from_file(config_file)
        if loaded_config:
            print("✓ Configuration loaded from file")
            print(f"  Loaded themes: {loaded_config.content_themes}")
        else:
            print(f"✗ Failed to load configuration: {errors}")
        
        # Clean up
        import os
        try:
            os.remove(config_file)
            print(f"✓ Cleaned up {config_file}")
        except:
            pass
    
    print_section("Demo Complete")
    print("The management interface provides comprehensive monitoring and control")
    print("capabilities for the Bluesky crypto agent system, including:")
    print("  • Configuration validation and management")
    print("  • Real-time system status and health monitoring")
    print("  • Performance metrics collection and reporting")
    print("  • Manual override system for operational control")
    print("  • HTTP API for remote management")
    print("  • Comprehensive error handling and logging")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())