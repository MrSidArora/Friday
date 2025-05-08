# command_deck/dashboard_interface.py
import asyncio
import datetime
import logging
import os
import json
from typing import Dict, List, Callable, Any, Optional

# Configure logger
logger = logging.getLogger('command_deck')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs/command_deck.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class CommandDeckDashboard:
    def __init__(self, http_controller=None):
        self.http_controller = http_controller
        self.active_panels = []
        self.registered_components = {}
        self.component_status = {}
        self.error_logs = []
        self.dashboard_config = self._load_config()
        self.last_update = datetime.datetime.now()
        logger.info("Command Deck Dashboard initialized")
    
    def _load_config(self) -> Dict:
        """Load dashboard configuration"""
        config_path = os.path.join('configs', 'command_deck_config.json')
        default_config = {
            "refresh_rate": 5,  # seconds
            "error_log_limit": 100,
            "default_panels": ["system_metrics", "memory_access", "error_tracker"],
            "ui_theme": "dark",
            "enable_remote_access": False
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            logger.error(f"Error loading dashboard config: {e}")
            return default_config
    
    def register_panel(self, panel_id: str, render_function: Callable):
        """Register a panel with the dashboard"""
        self.active_panels.append({
            "id": panel_id,
            "render": render_function,
            "visible": panel_id in self.dashboard_config.get("default_panels", []),
            "position": len(self.active_panels)
        })
        logger.info(f"Registered panel: {panel_id}")
        return True
    
    def register_component(self, component_id: str, component_instance: Any):
        """Register a system component for monitoring"""
        self.registered_components[component_id] = component_instance
        self.component_status[component_id] = {
            "status": "unknown",
            "last_check": datetime.datetime.now(),
            "errors": []
        }
        logger.info(f"Registered component: {component_id}")
        return True
    
    def update_component_status(self, component_id: str, status: str, error: Optional[str] = None):
        """Update the status of a monitored component"""
        if component_id in self.component_status:
            self.component_status[component_id]["status"] = status
            self.component_status[component_id]["last_check"] = datetime.datetime.now()
            
            if error:
                self.component_status[component_id]["errors"].append({
                    "timestamp": datetime.datetime.now(),
                    "message": error
                })
                # Keep only recent errors
                max_errors = 10
                if len(self.component_status[component_id]["errors"]) > max_errors:
                    self.component_status[component_id]["errors"] = self.component_status[component_id]["errors"][-max_errors:]
                
                # Also log to central error log
                self._log_error(component_id, error)
            
            return True
        return False
    
    def _log_error(self, component_id: str, error_message: str):
        """Add error to centralized error log"""
        self.error_logs.append({
            "component": component_id,
            "timestamp": datetime.datetime.now(),
            "message": error_message
        })
        
        # Keep error log size under limit
        if len(self.error_logs) > self.dashboard_config.get("error_log_limit", 100):
            self.error_logs = self.error_logs[-self.dashboard_config.get("error_log_limit", 100):]
    
    async def start_dashboard(self):
        """Start the dashboard update loop"""
        logger.info("Starting Command Deck Dashboard update loop")
        while True:
            try:
                await self.update_dashboard()
                await asyncio.sleep(self.dashboard_config.get("refresh_rate", 5))
            except Exception as e:
                logger.error(f"Error in dashboard update loop: {e}")
                await asyncio.sleep(10)  # Longer sleep on error
    
    async def update_dashboard(self):
        """Update all dashboard panels with current data"""
        update_time = datetime.datetime.now()
        time_diff = (update_time - self.last_update).total_seconds()
        
        # Skip if update interval hasn't elapsed
        if time_diff < self.dashboard_config.get("refresh_rate", 5):
            return
        
        self.last_update = update_time
        
        # Update component status
        await self._check_components()
        
        # Render all active panels
        dashboard_data = {
            "timestamp": update_time.isoformat(),
            "panels": {},
            "component_status": self.component_status,
            "error_summary": self._generate_error_summary()
        }
        
        for panel in self.active_panels:
            if panel["visible"]:
                try:
                    panel_data = await panel["render"]()
                    dashboard_data["panels"][panel["id"]] = panel_data
                except Exception as e:
                    logger.error(f"Error rendering panel {panel['id']}: {e}")
                    dashboard_data["panels"][panel["id"]] = {
                        "error": str(e),
                        "status": "error"
                    }
        
        # Send to UI if HTTP controller is available
        if self.http_controller:
            try:
                await self.http_controller.send_to_ui("dashboard_update", dashboard_data)
            except Exception as e:
                logger.error(f"Error sending dashboard data to UI: {e}")
    
    async def _check_components(self):
        """Check status of all registered components"""
        for component_id, component in self.registered_components.items():
            try:
                if hasattr(component, "get_status"):
                    status = await component.get_status()
                    self.update_component_status(component_id, status.get("status", "unknown"))
                    
                    if "error" in status and status["error"]:
                        self.update_component_status(component_id, "error", status["error"])
            except Exception as e:
                self.update_component_status(component_id, "error", str(e))
    
    def _generate_error_summary(self):
        """Generate a summary of recent errors"""
        recent_errors = sorted(self.error_logs, key=lambda x: x["timestamp"], reverse=True)[:10]
        error_counts = {}
        
        for error in self.error_logs:
            component = error["component"]
            if component in error_counts:
                error_counts[component] += 1
            else:
                error_counts[component] = 1
        
        return {
            "total_errors": len(self.error_logs),
            "recent_errors": recent_errors,
            "error_counts": error_counts
        }
    
    def get_component_errors(self, component_id: str = None, limit: int = 20):
        """Get errors for a specific component or all components"""
        if component_id:
            if component_id in self.component_status:
                return self.component_status[component_id]["errors"][:limit]
            return []
        else:
            return self.error_logs[:limit]
    
    def toggle_panel(self, panel_id: str, visible: bool = None):
        """Toggle a panel's visibility"""
        for panel in self.active_panels:
            if panel["id"] == panel_id:
                if visible is None:
                    panel["visible"] = not panel["visible"]
                else:
                    panel["visible"] = visible
                return True
        return False

    async def execute_command(self, command: str, params: Dict = None):
        """Execute a dashboard command"""
        if not params:
            params = {}
            
        commands = {
            "restart_component": self._restart_component,
            "clear_errors": self._clear_errors,
            "toggle_panel": self.toggle_panel,
            "get_component_details": self._get_component_details,
            "run_diagnostics": self._run_diagnostics,
            # Add more commands as needed
        }
        
        if command in commands:
            try:
                return await commands[command](**params)
            except Exception as e:
                logger.error(f"Error executing command {command}: {e}")
                return {"error": str(e), "success": False}
        else:
            return {"error": f"Unknown command: {command}", "success": False}
    
    async def _restart_component(self, component_id: str):
        """Restart a system component"""
        if component_id not in self.registered_components:
            return {"error": f"Component not found: {component_id}", "success": False}
            
        component = self.registered_components[component_id]
        try:
            if hasattr(component, "restart"):
                result = await component.restart()
                return {"success": True, "result": result}
            else:
                return {"error": f"Component {component_id} does not support restart", "success": False}
        except Exception as e:
            logger.error(f"Error restarting component {component_id}: {e}")
            return {"error": str(e), "success": False}
    
    async def _clear_errors(self, component_id: str = None):
        """Clear error logs for a component or all components"""
        if component_id:
            if component_id in self.component_status:
                self.component_status[component_id]["errors"] = []
                return {"success": True}
            return {"error": f"Component not found: {component_id}", "success": False}
        else:
            self.error_logs = []
            for component_id in self.component_status:
                self.component_status[component_id]["errors"] = []
            return {"success": True}
    
    async def _get_component_details(self, component_id: str):
        """Get detailed information about a component"""
        if component_id not in self.registered_components:
            return {"error": f"Component not found: {component_id}", "success": False}
            
        component = self.registered_components[component_id]
        details = {
            "id": component_id,
            "status": self.component_status[component_id]["status"],
            "errors": self.component_status[component_id]["errors"],
            "last_check": self.component_status[component_id]["last_check"].isoformat()
        }
        
        try:
            if hasattr(component, "get_details"):
                component_details = await component.get_details()
                details.update(component_details)
        except Exception as e:
            logger.error(f"Error getting details for component {component_id}: {e}")
            details["detail_error"] = str(e)
        
        return {"success": True, "details": details}
    
    async def _run_diagnostics(self, component_id: str = None):
        """Run diagnostics on a component or the whole system"""
        if component_id:
            if component_id not in self.registered_components:
                return {"error": f"Component not found: {component_id}", "success": False}
                
            component = self.registered_components[component_id]
            try:
                if hasattr(component, "run_diagnostics"):
                    diagnostics = await component.run_diagnostics()
                    return {"success": True, "diagnostics": diagnostics}
                else:
                    return {"error": f"Component {component_id} does not support diagnostics", "success": False}
            except Exception as e:
                logger.error(f"Error running diagnostics for component {component_id}: {e}")
                return {"error": str(e), "success": False}
        else:
            # Run system-wide diagnostics
            results = {}
            for comp_id, component in self.registered_components.items():
                try:
                    if hasattr(component, "run_diagnostics"):
                        results[comp_id] = await component.run_diagnostics()
                    else:
                        results[comp_id] = {"supported": False}
                except Exception as e:
                    logger.error(f"Error running diagnostics for component {comp_id}: {e}")
                    results[comp_id] = {"error": str(e)}
            
            return {"success": True, "diagnostics": results}