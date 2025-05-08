# command_deck/error_tracker.py
import asyncio
import datetime
import logging
import os
import json
import re
from typing import Dict, List, Optional

# Configure logger
logger = logging.getLogger('error_tracker')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs/command_deck.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ErrorTracker:
    def __init__(self, dashboard=None):
        self.dashboard = dashboard
        self.error_logs = []
        self.log_limit = 1000  # Store this many log entries
        self.log_files = {
            "friday_system": "logs/friday_system.log",
            "core": "logs/core.log",
            "memory": "logs/memory.log",
            "llm": "logs/llm.log",
            "intent": "logs/intent.log",
            "internet_access": "logs/internet_access.log",
            "security": "logs/security.log",
            "personality": "logs/personality.log",
            "api_usage": "logs/api_usage.log"
        }
        self.file_positions = {}  # Track file positions
        self.running = False
        self.update_interval = 10  # seconds
        self.last_update = datetime.datetime.now()
        
        logger.info("Error Tracker initialized")
        
        if dashboard:
            dashboard.register_panel("error_tracker", self.render_error_panel)
            dashboard.register_component("error_tracker", self)
    
    async def start_monitoring(self):
        """Start monitoring log files for errors in the background"""
        self.running = True
        logger.info("Starting error log monitoring")
        
        # Initialize file positions
        for log_name, log_path in self.log_files.items():
            if os.path.exists(log_path):
                self.file_positions[log_name] = os.path.getsize(log_path)
            else:
                self.file_positions[log_name] = 0
        
        # Periodic check for new errors
        while self.running:
            try:
                await self.check_log_files()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error checking log files: {e}")
                await asyncio.sleep(self.update_interval * 2)
    
    async def check_log_files(self):
        """Check log files for new errors"""
        new_errors = 0
        
        for log_name, log_path in self.log_files.items():
            if not os.path.exists(log_path):
                continue
                
            current_size = os.path.getsize(log_path)
            last_position = self.file_positions.get(log_name, 0)
            
            # File was truncated or is new
            if current_size < last_position:
                last_position = 0
            
            # If file has grown, check for new errors
            if current_size > last_position:
                try:
                    with open(log_path, 'r') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        
                        for line in new_lines:
                            if "ERROR" in line or "CRITICAL" in line or "WARNING" in line:
                                self._process_error_line(log_name, line)
                                new_errors += 1
                    
                    # Update file position
                    self.file_positions[log_name] = current_size
                except Exception as e:
                    logger.error(f"Error reading log file {log_path}: {e}")
        
        if new_errors > 0:
            logger.info(f"Found {new_errors} new errors in log files")
            
        self.last_update = datetime.datetime.now()
        return new_errors
    
    def _process_error_line(self, log_name, line):
        """Process an error log line and add it to the tracker"""
        try:
            # Extract timestamp, level, and message
            # Example format: 2025-05-07 13:35:55,675 - memory_system - WARNING - Could not connect to Redis
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                timestamp_str, component, level, message = parts
                
                # Parse timestamp
                try:
                    timestamp = datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                except ValueError:
                    timestamp = datetime.datetime.now()
                
                # Determine severity
                severity = "error"
                if "WARNING" in level:
                    severity = "warning"
                elif "CRITICAL" in level:
                    severity = "critical"
                
                # Create error log entry
                error_entry = {
                    "timestamp": timestamp.isoformat(),
                    "log_file": log_name,
                    "component": component.strip(),
                    "severity": severity,
                    "message": message.strip(),
                    "raw_line": line.strip()
                }
                
                self.error_logs.append(error_entry)
                
                # Trim logs if needed
                if len(self.error_logs) > self.log_limit:
                    self.error_logs = self.error_logs[-self.log_limit:]
                
                # Update dashboard if available
                if self.dashboard:
                    if severity == "critical":
                        self.dashboard.update_component_status("error_tracker", "critical", message.strip())
                    elif severity == "error":
                        self.dashboard.update_component_status("error_tracker", "error", message.strip())
                    else:
                        self.dashboard.update_component_status("error_tracker", "warning", message.strip())
            else:
                # Fallback for lines not matching expected format
                error_entry = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "log_file": log_name,
                    "component": "unknown",
                    "severity": "error" if "ERROR" in line else "warning",
                    "message": line.strip(),
                    "raw_line": line.strip()
                }
                
                self.error_logs.append(error_entry)
                
        except Exception as e:
            logger.error(f"Error processing log line: {e}")
    
    async def render_error_panel(self):
        """Render the error tracking panel for the dashboard"""
        try:
            # Check for new errors
            if (datetime.datetime.now() - self.last_update).total_seconds() > self.update_interval * 2:
                await self.check_log_files()
            
            # Count errors by severity
            error_counts = {"critical": 0, "error": 0, "warning": 0}
            component_counts = {}
            
            for error in self.error_logs:
                # Count by severity
                severity = error.get("severity", "error")
                if severity in error_counts:
                    error_counts[severity] += 1
                
                # Count by component
                component = error.get("component", "unknown")
                if component in component_counts:
                    component_counts[component] += 1
                else:
                    component_counts[component] = 1
            
            # Get recent errors, sorted by timestamp (newest first)
            recent_errors = sorted(
                self.error_logs,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:30]  # Last 30 errors
            
            # Create the panel data
            panel_data = {
                "title": "Error Tracking",
                "timestamp": datetime.datetime.now().isoformat(),
                "error_counts": error_counts,
                "component_counts": component_counts,
                "recent_errors": recent_errors,
                "monitored_logs": list(self.log_files.keys())
            }
            
            return panel_data
        except Exception as e:
            logger.error(f"Error rendering error panel: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def get_errors(self, severity=None, component=None, log_file=None, limit=50):
        """Get filtered error logs"""
        filtered_errors = self.error_logs
        
        # Apply filters
        if severity:
            filtered_errors = [e for e in filtered_errors if e.get("severity") == severity]
        
        if component:
            filtered_errors = [e for e in filtered_errors if e.get("component") == component]
        
        if log_file:
            filtered_errors = [e for e in filtered_errors if e.get("log_file") == log_file]
        
        # Return limited results, most recent first
        return sorted(filtered_errors, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    
    async def get_status(self):
        """Get component status for dashboard"""
        try:
            # Check if monitoring is active
            if (datetime.datetime.now() - self.last_update).total_seconds() > self.update_interval * 3:
                return {
                    "status": "stalled",
                    "error": "Error log monitoring has stalled"
                }
            
            # Count recent critical errors
            critical_count = len([e for e in self.error_logs[-20:] if e.get("severity") == "critical"])
            error_count = len([e for e in self.error_logs[-20:] if e.get("severity") == "error"])
            
            if critical_count > 0:
                return {
                    "status": "critical",
                    "warning": f"{critical_count} recent critical errors"
                }
            elif error_count > 5:
                return {
                    "status": "error",
                    "warning": f"{error_count} recent errors"
                }
            
            return {
                "status": "running",
                "last_update": self.last_update.isoformat(),
                "recent_errors": error_count
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_diagnostics(self):
        """Run diagnostics on the error tracking system"""
        try:
            # Check log files immediately
            new_errors = await self.check_log_files()
            
            # Check file access
            file_access = {}
            for log_name, log_path in self.log_files.items():
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r') as f:
                            f.read(1)  # Try to read a byte
                        file_access[log_name] = "accessible"
                    except Exception as e:
                        file_access[log_name] = f"error: {str(e)}"
                else:
                    file_access[log_name] = "file not found"
            
            # Analyze error patterns
            error_patterns = {}
            component_issues = {}
            
            for error in self.error_logs[-100:]:  # Analyze last 100 errors
                message = error.get("message", "")
                component = error.get("component", "unknown")
                
                # Extract error type (simplified)
                error_type = "unknown"
                if ":" in message:
                    error_type = message.split(":", 1)[0].strip()
                
                if error_type in error_patterns:
                    error_patterns[error_type] += 1
                else:
                    error_patterns[error_type] = 1
                
                # Track components with issues
                if component in component_issues:
                    component_issues[component] += 1
                else:
                    component_issues[component] = 1
            
            # Sort by frequency
            sorted_patterns = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)
            sorted_components = sorted(component_issues.items(), key=lambda x: x[1], reverse=True)
            
            # Check for issues
            issues = []
            warnings = []
            
            # Check if any log files are missing
            missing_logs = [log_name for log_name, status in file_access.items() if status == "file not found"]
            if missing_logs:
                warnings.append(f"Missing log files: {', '.join(missing_logs)}")
            
            # Check if any critical errors exist
            critical_errors = [e for e in self.error_logs[-50:] if e.get("severity") == "critical"]
            if critical_errors:
                issues.append(f"Found {len(critical_errors)} recent critical errors")
            
            # Check for repeated error patterns
            if sorted_patterns and sorted_patterns[0][1] > 10:
                error_type, count = sorted_patterns[0]
                issues.append(f"Recurring error pattern '{error_type}' ({count} occurrences)")
            
            # Check for components with many errors
            if sorted_components and sorted_components[0][1] > 15:
                component, count = sorted_components[0]
                issues.append(f"Component '{component}' has {count} recent errors")
            
            return {
                "status": "critical" if issues else "warning" if warnings else "healthy",
                "issues": issues,
                "warnings": warnings,
                "file_access": file_access,
                "error_patterns": dict(sorted_patterns[:5]),
                "component_issues": dict(sorted_components[:5]),
                "new_errors": new_errors
            }
        except Exception as e:
            logger.error(f"Error running error tracker diagnostics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def restart(self):
        """Restart the error tracker"""
        try:
            self.running = False
            await asyncio.sleep(1)
            
            # Reset file positions
            self.file_positions = {}
            
            # Reset logs
            self.error_logs = []
            
            # Restart
            self.running = True
            asyncio.create_task(self.start_monitoring())
            
            return {
                "success": True,
                "message": "Error tracker restarted"
            }
        except Exception as e:
            logger.error(f"Error restarting error tracker: {e}")
            return {
                "success": False,
                "error": str(e)
            }