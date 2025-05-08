# command_deck/system_metrics.py
import asyncio
import datetime
import logging
import os
import platform
import psutil
import json
from typing import Dict, List, Optional

# Configure logger
logger = logging.getLogger('system_metrics')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs/command_deck.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class SystemMetricsMonitor:
    def __init__(self, dashboard=None):
        self.dashboard = dashboard
        self.metrics_history = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        }
        self.history_limit = 100  # Store this many data points
        self.last_update = datetime.datetime.now()
        self.running = False
        self.update_interval = 5  # seconds
        logger.info("System Metrics Monitor initialized")
        
        if dashboard:
            dashboard.register_panel("system_metrics", self.render_metrics_panel)
            dashboard.register_component("system_metrics", self)
    
    async def start_monitoring(self):
        """Start collecting system metrics in the background"""
        self.running = True
        logger.info("Starting system metrics collection")
        
        while self.running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(self.update_interval * 2)  # Longer sleep on error
    
    async def collect_metrics(self):
        """Collect current system metrics"""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_used_percent = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_used_percent = disk.percent
            
            # Get network usage (simplified)
            net_io = psutil.net_io_counters()
            net_sent = net_io.bytes_sent
            net_recv = net_io.bytes_recv
            
            # Get process info for Friday components
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            process_cpu = process.cpu_percent(interval=0.1)
            
            # Create metrics record
            timestamp = datetime.datetime.now()
            metrics = {
                "timestamp": timestamp.isoformat(),
                "cpu": {
                    "total_percent": cpu_percent,
                    "process_percent": process_cpu
                },
                "memory": {
                    "total_percent": memory_used_percent,
                    "process_mb": process_memory,
                    "available_mb": memory.available / (1024 * 1024)
                },
                "disk": {
                    "percent": disk_used_percent,
                    "free_gb": disk.free / (1024 * 1024 * 1024)
                },
                "network": {
                    "bytes_sent": net_sent,
                    "bytes_recv": net_recv
                }
            }
            
            # Add to history
            self._add_to_history("cpu", {
                "timestamp": timestamp.isoformat(),
                "total_percent": cpu_percent,
                "process_percent": process_cpu
            })
            
            self._add_to_history("memory", {
                "timestamp": timestamp.isoformat(),
                "total_percent": memory_used_percent,
                "process_mb": process_memory
            })
            
            self._add_to_history("disk", {
                "timestamp": timestamp.isoformat(),
                "percent": disk_used_percent
            })
            
            self._add_to_history("network", {
                "timestamp": timestamp.isoformat(),
                "bytes_sent": net_sent,
                "bytes_recv": net_recv
            })
            
            # Update dashboard if necessary
            if self.dashboard:
                self.dashboard.update_component_status("system_metrics", "running")
            
            self.last_update = timestamp
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            if self.dashboard:
                self.dashboard.update_component_status("system_metrics", "error", str(e))
            raise
    
    def _add_to_history(self, metric_type: str, data: Dict):
        """Add a data point to the metrics history"""
        self.metrics_history[metric_type].append(data)
        
        # Trim history if needed
        if len(self.metrics_history[metric_type]) > self.history_limit:
            self.metrics_history[metric_type] = self.metrics_history[metric_type][-self.history_limit:]
    
    async def render_metrics_panel(self):
        """Render the system metrics panel for the dashboard"""
        try:
            # Get latest metrics if needed
            if (datetime.datetime.now() - self.last_update).total_seconds() > self.update_interval * 2:
                await self.collect_metrics()
            
            # Create the panel data
            panel_data = {
                "title": "System Resources",
                "timestamp": datetime.datetime.now().isoformat(),
                "metrics": {
                    "current": {
                        "cpu": self.metrics_history["cpu"][-1] if self.metrics_history["cpu"] else None,
                        "memory": self.metrics_history["memory"][-1] if self.metrics_history["memory"] else None,
                        "disk": self.metrics_history["disk"][-1] if self.metrics_history["disk"] else None,
                        "network": self.metrics_history["network"][-1] if self.metrics_history["network"] else None
                    },
                    "history": {
                        "cpu": self.metrics_history["cpu"][-20:],  # Last 20 points
                        "memory": self.metrics_history["memory"][-20:],
                        "disk": self.metrics_history["disk"][-20:],
                        "network": self.metrics_history["network"][-20:]
                    }
                },
                "system_info": {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "processors": os.cpu_count(),
                    "hostname": platform.node()
                }
            }
            
            return panel_data
        except Exception as e:
            logger.error(f"Error rendering metrics panel: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def get_status(self):
        """Get component status for dashboard"""
        try:
            # Check if metrics are being collected
            if (datetime.datetime.now() - self.last_update).total_seconds() > self.update_interval * 3:
                return {
                    "status": "stalled",
                    "error": "Metrics collection has stalled"
                }
            
            return {
                "status": "running",
                "last_update": self.last_update.isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_diagnostics(self):
        """Run diagnostics on the system metrics monitor"""
        try:
            # Collect metrics immediately
            metrics = await self.collect_metrics()
            
            # Check for potential issues
            issues = []
            warnings = []
            
            # Check CPU usage
            if metrics["cpu"]["total_percent"] > 90:
                issues.append(f"CPU usage is very high: {metrics['cpu']['total_percent']}%")
            elif metrics["cpu"]["total_percent"] > 75:
                warnings.append(f"CPU usage is elevated: {metrics['cpu']['total_percent']}%")
            
            # Check memory usage
            if metrics["memory"]["total_percent"] > 90:
                issues.append(f"Memory usage is very high: {metrics['memory']['total_percent']}%")
            elif metrics["memory"]["total_percent"] > 75:
                warnings.append(f"Memory usage is elevated: {metrics['memory']['total_percent']}%")
            
            # Check disk usage
            if metrics["disk"]["percent"] > 90:
                issues.append(f"Disk usage is very high: {metrics['disk']['percent']}%")
            elif metrics["disk"]["percent"] > 75:
                warnings.append(f"Disk usage is elevated: {metrics['disk']['percent']}%")
            
            # Check Friday process memory
            if metrics["memory"]["process_mb"] > 1000:  # 1GB
                warnings.append(f"Friday is using {metrics['memory']['process_mb']:.1f}MB of RAM")
            
            return {
                "status": "critical" if issues else "warning" if warnings else "healthy",
                "issues": issues,
                "warnings": warnings,
                "metrics": metrics
            }
        except Exception as e:
            logger.error(f"Error running diagnostics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def restart(self):
        """Restart the metrics monitor"""
        try:
            self.running = False
            await asyncio.sleep(1)
            
            # Clear history
            for metric in self.metrics_history:
                self.metrics_history[metric] = []
            
            # Restart
            self.running = True
            asyncio.create_task(self.start_monitoring())
            
            return {
                "success": True,
                "message": "System metrics monitor restarted"
            }
        except Exception as e:
            logger.error(f"Error restarting metrics monitor: {e}")
            return {
                "success": False,
                "error": str(e)
            }