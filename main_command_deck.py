# main_command_deck.py
import asyncio
import logging
import os
import sys
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/command_deck.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import command deck components
from command_deck import (
    CommandDeckDashboard,
    SystemMetricsMonitor,
    MemoryAccessMonitor,
    ErrorTracker
)

# Import existing system components
sys.path.append('.')  # Ensure current directory is in path
try:
    from core import memory_system, llm_interface, security_monitor
    from network import internet_controller
    from ui import http_controller
except ImportError as e:
    logger.error(f"Error importing system components: {e}")
    logger.info("Command Deck can still run in standalone mode")

async def initialize_command_deck():
    """Initialize the Command Deck and its components"""
    logger.info("Initializing Command Deck...")
    
    # Create dashboard
    dashboard = CommandDeckDashboard()
    
    # Initialize components
    metrics_monitor = SystemMetricsMonitor(dashboard)
    error_tracker = ErrorTracker(dashboard)
    
    # Try to connect to the memory system
    memory_monitor = None
    try:
        if 'memory_system' in globals():
            memory_monitor = MemoryAccessMonitor(dashboard, memory_system)
            logger.info("Connected to memory system")
        else:
            logger.warning("Memory system not available, creating standalone memory monitor")
            memory_monitor = MemoryAccessMonitor(dashboard)
    except Exception as e:
        logger.error(f"Error connecting to memory system: {e}")
        memory_monitor = MemoryAccessMonitor(dashboard)
    
    # Register additional system components if available
    if 'llm_interface' in globals():
        dashboard.register_component("llm_interface", llm_interface)
        logger.info("Registered LLM interface with dashboard")
    
    if 'security_monitor' in globals():
        dashboard.register_component("security_monitor", security_monitor)
        logger.info("Registered security monitor with dashboard")
    
    if 'internet_controller' in globals():
        dashboard.register_component("internet_controller", internet_controller)
        logger.info("Registered internet controller with dashboard")
    
    # Try to connect to HTTP controller
    try:
        if 'http_controller' in globals():
            dashboard.http_controller = http_controller
            logger.info("Connected to HTTP controller")
            
            # Register API endpoint for dashboard access
            await register_dashboard_api(http_controller, dashboard)
    except Exception as e:
        logger.error(f"Error connecting to HTTP controller: {e}")
    
    # Start component monitoring
    asyncio.create_task(metrics_monitor.start_monitoring())
    asyncio.create_task(error_tracker.start_monitoring())
    
    if memory_monitor:
        asyncio.create_task(memory_monitor.start_monitoring())
    
    # Start dashboard update loop
    asyncio.create_task(dashboard.start_dashboard())
    
    return dashboard

async def register_dashboard_api(http_controller, dashboard):
    """Register API endpoints for the dashboard"""
    try:
        # Register API handlers
        http_controller.register_route('GET', '/api/system_info', lambda: handle_system_info(dashboard))
        http_controller.register_route('GET', '/api/dashboard', lambda: handle_dashboard_data(dashboard))
        http_controller.register_route('POST', '/api/dashboard/command', lambda data: handle_dashboard_command(dashboard, data))
        
        logger.info("Registered dashboard API endpoints")
        return True
    except Exception as e:
        logger.error(f"Error registering dashboard API: {e}")
        return False

async def handle_system_info(dashboard):
    """Handle GET /api/system_info requests"""
    try:
        # Get basic system info
        import platform
        import psutil
        
        # Get component status from dashboard
        component_status = dashboard.component_status
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Create response
        response = {
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
                "component_status": component_status,
                "uptime": 0  # Will be calculated if available
            }
        }
        
        return {"status": "success", "data": response}
    except Exception as e:
        logger.error(f"Error handling system info request: {e}")
        return {"status": "error", "error": str(e)}

async def handle_dashboard_data(dashboard):
    """Handle GET /api/dashboard requests"""
    try:
        # Force dashboard update
        await dashboard.update_dashboard()
        
        # Create response with panel data
        response = {
            "timestamp": dashboard.last_update.isoformat(),
            "panels": {}
        }
        
        for panel in dashboard.active_panels:
            if panel["visible"]:
                try:
                    panel_data = await panel["render"]()
                    response["panels"][panel["id"]] = panel_data
                except Exception as e:
                    logger.error(f"Error rendering panel {panel['id']}: {e}")
                    response["panels"][panel["id"]] = {
                        "error": str(e),
                        "status": "error"
                    }
        
        return {"status": "success", "data": response}
    except Exception as e:
        logger.error(f"Error handling dashboard data request: {e}")
        return {"status": "error", "error": str(e)}

async def handle_dashboard_command(dashboard, data):
    """Handle POST /api/dashboard/command requests"""
    try:
        command = data.get("command")
        params = data.get("params", {})
        
        if not command:
            return {"status": "error", "error": "No command specified"}
        
        result = await dashboard.execute_command(command, params)
        return {"status": "success" if result.get("success", False) else "error", "data": result}
    except Exception as e:
        logger.error(f"Error handling dashboard command: {e}")
        return {"status": "error", "error": str(e)}

async def main():
    """Main entry point for the Command Deck"""
    try:
        # Check if required directories exist
        os.makedirs('logs', exist_ok=True)
        os.makedirs('configs', exist_ok=True)
        
        # Initialize the Command Deck
        dashboard = await initialize_command_deck()
        
        logger.info("Command Deck initialized successfully")
        
        # Keep the program running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Command Deck shutdown requested")
    except Exception as e:
        logger.error(f"Error in Command Deck main loop: {e}")
    finally:
        logger.info("Command Deck shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())