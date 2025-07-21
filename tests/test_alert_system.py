# tests/test_alert_system.py
"""
Unit tests for alert system functionality
"""
import unittest
import tempfile
import json
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock

from src.utils.alert_system import (
    Alert, AlertRule, AlertManager, AlertSeverity, AlertChannel,
    get_alert_manager, initialize_alert_manager, trigger_alert, check_alert_rules
)


class TestAlert(unittest.TestCase):
    """Test cases for Alert data class"""
    
    def test_alert_creation(self):
        """Test Alert creation and serialization"""
        timestamp = datetime.now()
        metadata = {"component": "test", "error_code": 500}
        
        alert = Alert(
            id="test-alert-1",
            title="Test Alert",
            message="This is a test alert",
            severity=AlertSeverity.HIGH,
            component="test_component",
            timestamp=timestamp,
            metadata=metadata
        )
        
        self.assertEqual(alert.title, "Test Alert")
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        self.assertEqual(alert.component, "test_component")
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_at)
        
        # Test serialization
        alert_dict = alert.to_dict()
        self.assertEqual(alert_dict["title"], "Test Alert")
        self.assertEqual(alert_dict["severity"], "high")
        self.assertEqual(alert_dict["timestamp"], timestamp.isoformat())
        self.assertEqual(alert_dict["metadata"], metadata)
    
    def test_alert_resolution(self):
        """Test alert resolution"""
        alert = Alert(
            id="test-alert-1",
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.MEDIUM,
            component="test_component",
            timestamp=datetime.now(),
            metadata={}
        )
        
        # Initially not resolved
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_at)
        
        # Mark as resolved
        alert.resolved = True
        alert.resolved_at = datetime.now()
        
        self.assertTrue(alert.resolved)
        self.assertIsNotNone(alert.resolved_at)


class TestAlertRule(unittest.TestCase):
    """Test cases for AlertRule"""
    
    def test_alert_rule_creation(self):
        """Test AlertRule creation"""
        def test_condition(ctx):
            return ctx.get("error_count", 0) > 5
        
        rule = AlertRule(
            name="high_error_rate",
            condition=test_condition,
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.LOG, AlertChannel.EMAIL],
            cooldown_minutes=10,
            max_alerts_per_hour=5,
            description="High error rate detected"
        )
        
        self.assertEqual(rule.name, "high_error_rate")
        self.assertEqual(rule.severity, AlertSeverity.HIGH)
        self.assertEqual(len(rule.channels), 2)
        self.assertTrue(rule.enabled)
        
        # Test condition
        self.assertTrue(rule.condition({"error_count": 10}))
        self.assertFalse(rule.condition({"error_count": 3}))


