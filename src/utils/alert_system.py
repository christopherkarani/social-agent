# src/utils/alert_system.py
"""
Alert system for critical errors and failures in the Bluesky Crypto Agent
Provides configurable alerting mechanisms with different severity levels
"""
import logging
import smtplib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict, deque
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"


@dataclass
class Alert:
    """Individual alert data structure"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    component: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 5
    max_alerts_per_hour: int = 10
    enabled: bool = True
    description: str = ""


class AlertManager:
    """
    Comprehensive alert management system with rate limiting and multiple channels
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize alert manager
        
        Args:
            config: Alert configuration dictionary
        """
        self.config = config or {}
        self._alerts: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        self._alert_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._last_alert_time: Dict[str, datetime] = {}
        self._rules: Dict[str, AlertRule] = {}
        self._lock = threading.RLock()
        
        # Email configuration
        self.email_config = self.config.get('email', {})
        
        # Webhook configuration
        self.webhook_config = self.config.get('webhook', {})
        
        # Setup default alert rules
        self._setup_default_rules()
        
        logger.info("AlertManager initialized")
    
    def add_rule(self, rule: AlertRule) -> None:
        """
        Add an alert rule
        
        Args:
            rule: AlertRule to add
        """
        with self._lock:
            self._rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove an alert rule
        
        Args:
            rule_name: Name of rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        with self._lock:
            if rule_name in self._rules:
                del self._rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
                return True
            return False
    
    def trigger_alert(self, 
                     title: str,
                     message: str,
                     severity: AlertSeverity,
                     component: str,
                     metadata: Optional[Dict[str, Any]] = None,
                     channels: Optional[List[AlertChannel]] = None) -> Optional[Alert]:
        """
        Trigger an alert
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            component: Component that triggered the alert
            metadata: Additional metadata
            channels: Specific channels to use (overrides default)
            
        Returns:
            Created Alert object or None if rate limited
        """
        if metadata is None:
            metadata = {}
        
        # Generate alert ID
        alert_id = f"{component}_{title}_{int(time.time())}"
        
        # Check rate limiting
        if not self._check_rate_limit(component, title):
            logger.warning(f"Alert rate limited: {title} from {component}")
            return None
        
        # Create alert
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            component=component,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        # Store alert
        with self._lock:
            self._alerts.append(alert)
            self._alert_counts[f"{component}_{title}"].append(datetime.now())
            self._last_alert_time[f"{component}_{title}"] = datetime.now()
        
        # Determine channels to use
        if channels is None:
            channels = self._get_default_channels(severity)
        
        # Send alert through channels
        self._send_alert(alert, channels)
        
        logger.info(f"Alert triggered: {title} [{severity.value}] from {component}")
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved
        
        Args:
            alert_id: ID of alert to resolve
            
        Returns:
            True if alert was found and resolved
        """
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    logger.info(f"Alert resolved: {alert_id}")
                    return True
        return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """
        Get list of active (unresolved) alerts
        
        Args:
            severity: Filter by severity level
            
        Returns:
            List of active alerts
        """
        with self._lock:
            active_alerts = [alert for alert in self._alerts if not alert.resolved]
            
            if severity:
                active_alerts = [alert for alert in active_alerts if alert.severity == severity]
            
            return sorted(active_alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get alert summary for the specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Alert summary dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_alerts = [
                alert for alert in self._alerts 
                if alert.timestamp >= cutoff_time
            ]
            
            # Count by severity
            severity_counts = defaultdict(int)
            for alert in recent_alerts:
                severity_counts[alert.severity.value] += 1
            
            # Count by component
            component_counts = defaultdict(int)
            for alert in recent_alerts:
                component_counts[alert.component] += 1
            
            # Active alerts
            active_alerts = [alert for alert in recent_alerts if not alert.resolved]
            
            return {
                "time_period_hours": hours,
                "total_alerts": len(recent_alerts),
                "active_alerts": len(active_alerts),
                "resolved_alerts": len(recent_alerts) - len(active_alerts),
                "severity_breakdown": dict(severity_counts),
                "component_breakdown": dict(component_counts),
                "most_recent_alert": recent_alerts[-1].to_dict() if recent_alerts else None
            }
    
    def check_rules(self, context: Dict[str, Any]) -> List[Alert]:
        """
        Check all alert rules against the provided context
        
        Args:
            context: Context data to evaluate rules against
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        with self._lock:
            for rule_name, rule in self._rules.items():
                if not rule.enabled:
                    continue
                
                try:
                    if rule.condition(context):
                        alert = self.trigger_alert(
                            title=f"Rule triggered: {rule_name}",
                            message=rule.description or f"Alert rule {rule_name} was triggered",
                            severity=rule.severity,
                            component="alert_system",
                            metadata={"rule_name": rule_name, "context": context},
                            channels=rule.channels
                        )
                        if alert:
                            triggered_alerts.append(alert)
                
                except Exception as e:
                    logger.error(f"Error evaluating alert rule {rule_name}: {e}")
        
        return triggered_alerts
    
    def _setup_default_rules(self) -> None:
        """Setup default alert rules"""
        
        # High error rate rule
        self.add_rule(AlertRule(
            name="high_error_rate",
            condition=lambda ctx: ctx.get("error_rate", 0) > 0.1,  # 10% error rate
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.LOG, AlertChannel.EMAIL],
            cooldown_minutes=10,
            description="Error rate exceeded 10%"
        ))
        
        # API failure rule
        self.add_rule(AlertRule(
            name="api_failure",
            condition=lambda ctx: ctx.get("api_failures", 0) > 3,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.CONSOLE],
            cooldown_minutes=5,
            description="Multiple API failures detected"
        ))
        
        # Long execution time rule
        self.add_rule(AlertRule(
            name="long_execution_time",
            condition=lambda ctx: ctx.get("execution_time", 0) > 1200,  # 20 minutes
            severity=AlertSeverity.MEDIUM,
            channels=[AlertChannel.LOG],
            cooldown_minutes=15,
            description="Execution time exceeded 20 minutes"
        ))
        
        # Memory usage rule
        self.add_rule(AlertRule(
            name="high_memory_usage",
            condition=lambda ctx: ctx.get("memory_usage_percent", 0) > 90,
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.LOG, AlertChannel.EMAIL],
            cooldown_minutes=10,
            description="Memory usage exceeded 90%"
        ))
    
    def _check_rate_limit(self, component: str, title: str) -> bool:
        """Check if alert is rate limited"""
        key = f"{component}_{title}"
        now = datetime.now()
        
        with self._lock:
            # Check cooldown
            if key in self._last_alert_time:
                time_since_last = now - self._last_alert_time[key]
                if time_since_last.total_seconds() < 300:  # 5 minute default cooldown
                    return False
            
            # Check hourly limit
            hour_ago = now - timedelta(hours=1)
            recent_alerts = [
                timestamp for timestamp in self._alert_counts[key]
                if timestamp >= hour_ago
            ]
            
            if len(recent_alerts) >= 10:  # Default max 10 per hour
                return False
        
        return True
    
    def _get_default_channels(self, severity: AlertSeverity) -> List[AlertChannel]:
        """Get default channels based on severity"""
        if severity == AlertSeverity.CRITICAL:
            return [AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.CONSOLE]
        elif severity == AlertSeverity.HIGH:
            return [AlertChannel.LOG, AlertChannel.EMAIL]
        elif severity == AlertSeverity.MEDIUM:
            return [AlertChannel.LOG]
        else:
            return [AlertChannel.LOG]
    
    def _send_alert(self, alert: Alert, channels: List[AlertChannel]) -> None:
        """Send alert through specified channels"""
        for channel in channels:
            try:
                if channel == AlertChannel.LOG:
                    self._send_log_alert(alert)
                elif channel == AlertChannel.EMAIL:
                    self._send_email_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_alert(alert)
                elif channel == AlertChannel.CONSOLE:
                    self._send_console_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")
    
    def _send_log_alert(self, alert: Alert) -> None:
        """Send alert to log"""
        log_level = {
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(alert.severity, logging.INFO)
        
        logger.log(
            log_level,
            f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message}",
            extra={
                "alert_id": alert.id,
                "component": alert.component,
                "severity": alert.severity.value,
                "metadata": alert.metadata
            }
        )
    
    def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email"""
        if not self.email_config.get('enabled', False):
            return
        
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            from_email = self.email_config.get('from_email', username)
            to_emails = self.email_config.get('to_emails', [])
            
            if not all([smtp_server, username, password, to_emails]):
                logger.warning("Email configuration incomplete, skipping email alert")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] Bluesky Agent Alert: {alert.title}"
            
            # Email body
            body = f"""
Alert Details:
- Title: {alert.title}
- Severity: {alert.severity.value.upper()}
- Component: {alert.component}
- Time: {alert.timestamp.isoformat()}
- Message: {alert.message}

Metadata:
{json.dumps(alert.metadata, indent=2)}

Alert ID: {alert.id}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent for: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, alert: Alert) -> None:
        """Send alert via webhook"""
        if not self.webhook_config.get('enabled', False):
            return
        
        try:
            import requests
            
            webhook_url = self.webhook_config.get('url')
            if not webhook_url:
                return
            
            payload = {
                "alert": alert.to_dict(),
                "timestamp": datetime.now().isoformat()
            }
            
            headers = self.webhook_config.get('headers', {})
            timeout = self.webhook_config.get('timeout', 10)
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            
            logger.info(f"Webhook alert sent for: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_console_alert(self, alert: Alert) -> None:
        """Send alert to console"""
        severity_colors = {
            AlertSeverity.LOW: '\033[94m',      # Blue
            AlertSeverity.MEDIUM: '\033[93m',   # Yellow
            AlertSeverity.HIGH: '\033[91m',     # Red
            AlertSeverity.CRITICAL: '\033[95m'  # Magenta
        }
        
        color = severity_colors.get(alert.severity, '')
        reset_color = '\033[0m'
        
        print(f"\n{color}🚨 ALERT [{alert.severity.value.upper()}]{reset_color}")
        print(f"Title: {alert.title}")
        print(f"Component: {alert.component}")
        print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Message: {alert.message}")
        if alert.metadata:
            print(f"Metadata: {json.dumps(alert.metadata, indent=2)}")
        print(f"Alert ID: {alert.id}\n")


# Global alert manager instance
_global_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager


def initialize_alert_manager(config: Optional[Dict[str, Any]] = None) -> AlertManager:
    """
    Initialize the global alert manager
    
    Args:
        config: Alert configuration
        
    Returns:
        Initialized AlertManager instance
    """
    global _global_alert_manager
    _global_alert_manager = AlertManager(config)
    logger.info("Global alert manager initialized")
    return _global_alert_manager


# Convenience functions
def trigger_alert(title: str, message: str, severity: AlertSeverity, component: str, 
                 metadata: Optional[Dict[str, Any]] = None) -> Optional[Alert]:
    """Trigger an alert using the global alert manager"""
    return get_alert_manager().trigger_alert(title, message, severity, component, metadata)


def check_alert_rules(context: Dict[str, Any]) -> List[Alert]:
    """Check alert rules using the global alert manager"""
    return get_alert_manager().check_rules(context)