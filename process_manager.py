"""
Friday AI - Process Manager

This module handles starting and stopping the Friday AI system and UI.
"""

import os
import sys
import time
import logging
import subprocess
import signal
import asyncio
import json
import requests
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/process_manager.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger()

class FridayProcessManager:
    def __init__(self):
        """Initialize the process manager."""
        self.friday_process = None
        self.ui_process = None
        self.config = self._load_config()
        
    def _load_config(self):
        """Load configuration settings."""
        default_config = {
            "core": {
                "startup_timeout": 10,  # seconds to wait for core to start
                "script_path": "main.py",
                "config_path": None
            },
            "ui": {
                "startup_timeout": 10,  # seconds to wait for UI to start
                "path": ".ui/electron_app",
                "command": "npm start",
                "auto_start": True
            },
            "http": {
                "port": 5000,
                "host": "localhost",
                "status_endpoint": "/status"
            }
        }
        
        # Try to load config from file
        config_path = "configs/system_config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    
                # Merge configs
                for section, values in loaded_config.items():
                    if section in default_config:
                        default_config[section].update(values)
                    else:
                        default_config[section] = values
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                
        return default_config
        
    async def start_friday(self):
        """Start the Friday AI system.
        
        Returns:
            bool: True if startup was successful
        """
        logger.info("Starting Friday AI system...")
        
        # Make sure the logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Start the core process
        core_config = self.config["core"]
        script_path = core_config["script_path"]
        config_path = core_config["config_path"]
        
        cmd = [sys.executable, script_path]
        if config_path:
            cmd.extend(["--config", config_path])
            
        try:
            # Start the process
            self.friday_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"Friday process started with PID {self.friday_process.pid}")
            
            # Wait for HTTP server to start
            http_config = self.config["http"]
            startup_timeout = core_config["startup_timeout"]
            success = await self._wait_for_http_server(
                http_config["host"],
                http_config["port"],
                http_config["status_endpoint"],
                startup_timeout
            )
            
            if not success:
                logger.error("Failed to start Friday AI system: HTTP server did not respond")
                self.stop_friday()
                return False
                
            logger.info("Friday AI system started successfully")
            
            # Start UI if configured
            ui_config = self.config["ui"]
            if ui_config["auto_start"]:
                await self.start_ui()
            
            return True
        except Exception as e:
            logger.error(f"Failed to start Friday AI system: {e}")
            self.stop_friday()
            return False
            
    async def start_ui(self):
        """Start the Friday UI.
        
        Returns:
            bool: True if startup was successful
        """
        if self.ui_process:
            logger.info("UI already running")
            return True
            
        logger.info("Starting Friday UI...")
        
        # Get UI configuration
        ui_config = self.config["ui"]
        ui_path = ui_config["path"]
        ui_command = ui_config["command"].split()
        
        # Check if directory exists
        if not os.path.exists(ui_path):
            logger.error(f"UI directory not found: {ui_path}")
            return False
            
        try:
            # Start the process
            self.ui_process = subprocess.Popen(
                ui_command,
                cwd=ui_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"UI process started with PID {self.ui_process.pid}")
            
            # Wait a bit for the UI to start
            startup_timeout = ui_config["startup_timeout"]
            for _ in range(startup_timeout):
                if self.ui_process.poll() is not None:
                    # Process ended
                    logger.error(f"UI process exited with code {self.ui_process.returncode}")
                    return False
                    
                await asyncio.sleep(1)
                
            # Start output monitoring
            self._start_output_monitoring()
            
            logger.info("UI started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start UI: {e}")
            return False
            
    def stop_friday(self):
        """Stop the Friday AI system."""
        # Stop UI first
        self.stop_ui()
        
        # Then stop Friday core
        if self.friday_process:
            logger.info("Stopping Friday AI system...")
            
            # Send termination signal
            try:
                if os.name == 'nt':  # Windows
                    self.friday_process.terminate()
                else:  # Unix/Linux
                    os.kill(self.friday_process.pid, signal.SIGTERM)
                    
                # Wait for process to end
                self.friday_process.wait(timeout=5)
                logger.info("Friday AI system stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Friday process did not terminate, forcing...")
                try:
                    if os.name == 'nt':  # Windows
                        self.friday_process.kill()
                    else:  # Unix/Linux
                        os.kill(self.friday_process.pid, signal.SIGKILL)
                    logger.info("Friday AI system forcibly stopped")
                except Exception as e:
                    logger.error(f"Error stopping Friday process: {e}")
            except Exception as e:
                logger.error(f"Error stopping Friday process: {e}")
                
            self.friday_process = None
            
    def stop_ui(self):
        """Stop the Friday UI."""
        if self.ui_process:
            logger.info("Stopping Friday UI...")
            
            # Send termination signal
            try:
                if os.name == 'nt':  # Windows
                    self.ui_process.terminate()
                else:  # Unix/Linux
                    os.kill(self.ui_process.pid, signal.SIGTERM)
                    
                # Wait for process to end
                self.ui_process.wait(timeout=5)
                logger.info("Friday UI stopped")
            except subprocess.TimeoutExpired:
                logger.warning("UI process did not terminate, forcing...")
                try:
                    if os.name == 'nt':  # Windows
                        self.ui_process.kill()
                    else:  # Unix/Linux
                        os.kill(self.ui_process.pid, signal.SIGKILL)
                    logger.info("Friday UI forcibly stopped")
                except Exception as e:
                    logger.error(f"Error stopping UI process: {e}")
            except Exception as e:
                logger.error(f"Error stopping UI process: {e}")
                
            self.ui_process = None
            
    def _start_output_monitoring(self):
        """Start monitoring process output in background threads."""
        # Monitor Friday process output
        if self.friday_process:
            def monitor_friday_output():
                while self.friday_process and self.friday_process.poll() is None:
                    line = self.friday_process.stdout.readline()
                    if line:
                        print(f"[Friday] {line.strip()}")
                
            def monitor_friday_errors():
                while self.friday_process and self.friday_process.poll() is None:
                    line = self.friday_process.stderr.readline()
                    if line:
                        print(f"[Friday ERROR] {line.strip()}")
                
            # Start monitoring threads
            threading.Thread(target=monitor_friday_output, daemon=True).start()
            threading.Thread(target=monitor_friday_errors, daemon=True).start()
        
        # Monitor UI process output
        if self.ui_process:
            def monitor_ui_output():
                while self.ui_process and self.ui_process.poll() is None:
                    line = self.ui_process.stdout.readline()
                    if line:
                        print(f"[UI] {line.strip()}")
                
            def monitor_ui_errors():
                while self.ui_process and self.ui_process.poll() is None:
                    line = self.ui_process.stderr.readline()
                    if line:
                        print(f"[UI ERROR] {line.strip()}")
                
            # Start monitoring threads
            threading.Thread(target=monitor_ui_output, daemon=True).start()
            threading.Thread(target=monitor_ui_errors, daemon=True).start()
            
    async def _wait_for_http_server(self, host, port, status_endpoint, timeout):
        """Wait for HTTP server to be available.
        
        Args:
            host: Server hostname
            port: Server port
            status_endpoint: Endpoint to check
            timeout: Timeout in seconds
            
        Returns:
            bool: True if server is available
        """
        url = f"http://{host}:{port}{status_endpoint}"
        logger.info(f"Waiting for HTTP server at {url}...")
        
        for i in range(timeout):
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    logger.info(f"HTTP server available after {i+1} seconds")
                    return True
            except requests.exceptions.RequestException:
                pass
                
            await asyncio.sleep(1)
            
        return False

# Add threading import
import threading

# Main entry point
async def main():
    """Main entry point for the process manager."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Friday AI Process Manager")
    parser.add_argument("--ui-only", action="store_true", help="Start only the UI")
    parser.add_argument("--core-only", action="store_true", help="Start only the core system")
    args = parser.parse_args()
    
    # Create process manager
    manager = FridayProcessManager()
    
    try:
        if args.ui_only:
            # Start only the UI
            success = await manager.start_ui()
            if success:
                # Keep running until interrupted
                print("Press Ctrl+C to exit...")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
        elif args.core_only:
            # Start only the core system
            success = await manager.start_friday()
            if success:
                # Keep running until interrupted
                print("Press Ctrl+C to exit...")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
        else:
            # Start both
            success = await manager.start_friday()
            if success:
                # Keep running until interrupted
                print("Press Ctrl+C to exit...")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
    finally:
        # Stop everything when exiting
        manager.stop_friday()
        print("Friday AI system shut down")

if __name__ == "__main__":
    asyncio.run(main())