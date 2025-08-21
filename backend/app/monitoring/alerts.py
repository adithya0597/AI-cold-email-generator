"""
Monitoring and Alerting System for AI Content Generation Suite
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    API_ERROR = "api_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RATE_LIMIT = "rate_limit"
    SERVICE_DOWN = "service_down"
    HIGH_ERROR_RATE = "high_error_rate"
    SCRAPING_FAILURE = "scraping_failure"
    LLM_FAILURE = "llm_failure"
    SEARCH_FAILURE = "search_failure"


class MetricsCollector:
    """Collects and tracks metrics for monitoring"""
    
    def __init__(self):
        self.metrics = {
            "email_generations": {"success": 0, "failure": 0, "total": 0},
            "post_generations": {"success": 0, "failure": 0, "total": 0},
            "api_calls": {"openai": 0, "anthropic": 0, "web_search": 0},
            "response_times": [],
            "error_log": [],
            "scraping_failures": [],
            "last_reset": datetime.utcnow()
        }
        self.thresholds = {
            "error_rate": 0.1,  # 10% error rate threshold
            "response_time": 10.0,  # 10 seconds max response time
            "consecutive_failures": 3,  # Alert after 3 consecutive failures
        }
    
    def record_email_generation(self, success: bool, response_time: float = None):
        """Record email generation metrics"""
        self.metrics["email_generations"]["total"] += 1
        if success:
            self.metrics["email_generations"]["success"] += 1
        else:
            self.metrics["email_generations"]["failure"] += 1
        
        if response_time:
            self.metrics["response_times"].append({
                "service": "email",
                "time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def record_post_generation(self, success: bool, response_time: float = None):
        """Record LinkedIn post generation metrics"""
        self.metrics["post_generations"]["total"] += 1
        if success:
            self.metrics["post_generations"]["success"] += 1
        else:
            self.metrics["post_generations"]["failure"] += 1
        
        if response_time:
            self.metrics["response_times"].append({
                "service": "post",
                "time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def record_api_call(self, api_type: str):
        """Record API call"""
        if api_type in self.metrics["api_calls"]:
            self.metrics["api_calls"][api_type] += 1
    
    def record_error(self, error_type: str, error_message: str, context: Dict = None):
        """Record error for analysis"""
        self.metrics["error_log"].append({
            "type": error_type,
            "message": error_message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_error_rate(self, service: str = None) -> float:
        """Calculate error rate"""
        if service == "email":
            total = self.metrics["email_generations"]["total"]
            failures = self.metrics["email_generations"]["failure"]
        elif service == "post":
            total = self.metrics["post_generations"]["total"]
            failures = self.metrics["post_generations"]["failure"]
        else:
            # Overall error rate
            total = (self.metrics["email_generations"]["total"] + 
                    self.metrics["post_generations"]["total"])
            failures = (self.metrics["email_generations"]["failure"] + 
                       self.metrics["post_generations"]["failure"])
        
        if total == 0:
            return 0.0
        return failures / total
    
    def get_average_response_time(self, service: str = None) -> float:
        """Calculate average response time"""
        times = self.metrics["response_times"]
        if service:
            times = [t for t in times if t["service"] == service]
        
        if not times:
            return 0.0
        
        return sum(t["time"] for t in times) / len(times)
    
    def check_thresholds(self) -> List[Dict[str, Any]]:
        """Check if any thresholds are exceeded"""
        alerts = []
        
        # Check error rate
        error_rate = self.get_error_rate()
        if error_rate > self.thresholds["error_rate"]:
            alerts.append({
                "type": AlertType.HIGH_ERROR_RATE,
                "severity": AlertSeverity.WARNING,
                "message": f"Error rate {error_rate:.2%} exceeds threshold {self.thresholds['error_rate']:.2%}",
                "value": error_rate
            })
        
        # Check response time
        avg_response_time = self.get_average_response_time()
        if avg_response_time > self.thresholds["response_time"]:
            alerts.append({
                "type": AlertType.PERFORMANCE_DEGRADATION,
                "severity": AlertSeverity.WARNING,
                "message": f"Average response time {avg_response_time:.2f}s exceeds threshold",
                "value": avg_response_time
            })
        
        # Check consecutive failures
        recent_errors = self.metrics["error_log"][-10:]  # Last 10 errors
        if len(recent_errors) >= self.thresholds["consecutive_failures"]:
            # Check if they're within 5 minutes
            if recent_errors:
                first_error_time = datetime.fromisoformat(recent_errors[0]["timestamp"])
                last_error_time = datetime.fromisoformat(recent_errors[-1]["timestamp"])
                if (last_error_time - first_error_time) < timedelta(minutes=5):
                    alerts.append({
                        "type": AlertType.SERVICE_DOWN,
                        "severity": AlertSeverity.CRITICAL,
                        "message": f"Multiple consecutive failures detected",
                        "errors": recent_errors
                    })
        
        return alerts
    
    def reset_metrics(self):
        """Reset metrics (daily reset)"""
        self.metrics = {
            "email_generations": {"success": 0, "failure": 0, "total": 0},
            "post_generations": {"success": 0, "failure": 0, "total": 0},
            "api_calls": {"openai": 0, "anthropic": 0, "web_search": 0},
            "response_times": [],
            "error_log": [],
            "scraping_failures": [],
            "last_reset": datetime.utcnow()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        error_rate = self.get_error_rate()
        avg_response_time = self.get_average_response_time()
        
        # Determine health status
        if error_rate > 0.2 or avg_response_time > 15:
            status = "unhealthy"
        elif error_rate > 0.1 or avg_response_time > 10:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "metrics": {
                "error_rate": f"{error_rate:.2%}",
                "avg_response_time": f"{avg_response_time:.2f}s",
                "total_requests": self.metrics["email_generations"]["total"] + self.metrics["post_generations"]["total"],
                "uptime": (datetime.utcnow() - self.metrics["last_reset"]).total_seconds()
            },
            "services": {
                "email_generation": {
                    "total": self.metrics["email_generations"]["total"],
                    "success": self.metrics["email_generations"]["success"],
                    "failure": self.metrics["email_generations"]["failure"]
                },
                "post_generation": {
                    "total": self.metrics["post_generations"]["total"],
                    "success": self.metrics["post_generations"]["success"],
                    "failure": self.metrics["post_generations"]["failure"]
                }
            }
        }


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alert_channels = []
        self.alert_history = []
        self.metrics_collector = MetricsCollector()
        
        # Configure alert channels based on environment variables
        if os.getenv("SLACK_WEBHOOK_URL"):
            self.alert_channels.append(SlackAlertChannel())
        if os.getenv("ALERT_EMAIL"):
            self.alert_channels.append(EmailAlertChannel())
        
        # Always add console logging
        self.alert_channels.append(ConsoleAlertChannel())
    
    async def send_alert(self, alert_type: AlertType, severity: AlertSeverity, 
                         message: str, details: Dict = None):
        """Send alert through configured channels"""
        alert = {
            "type": alert_type.value,
            "severity": severity.value,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to history
        self.alert_history.append(alert)
        
        # Send through all channels
        for channel in self.alert_channels:
            try:
                await channel.send(alert)
            except Exception as e:
                logger.error(f"Failed to send alert through {channel.__class__.__name__}: {e}")
    
    async def check_and_alert(self):
        """Check metrics and send alerts if needed"""
        alerts = self.metrics_collector.check_thresholds()
        
        for alert in alerts:
            await self.send_alert(
                alert_type=alert["type"],
                severity=alert["severity"],
                message=alert["message"],
                details=alert
            )
    
    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        """Get recent alert history"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]