class TestAlertManager(unittest.TestCase):
    """Test cases for AlertManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            "email": {
                "enabled": False  # Disable email for testing
            },
            "webhook": {
                "enabled": False  # Disable webhook for testing
            }
        }
        self.alert_manager = AlertManager(self.config)
    
    def test_alert_manager_initialization(self):
        """Test AlertManager initialization"""
        self.assertIsInstance(self.alert_manager, AlertManager)
        self.assertEqual(len(self.alert_manager._alerts), 0)
        self.assertGreater(len(self.alert_manager._rules), 0)  # Should have default rules
    
    def test_trigger_alert(self):
        """Test triggering an alert"""
        alert = self.alert_manager.trigger_alert(
            title="Test Alert",
            message="This is a test alert",
            severity=AlertSeverity.MEDIUM,
            component="test_component",
            metadata={"test": "data"}
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.title, "Test Alert")
        self.assertEqual(alert.severity, AlertSeverity.MEDIUM)
        self.assertEqual(alert.component, "test_component")
        self.assertEqual(alert.metadata["test"], "data")
        
        # Check that alert was stored
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(active_alerts), 1)
        self.assertEqual(active_alerts[0].id, alert.id)
    
    def test_resolve_alert(self):
        """Test resolving an alert"""
        # Trigger an alert
        alert = self.alert_manager.trigger_alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.LOW,
            component="test_component"
        )
        
        # Verify it's active
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(active_alerts), 1)
        
        # Resolve the alert
        resolved = self.alert_manager.resolve_alert(alert.id)
        self.assertTrue(resolved)
        
        # Verify it's no longer active
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(active_alerts), 0)
        
        # Try to resolve non-existent alert
        resolved = self.alert_manager.resolve_alert("non-existent-id")
        self.assertFalse(resolved)
    
    def test_get_active_alerts_by_severity(self):
        """Test filtering active alerts by severity"""
        # Trigger alerts with different severities
        self.alert_manager.trigger_alert(
            title="Low Alert", message="Low", severity=AlertSeverity.LOW, component="test"
        )
        self.alert_manager.trigger_alert(
            title="High Alert", message="High", severity=AlertSeverity.HIGH, component="test"
        )
        self.alert_manager.trigger_alert(
            title="Critical Alert", message="Critical", severity=AlertSeverity.CRITICAL, component="test"
        )
        
        # Get all active alerts
        all_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(all_alerts), 3)
        
        # Get only high severity alerts
        high_alerts = self.alert_manager.get_active_alerts(AlertSeverity.HIGH)
        self.assertEqual(len(high_alerts), 1)
        self.assertEqual(high_alerts[0].title, "High Alert")
        
        # Get only critical alerts
        critical_alerts = self.alert_manager.get_active_alerts(AlertSeverity.CRITICAL)
        self.assertEqual(len(critical_alerts), 1)
        self.assertEqual(critical_alerts[0].title, "Critical Alert")
    
    def test_get_alert_summary(self):
        """Test alert summary generation"""
        # Trigger some alerts
        self.alert_manager.trigger_alert(
            title="Error Alert", message="Error", severity=AlertSeverity.HIGH, component="api"
        )
        self.alert_manager.trigger_alert(
            title="Warning Alert", message="Warning", severity=AlertSeverity.MEDIUM, component="database"
        )
        
        # Resolve one alert
        alerts = self.alert_manager.get_active_alerts()
        self.alert_manager.resolve_alert(alerts[0].id)
        
        # Get summary
        summary = self.alert_manager.get_alert_summary(hours=1)
        
        self.assertEqual(summary["total_alerts"], 2)
        self.assertEqual(summary["active_alerts"], 1)
        self.assertEqual(summary["resolved_alerts"], 1)
        self.assertIn("severity_breakdown", summary)
        self.assertIn("component_breakdown", summary)
    
    def test_rate_limiting(self):
        """Test alert rate limiting"""
        # Trigger multiple alerts quickly
        alerts = []
        for i in range(5):
            alert = self.alert_manager.trigger_alert(
                title="Repeated Alert",
                message=f"Message {i}",
                severity=AlertSeverity.LOW,
                component="test_component"
            )
            alerts.append(alert)
            time.sleep(0.1)  # Small delay
        
        # First alert should succeed, subsequent ones might be rate limited
        successful_alerts = [a for a in alerts if a is not None]
        self.assertGreater(len(successful_alerts), 0)
        self.assertLessEqual(len(successful_alerts), 5)
    
    def test_add_custom_rule(self):
        """Test adding custom alert rules"""
        def custom_condition(ctx):
            return ctx.get("cpu_usage", 0) > 90
        
        custom_rule = AlertRule(
            name="high_cpu_usage",
            condition=custom_condition,
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.LOG],
            description="CPU usage is too high"
        )
        
        self.alert_manager.add_rule(custom_rule)
        
        # Test the rule
        context = {"cpu_usage": 95}
        triggered_alerts = self.alert_manager.check_rules(context)
        
        self.assertEqual(len(triggered_alerts), 1)
        self.assertIn("high_cpu_usage", triggered_alerts[0].title)
    
    def test_remove_rule(self):
        """Test removing alert rules"""
        # Add a custom rule
        def test_condition(ctx):
            return False
        
        rule = AlertRule(
            name="test_rule",
            condition=test_condition,
            severity=AlertSeverity.LOW,
            channels=[AlertChannel.LOG]
        )
        
        self.alert_manager.add_rule(rule)
        
        # Verify rule exists
        self.assertIn("test_rule", self.alert_manager._rules)
        
        # Remove the rule
        removed = self.alert_manager.remove_rule("test_rule")
        self.assertTrue(removed)
        self.assertNotIn("test_rule", self.alert_manager._rules)
        
        # Try to remove non-existent rule
        removed = self.alert_manager.remove_rule("non_existent_rule")
        self.assertFalse(removed)
    
    def test_check_default_rules(self):
        """Test default alert rules"""
        # Test high error rate rule
        context = {"error_rate": 0.15}  # 15% error rate
        triggered_alerts = self.alert_manager.check_rules(context)
        
        # Should trigger high_error_rate rule
        error_rate_alerts = [a for a in triggered_alerts if "error_rate" in a.title.lower()]
        self.assertGreater(len(error_rate_alerts), 0)
        
        # Test API failure rule
        context = {"api_failures": 5}
        triggered_alerts = self.alert_manager.check_rules(context)
        
        # Should trigger api_failure rule
        api_failure_alerts = [a for a in triggered_alerts if "api" in a.title.lower()]
        self.assertGreater(len(api_failure_alerts), 0)
    
    @patch('smtplib.SMTP')
    def test_email_alert_disabled(self, mock_smtp):
        """Test that email alerts are disabled in test config"""
        alert = self.alert_manager.trigger_alert(
            title="Email Test",
            message="Test email alert",
            severity=AlertSeverity.CRITICAL,
            component="test",
            channels=[AlertChannel.EMAIL]
        )
        
        # Email should not be sent because it's disabled in config
        mock_smtp.assert_not_called()
    
    def test_console_alert(self):
        """Test console alert output"""
        with patch('builtins.print') as mock_print:
            self.alert_manager.trigger_alert(
                title="Console Test",
                message="Test console alert",
                severity=AlertSeverity.HIGH,
                component="test",
                channels=[AlertChannel.CONSOLE]
            )
            
            # Should have printed to console
            mock_print.assert_called()
            
            # Check that alert information was printed
            printed_text = ''.join([str(call) for call in mock_print.call_args_list])
            self.assertIn("Console Test", printed_text)
            self.assertIn("HIGH", printed_text)


class TestGlobalAlertFunctions(unittest.TestCase):
    """Test cases for global alert functions"""
    
    def test_get_alert_manager(self):
        """Test getting global alert manager instance"""
        manager1 = get_alert_manager()
        manager2 = get_alert_manager()
        
        # Should return the same instance
        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, AlertManager)
    
    def test_initialize_alert_manager(self):
        """Test initializing global alert manager"""
        config = {"test": "config"}
        
        manager = initialize_alert_manager(config)
        
        self.assertIsInstance(manager, AlertManager)
        self.assertEqual(manager.config, config)
        
        # Should be the same as global instance
        global_manager = get_alert_manager()
        self.assertIs(manager, global_manager)
    
    def test_trigger_alert_global(self):
        """Test global trigger_alert function"""
        alert = trigger_alert(
            title="Global Test",
            message="Test global alert function",
            severity=AlertSeverity.MEDIUM,
            component="global_test"
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.title, "Global Test")
        self.assertEqual(alert.component, "global_test")
    
    def test_check_alert_rules_global(self):
        """Test global check_alert_rules function"""
        context = {"error_rate": 0.2}  # 20% error rate
        
        triggered_alerts = check_alert_rules(context)
        
        self.assertIsInstance(triggered_alerts, list)
        # Should trigger at least the high error rate rule
        self.assertGreater(len(triggered_alerts), 0)


if __name__ == '__main__':
    unittest.main()