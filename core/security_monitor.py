"""
Friday AI - Security Monitor
Monitors system health, resource usage, and security status.
Provides alerts for potential issues and maintains logs of system activity.
"""

import os
import json
import psutil
import logging
import platform
import datetime
from typing import Dict, List, Any, Optional, Tuple
import time
import threading

class SecurityMonitor:
    def __init__(self, config_path: str = None):
        """Initialize the security monitoring system.
        
        Args:
            config_path: Path to security configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Set up logging
        self._setup_logging()
        
        # Initialize monitoring state
        self.alerts = []
        self.system_health = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "status": "initializing",
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        # Flag to control background monitoring
        self.monitoring_active = False
        self.monitor_thread = None
        
        logging.info("Security monitor initialized successfully")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load security configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "logging": {
                "level": "INFO",
                "file_path": "logs/security.log",
                "max_size_mb": 10,
                "backup_count": 5
            },
            "monitoring": {
                "check_interval_seconds": 60,
                "thresholds": {
                    "cpu_warning": 80.0,  # Percentage
                    "cpu_critical": 95.0,
                    "memory_warning": 80.0,  # Percentage
                    "memory_critical": 95.0,
                    "disk_warning": 85.0,  # Percentage
                    "disk_critical": 95.0
                }
            },
            "security": {
                "log_api_access": True,
                "log_internet_access": True,
                "require_confirmation_for_system_commands": True
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with default config to ensure all fields exist
                for section in default_config:
                    if section in loaded_config:
                        if isinstance(default_config[section], dict) and isinstance(loaded_config[section], dict):
                            # Deeply merge nested dictionaries
                            for key, value in loaded_config[section].items():
                                if isinstance(value, dict) and key in default_config[section] and isinstance(default_config[section][key], dict):
                                    default_config[section][key].update(value)
                                else:
                                    default_config[section][key] = value
                        else:
                            default_config[section] = loaded_config[section]
            except Exception as e:
                logging.error(f"Error loading security config: {e}. Using defaults.")
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(default_config["logging"]["file_path"]), exist_ok=True)
            
        return default_config
    
    def _setup_logging(self) -> None:
        """Configure logging based on configuration."""
        log_config = self.config["logging"]
        
        # Determine log level
        level_name = log_config.get("level", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        
        # Configure logging
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create a rotating file handler to manage log files
        from logging.handlers import RotatingFileHandler
        
        handler = RotatingFileHandler(
            log_config["file_path"],
            maxBytes=log_config["max_size_mb"] * 1024 * 1024,
            backupCount=log_config["backup_count"]
        )
        
        # Configure logging
        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=[handler]
        )
    
    def start_monitoring(self) -> bool:
        """Start the background monitoring thread.
        
        Returns:
            Success flag
        """
        if self.monitoring_active:
            logging.warning("Monitoring already active")
            return False
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logging.info("System monitoring started")
        return True
    
    def stop_monitoring(self) -> bool:
        """Stop the background monitoring thread.
        
        Returns:
            Success flag
        """
        if not self.monitoring_active:
            logging.warning("Monitoring not active")
            return False
            
        self.monitoring_active = False
        
        # Wait for thread to terminate (with timeout)
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
            
        logging.info("System monitoring stopped")
        return True
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop to check system health."""
        interval = self.config["monitoring"]["check_interval_seconds"]
        
        while self.monitoring_active:
            try:
                # Check system health
                self._check_system_health()
                
                # Check for security issues
                self._check_security()
                
                # Sleep for the configured interval
                time.sleep(interval)
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)  # Still sleep to prevent busy-looping on error
    
    def _check_system_health(self) -> None:
        """Check current system health metrics."""
        try:
            # Get current usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check disk usage for the current directory
            disk = psutil.disk_usage(os.getcwd())
            disk_percent = disk.percent
            
            # Update state
            self.system_health = {
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "disk_usage": disk_percent,
                "status": self._determine_health_status(cpu_percent, memory_percent, disk_percent),
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            # Log if status changed
            if hasattr(self, '_last_status') and self._last_status != self.system_health["status"]:
                logging.info(f"System status changed from {self._last_status} to {self.system_health['status']}")
                
            self._last_status = self.system_health["status"]
            
            # Check thresholds and create alerts if necessary
            self._check_thresholds(cpu_percent, memory_percent, disk_percent)
            
        except Exception as e:
            logging.error(f"Error checking system health: {e}")
            
            # Update state with error
            self.system_health = {
                "cpu_usage": -1,
                "memory_usage": -1,
                "disk_usage": -1,
                "status": "error",
                "error": str(e),
                "last_updated": datetime.datetime.now().isoformat()
            }
    
    def _determine_health_status(self, cpu_percent: float, memory_percent: float, disk_percent: float) -> str:
        """Determine overall system health status based on metrics.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
            
        Returns:
            Health status string
        """
        thresholds = self.config["monitoring"]["thresholds"]
        
        # Check for critical conditions
        if (cpu_percent >= thresholds["cpu_critical"] or 
            memory_percent >= thresholds["memory_critical"] or
            disk_percent >= thresholds["disk_critical"]):
            return "critical"
            
        # Check for warning conditions
        if (cpu_percent >= thresholds["cpu_warning"] or 
            memory_percent >= thresholds["memory_warning"] or
            disk_percent >= thresholds["disk_warning"]):
            return "warning"
            
        # All metrics below warning thresholds
        return "healthy"
    
    def _check_thresholds(self, cpu_percent: float, memory_percent: float, disk_percent: float) -> None:
        """Check metrics against thresholds and generate alerts if necessary.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
        """
        thresholds = self.config["monitoring"]["thresholds"]
        
        # Check CPU
        if cpu_percent >= thresholds["cpu_critical"]:
            self._add_alert("CPU usage critical", f"CPU usage at {cpu_percent}%", "critical")
        elif cpu_percent >= thresholds["cpu_warning"]:
            self._add_alert("CPU usage warning", f"CPU usage at {cpu_percent}%", "warning")
            
        # Check memory
        if memory_percent >= thresholds["memory_critical"]:
            self._add_alert("Memory usage critical", f"Memory usage at {memory_percent}%", "critical")
        elif memory_percent >= thresholds["memory_warning"]:
            self._add_alert("Memory usage warning", f"Memory usage at {memory_percent}%", "warning")
            
        # Check disk
        if disk_percent >= thresholds["disk_critical"]:
            self._add_alert("Disk usage critical", f"Disk usage at {disk_percent}%", "critical")
        elif disk_percent >= thresholds["disk_warning"]:
            self._add_alert("Disk usage warning", f"Disk usage at {disk_percent}%", "warning")
    
    def _check_security(self) -> None:
        """Check for potential security issues."""
        # This is a placeholder for future security checks
        # Will be expanded in future implementations
        pass
    
    def _add_alert(self, title: str, message: str, level: str) -> None:
        """Add a new alert to the alerts list.
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert level (info, warning, critical)
        """
        alert = {
            "id": len(self.alerts) + 1,
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.datetime.now().isoformat(),
            "acknowledged": False
        }
        
        # Check if this alert already exists and is unacknowledged
        for existing_alert in self.alerts:
            if (existing_alert["title"] == title and 
                existing_alert["level"] == level and 
                not existing_alert["acknowledged"]):
                # Update existing alert instead of adding a new one
                existing_alert["message"] = message
                existing_alert["timestamp"] = alert["timestamp"]
                return
        
        # Log the alert
        log_func = logging.warning if level == "warning" else logging.error if level == "critical" else logging.info
        log_func(f"Alert: {title} - {message}")
        
        # Add new alert
        self.alerts.append(alert)
        
        # Keep only recent alerts (max 100)
        if len(self.alerts) > 100:
            # Remove oldest acknowledged alerts first
            acknowledged = [a for a in self.alerts if a["acknowledged"]]
            if acknowledged:
                self.alerts.remove(min(acknowledged, key=lambda x: x["timestamp"]))
            else:
                # All alerts are unacknowledged, remove oldest
                self.alerts.remove(min(self.alerts, key=lambda x: x["timestamp"]))
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """Acknowledge an alert to mark it as seen.
        
        Args:
            alert_id: ID of the alert to acknowledge
            
        Returns:
            Success flag
        """
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                return True
        return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status.
        
        Returns:
            System health information
        """
        # Update system health before returning
        self._check_system_health()
        return self.system_health
    
    def get_alerts(self, include_acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get current alerts.
        
        Args:
            include_acknowledged: Whether to include acknowledged alerts
            
        Returns:
            List of alerts
        """
        if include_acknowledged:
            return self.alerts
        else:
            return [a for a in self.alerts if not a["acknowledged"]]
    
    def log_api_access(self, api_name: str, parameters: Dict[str, Any]) -> None:
        """Log external API access for security monitoring.
        
        Args:
            api_name: Name of the API being accessed
            parameters: Parameters being sent to the API
        """
        if not self.config["security"]["log_api_access"]:
            return
            
        logging.info(f"API Access: {api_name} - Parameters: {json.dumps(parameters)}")
    
    def log_internet_access(self, url: str, purpose: str) -> None:
        """Log internet access for security monitoring.
        
        Args:
            url: URL being accessed
            purpose: Purpose of the access
        """
        if not self.config["security"]["log_internet_access"]:
            return
            
        logging.info(f"Internet Access: {url} - Purpose: {purpose}")
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed system status information.
        
        Returns:
            Detailed status dictionary
        """
        try:
            # Update system health
            self._check_system_health()
            
            # Get detailed system info
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(os.getcwd())
            
            status = {
                "system": {
                    "platform": platform.platform(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version()
                },
                "resources": {
                    "cpu": {
                        "usage_percent": self.system_health["cpu_usage"],
                        "count": psutil.cpu_count(logical=True)
                    },
                    "memory": {
                        "usage_percent": self.system_health["memory_usage"],
                        "total_gb": round(memory.total / (1024 ** 3), 2),
                        "available_gb": round(memory.available / (1024 ** 3), 2)
                    },
                    "disk": {
                        "usage_percent": self.system_health["disk_usage"],
                        "total_gb": round(disk.total / (1024 ** 3), 2),
                        "free_gb": round(disk.free / (1024 ** 3), 2)
                    }
                },
                "status": self.system_health["status"],
                "alert_count": len(self.get_alerts()),
                "monitoring_active": self.monitoring_active
            }
            
            return status
        except Exception as e:
            logging.error(f"Error getting detailed status: {e}")
            return {
                "error": str(e),
                "status": "error",
                "alert_count": len(self.get_alerts()),
                "monitoring_active": self.monitoring_active
            }