class AlertChannel:
    """Base class for alert channels"""
    
    async def send(self, alert: Dict[str, Any]):
        """Send alert through this channel"""
        raise NotImplementedError


class ConsoleAlertChannel(AlertChannel):
    """Console/logging alert channel"""
    
    async def send(self, alert: Dict[str, Any]):
        """Log alert to console"""
        severity = alert["severity"]
        message = f"[ALERT] [{severity.upper()}] {alert['message']}"
        
        if severity == "critical":
            logger.critical(message)
        elif severity == "error":
            logger.error(message)
        elif severity == "warning":
            logger.warning(message)
        else:
            logger.info(message)
        
        if alert.get("details"):
            logger.debug(f"Alert details: {json.dumps(alert['details'], indent=2)}")


class SlackAlertChannel(AlertChannel):
    """Slack webhook alert channel"""
    
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    async def send(self, alert: Dict[str, Any]):
        """Send alert to Slack"""
        if not self.webhook_url:
            return
        
        # Format message for Slack
        color = {
            "critical": "danger",
            "error": "danger",
            "warning": "warning",
            "info": "good"
        }.get(alert["severity"], "warning")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"🚨 {alert['type'].replace('_', ' ').title()}",
                "text": alert["message"],
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert["severity"].upper(),
                        "short": True
                    },
                    {
                        "title": "Time",
                        "value": alert["timestamp"],
                        "short": True
                    }
                ],
                "footer": "AI Content Generation Suite"
            }]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                if response.status_code != 200:
                    logger.error(f"Failed to send Slack alert: {response.text}")
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")


class EmailAlertChannel(AlertChannel):
    """Email alert channel"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("ALERT_SENDER_EMAIL")
        self.sender_password = os.getenv("ALERT_SENDER_PASSWORD")
        self.recipient_email = os.getenv("ALERT_RECIPIENT_EMAIL")
    
    async def send(self, alert: Dict[str, Any]):
        """Send alert via email"""
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            return
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg["Subject"] = f"[{alert['severity'].upper()}] {alert['type'].replace('_', ' ').title()}"
            
            # Email body
            body = f"""
            Alert Type: {alert['type']}
            Severity: {alert['severity'].upper()}
            Time: {alert['timestamp']}
            
            Message:
            {alert['message']}
            
            Details:
            {json.dumps(alert.get('details', {}), indent=2)}
            
            ---
            AI Content Generation Suite Monitoring
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")


# Global alert manager instance
alert_manager = AlertManager()


# Decorator for monitoring function execution
def monitor_execution(service_type: str):
    """Decorator to monitor function execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            success = False
            
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                alert_manager.metrics_collector.record_error(
                    error_type=f"{service_type}_error",
                    error_message=str(e),
                    context={"function": func.__name__}
                )
                raise
            finally:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                
                if service_type == "email":
                    alert_manager.metrics_collector.record_email_generation(success, elapsed)
                elif service_type == "post":
                    alert_manager.metrics_collector.record_post_generation(success, elapsed)
                
                # Check for performance issues
                if elapsed > 10:
                    await alert_manager.send_alert(
                        AlertType.PERFORMANCE_DEGRADATION,
                        AlertSeverity.WARNING,
                        f"{service_type} generation took {elapsed:.2f}s",
                        {"function": func.__name__, "duration": elapsed}
                    )
        
        return wrapper
    return decorator