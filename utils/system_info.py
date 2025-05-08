"""
Friday AI - System Information Provider

This module provides access to system information from Windows,
including CPU/RAM/disk usage, date/time, weather, and other system metrics.
"""

import os
import sys
import time
import json
import logging
import asyncio
import datetime
import platform
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("system_info")

# Import platform-specific modules
try:
    import psutil
    import wmi
    import win32api
    import win32con
    import win32process
except ImportError as e:
    logger.warning(f"Could not import system monitoring module: {e}")
    logger.warning("Run 'pip install psutil wmi pywin32' to enable full system monitoring")

class SystemInfoProvider:
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the system information provider.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.wmi_client = None
        self.weather_cache = {"timestamp": 0, "data": None}
        self.weather_cache_ttl = 3600  # 1 hour in seconds
        
        # Initialize WMI client if available
        try:
            self.wmi_client = wmi.WMI()
            logger.info("WMI client initialized")
        except Exception as e:
            logger.warning(f"Could not initialize WMI client: {e}")
            
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "weather_api_key": None,
            "weather_location": None,
            "update_interval": 5,  # seconds
            "monitor_processes": True,
            "monitor_startup_items": True,
            "monitor_sensors": True,
            "monitor_network": True
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    
                # Update default config with loaded values
                for key, value in loaded_config.items():
                    default_config[key] = value
            except Exception as e:
                logger.error(f"Error loading system info config: {e}")
                
        return default_config
    
    async def get_basic_info(self) -> Dict[str, Any]:
        """Get basic system information.
        
        Returns:
            Dict with basic system information
        """
        info = {
            "platform": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": time.tzname,
            "uptime": self.get_uptime()
        }
        
        return info
    
    def get_uptime(self) -> str:
        """Get system uptime in a human-readable format.
        
        Returns:
            Uptime string
        """
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_days = int(uptime_seconds // 86400)
            uptime_hours = int((uptime_seconds % 86400) // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            
            if uptime_days > 0:
                return f"{uptime_days}d {uptime_hours}h {uptime_minutes}m"
            elif uptime_hours > 0:
                return f"{uptime_hours}h {uptime_minutes}m"
            else:
                return f"{uptime_minutes}m"
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
            return "Unknown"
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics.
        
        Returns:
            Dict with CPU, memory, and disk usage
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = self._format_bytes(memory.used)
            memory_total = self._format_bytes(memory.total)
            
            # Disk usage for C: drive
            disk = psutil.disk_usage('C:\\')
            disk_percent = disk.percent
            disk_used = self._format_bytes(disk.used)
            disk_total = self._format_bytes(disk.total)
            
            # Network usage
            if self.config.get("monitor_network", True):
                network_before = psutil.net_io_counters()
                await asyncio.sleep(0.5)
                network_after = psutil.net_io_counters()
                
                network_sent = self._format_bytes((network_after.bytes_sent - network_before.bytes_sent) * 2)
                network_recv = self._format_bytes((network_after.bytes_recv - network_before.bytes_recv) * 2)
                network = {
                    "sent_per_sec": network_sent,
                    "recv_per_sec": network_recv,
                    "total_sent": self._format_bytes(network_after.bytes_sent),
                    "total_recv": self._format_bytes(network_after.bytes_recv)
                }
            else:
                network = None
                
            # Battery info if available
            battery = {}
            if hasattr(psutil, "sensors_battery"):
                battery_info = psutil.sensors_battery()
                if battery_info:
                    battery = {
                        "percent": battery_info.percent,
                        "power_plugged": battery_info.power_plugged,
                        "time_left": self._format_seconds(battery_info.secsleft) if battery_info.secsleft != -1 else "Unknown"
                    }
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent
                },
                "memory": {
                    "usage_percent": memory_percent,
                    "used": memory_used,
                    "total": memory_total
                },
                "disk": {
                    "usage_percent": disk_percent,
                    "used": disk_used,
                    "total": disk_total
                },
                "network": network,
                "battery": battery if battery else None
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                "cpu": {"usage_percent": 0},
                "memory": {"usage_percent": 0},
                "disk": {"usage_percent": 0},
                "error": str(e)
            }
    
    async def get_top_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top processes by CPU usage.
        
        Args:
            limit: Maximum number of processes to return
            
        Returns:
            List of process information dictionaries
        """
        if not self.config.get("monitor_processes", True):
            return []
            
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    # Get CPU usage, updating it if it's 0
                    if pinfo['cpu_percent'] == 0:
                        proc.cpu_percent(interval=0.1)
                    processes.append(pinfo)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by CPU usage and get top processes
            top_cpu = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:limit]
            
            # Sort by memory usage and get top processes
            top_memory = sorted(processes, key=lambda p: p['memory_percent'], reverse=True)[:limit]
            
            return {
                "top_cpu": [{
                    "pid": p["pid"],
                    "name": p["name"],
                    "cpu_percent": p["cpu_percent"]
                } for p in top_cpu],
                "top_memory": [{
                    "pid": p["pid"],
                    "name": p["name"],
                    "memory_percent": p["memory_percent"]
                } for p in top_memory]
            }
        except Exception as e:
            logger.error(f"Error getting top processes: {e}")
            return []
            
    async def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information.
        
        Returns:
            Dict with GPU information
        """
        try:
            if not self.wmi_client:
                return {"error": "WMI client not available"}
                
            gpu_info = []
            for gpu in self.wmi_client.Win32_VideoController():
                gpu_info.append({
                    "name": gpu.Name,
                    "driver_version": gpu.DriverVersion,
                    "adapter_ram": self._format_bytes(int(gpu.AdapterRAM)) if hasattr(gpu, 'AdapterRAM') and gpu.AdapterRAM else "Unknown"
                })
                
            return {"gpus": gpu_info}
        except Exception as e:
            logger.error(f"Error getting GPU info: {e}")
            return {"error": str(e)}
            
    async def get_network_info(self) -> Dict[str, Any]:
        """Get network information.
        
        Returns:
            Dict with network information
        """
        if not self.config.get("monitor_network", True):
            return {"error": "Network monitoring disabled"}
            
        try:
            network_info = []
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info = {"name": interface, "addresses": []}
                
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        interface_info["addresses"].append({
                            "type": "IPv4",
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
                    elif addr.family == socket.AF_INET6:
                        interface_info["addresses"].append({
                            "type": "IPv6",
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
                        
                # Get stats if available
                try:
                    stats = psutil.net_if_stats()[interface]
                    interface_info["speed"] = f"{stats.speed} Mbps" if stats.speed > 0 else "Unknown"
                    interface_info["mtu"] = stats.mtu
                    interface_info["up"] = stats.isup
                except (KeyError, AttributeError):
                    pass
                    
                network_info.append(interface_info)
                
            return {"interfaces": network_info}
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            return {"error": str(e)}
            
    async def get_date_time_info(self) -> Dict[str, Any]:
        """Get detailed date and time information.
        
        Returns:
            Dict with date and time information
        """
        now = datetime.datetime.now()
        return {
            "timestamp": now.timestamp(),
            "iso_format": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "day_of_month": now.day,
            "day_of_year": now.timetuple().tm_yday,
            "month": now.strftime("%B"),
            "year": now.year,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "timezone": time.tzname,
            "is_dst": time.localtime().tm_isdst > 0
        }
        
    async def get_weather(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get current weather information.
        
        Args:
            force_refresh: Whether to force a refresh of cached data
            
        Returns:
            Dict with weather information
        """
        api_key = self.config.get("weather_api_key")
        location = self.config.get("weather_location")
        
        if not api_key or not location:
            return {"error": "Weather API key or location not configured"}
            
        # Check cache
        now = time.time()
        if not force_refresh and self.weather_cache["data"] and (now - self.weather_cache["timestamp"]) < self.weather_cache_ttl:
            return self.weather_cache["data"]
            
        # Use OpenWeatherMap API
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            
            # Use aiohttp to make the request
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Format the data
                        weather = {
                            "location": f"{data['name']}, {data.get('sys', {}).get('country', '')}",
                            "temperature": {
                                "current": data["main"]["temp"],
                                "feels_like": data["main"]["feels_like"],
                                "min": data["main"]["temp_min"],
                                "max": data["main"]["temp_max"],
                                "unit": "°C"
                            },
                            "condition": {
                                "main": data["weather"][0]["main"],
                                "description": data["weather"][0]["description"],
                                "icon": data["weather"][0]["icon"]
                            },
                            "humidity": data["main"]["humidity"],
                            "pressure": data["main"]["pressure"],
                            "wind": {
                                "speed": data["wind"]["speed"],
                                "direction": data["wind"].get("deg", 0)
                            },
                            "clouds": data.get("clouds", {}).get("all", 0),
                            "sunrise": datetime.datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                            "sunset": datetime.datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
                            "timestamp": now
                        }
                        
                        # Update cache
                        self.weather_cache = {
                            "timestamp": now,
                            "data": weather
                        }
                        
                        return weather
                    else:
                        return {"error": f"Weather API returned status {response.status}"}
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return {"error": str(e)}
            
    def get_display_info(self) -> Dict[str, Any]:
        """Get information about display settings.
        
        Returns:
            Dict with display information
        """
        try:
            if sys.platform != 'win32':
                return {"error": "Not supported on this platform"}
                
            # Use win32api to get display information
            displays = []
            
            # Get the primary display settings
            try:
                settings = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
                displays.append({
                    "width": settings.PelsWidth,
                    "height": settings.PelsHeight,
                    "frequency": settings.DisplayFrequency,
                    "bits_per_pixel": settings.BitsPerPel,
                    "is_primary": True
                })
            except Exception as e:
                logger.error(f"Error getting primary display settings: {e}")
                
            # Use wmi to get all displays
            if self.wmi_client:
                for monitor in self.wmi_client.Win32_DesktopMonitor():
                    displays.append({
                        "name": monitor.Name,
                        "device_id": monitor.DeviceID,
                        "status": monitor.Status
                    })
                    
            return {"displays": displays}
        except Exception as e:
            logger.error(f"Error getting display info: {e}")
            return {"error": str(e)}
            
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string.
        
        Args:
            bytes_val: Bytes value
            
        Returns:
            Formatted string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024 or unit == 'TB':
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
            
    def _format_seconds(self, seconds: int) -> str:
        """Format seconds to human-readable string.
        
        Args:
            seconds: Seconds value
            
        Returns:
            Formatted string
        """
        if seconds < 0:
            return "Unknown"
            
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        else:
            return f"{int(minutes)}m {int(seconds)}s"