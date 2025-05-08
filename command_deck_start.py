"""
Friday AI - Command Deck Launcher
Standalone launcher for the Command Deck dashboard
"""

import os
import sys
import asyncio
import logging
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/command_deck.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Ensure the command_deck directory exists
os.makedirs('command_deck', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Import Command Deck components
try:
    from command_deck.dashboard_interface import CommandDeckDashboard
    from command_deck.system_metrics import SystemMetricsMonitor
    from command_deck.memory_access_logs import MemoryAccessMonitor
    from command_deck.error_tracker import ErrorTracker
    command_deck_available = True
except ImportError as e:
    logging.error(f"Command Deck modules not available: {e}")
    command_deck_available = False

# Create a simple HTTP handler to serve the Command Deck UI
class CommandDeckHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            # Serve the Command Deck HTML
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            with open('ui/command_deck.html', 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/api/system_info':
            # Basic system info response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            import json
            import platform
            import psutil
            
            memory = psutil.virtual_memory()
            response = {
                "status": "success",
                "data": {
                    "system": {
                        "platform": platform.platform(),
                        "python_version": platform.python_version(),
                        "cpu_count": os.cpu_count(),
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_total": memory.total,
                        "memory_available": memory.available,
                        "memory_percent": memory.percent
                    },
                    "friday": {
                        "status": "running",
                        "component_status": {}
                    }
                }
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            # Try to serve static files
            super().do_GET()
    
    def log_message(self, format, *args):
        """Override to use the logger instead of stderr"""
        logging.info("%s - - [%s] %s" % (self.address_string(),
                                          self.log_date_time_string(),
                                          format % args))

async def initialize_dashboard():
    """Initialize the command deck dashboard"""
    if not command_deck_available:
        logging.error("Command Deck modules could not be imported")
        return None, None, None, None
    
    try:
        # Create dashboard instance
        dashboard = CommandDeckDashboard()
        
        # Initialize components
        metrics_monitor = SystemMetricsMonitor(dashboard)
        error_tracker = ErrorTracker(dashboard)
        memory_monitor = MemoryAccessMonitor(dashboard)
        
        # Start component monitoring
        metrics_monitor_task = asyncio.create_task(metrics_monitor.start_monitoring())
        error_tracker_task = asyncio.create_task(error_tracker.start_monitoring())
        memory_monitor_task = asyncio.create_task(memory_monitor.start_monitoring())
        
        logging.info("Command Deck dashboard initialized successfully")
        return dashboard, metrics_monitor, error_tracker, memory_monitor
    except Exception as e:
        logging.error(f"Error initializing dashboard: {e}")
        return None, None, None, None

async def main():
    """Main entry point for the Command Deck launcher"""
    print("\nFriday AI - Command Deck Launcher")
    print("--------------------------------\n")
    
    # Initialize the dashboard
    dashboard, metrics_monitor, error_tracker, memory_monitor = await initialize_dashboard()
    
    if not dashboard:
        print("Failed to initialize Command Deck. Check logs for details.")
        return
    
    # Set up HTTP server to serve the Command Deck UI
    port = 5050  # Use a different port to avoid conflict with Friday's port
    httpd = HTTPServer(('localhost', port), CommandDeckHandler)
    
    # Start HTTP server in a separate thread
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    
    print(f"Command Deck UI available at: http://localhost:{port}")
    
    # Open web browser
    webbrowser.open(f'http://localhost:{port}')
    
    print("Server started. Press Ctrl+C to stop.")
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutdown requested. Stopping server...")
    except Exception as e:
        logging.error(f"Error running Command Deck: {e}")
    finally:
        httpd.shutdown()
        print("Server stopped. Goodbye!")

# Make the dashboard module available for import
dashboard = None
metrics_monitor = None
error_tracker = None
memory_monitor = None

if __name__ == "__main__":
    asyncio.run(main())