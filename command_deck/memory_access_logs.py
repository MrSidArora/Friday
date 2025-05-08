# command_deck/memory_access_logs.py
import asyncio
import datetime
import logging
import os
import json
from typing import Dict, List, Optional

# Configure logger
logger = logging.getLogger('memory_access_logs')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs/command_deck.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class MemoryAccessMonitor:
    def __init__(self, dashboard=None, memory_system=None):
        self.dashboard = dashboard
        self.memory_system = memory_system
        self.access_logs = []
        self.log_limit = 200  # Store this many log entries
        self.error_logs = []
        self.running = False
        self.update_interval = 5  # seconds
        self.last_update = datetime.datetime.now()
        logger.info("Memory Access Monitor initialized")
        
        if dashboard:
            dashboard.register_panel("memory_access", self.render_memory_panel)
            dashboard.register_component("memory_access", self)
    
    def log_memory_access(self, operation: str, memory_tier: str, key: str, agent: str, 
                         success: bool, details: Dict = None, error: str = None):
        """Log a memory access operation"""
        timestamp = datetime.datetime.now()
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "operation": operation,
            "memory_tier": memory_tier,
            "key": key,
            "agent": agent,
            "success": success,
            "details": details or {}
        }
        
        if error:
            log_entry["error"] = error
            self.error_logs.append({
                "timestamp": timestamp.isoformat(),
                "operation": operation,
                "memory_tier": memory_tier,
                "error": error
            })
            
            # Trim error logs if needed
            if len(self.error_logs) > self.log_limit:
                self.error_logs = self.error_logs[-self.log_limit:]
        
        self.access_logs.append(log_entry)
        
        # Trim logs if needed
        if len(self.access_logs) > self.log_limit:
            self.access_logs = self.access_logs[-self.log_limit:]
        
        # Update dashboard if available
        if self.dashboard:
            self.dashboard.update_component_status("memory_access", "running")
            
        self.last_update = timestamp
        return log_entry
    
    async def start_monitoring(self):
        """Start monitoring memory access in the background"""
        if not self.memory_system:
            logger.warning("Cannot start memory access monitoring: No memory system provided")
            return False
        
        self.running = True
        logger.info("Starting memory access monitoring")
        
        # Register with memory system if it supports it
        if hasattr(self.memory_system, "register_monitor"):
            self.memory_system.register_monitor(self)
        
        # Periodic check for memory statistics
        while self.running:
            try:
                await self.collect_memory_stats()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error collecting memory statistics: {e}")
                await asyncio.sleep(self.update_interval * 2)
    
    async def collect_memory_stats(self):
        """Collect statistics about memory usage"""
        if not self.memory_system:
            return
        
        try:
            stats = {}
            
            # Check if memory system has methods to get statistics
            if hasattr(self.memory_system, "get_memory_stats"):
                stats = await self.memory_system.get_memory_stats()
            else:
                # Fallback to basic stats
                if hasattr(self.memory_system, "short_term"):
                    if isinstance(self.memory_system.short_term, dict):
                        stats["short_term_count"] = len(self.memory_system.short_term)
                
                if hasattr(self.memory_system, "mid_term"):
                    if hasattr(self.memory_system.mid_term, "count_entries"):
                        stats["mid_term_count"] = await self.memory_system.mid_term.count_entries()
                
                if hasattr(self.memory_system, "long_term"):
                    if hasattr(self.memory_system.long_term, "count"):
                        stats["long_term_count"] = await self.memory_system.long_term.count()
            
            # Add timestamp
            stats["timestamp"] = datetime.datetime.now().isoformat()
            
            # Calculate access statistics
            recent_logs = self.access_logs[-min(50, len(self.access_logs)):]
            operation_counts = {}
            tier_counts = {}
            error_count = 0
            
            for log in recent_logs:
                # Count operations
                op = log["operation"]
                if op in operation_counts:
                    operation_counts[op] += 1
                else:
                    operation_counts[op] = 1
                
                # Count memory tiers
                tier = log["memory_tier"]
                if tier in tier_counts:
                    tier_counts[tier] += 1
                else:
                    tier_counts[tier] = 1
                
                # Count errors
                if not log["success"]:
                    error_count += 1
            
            stats["recent_operations"] = operation_counts
            stats["recent_tiers"] = tier_counts
            stats["recent_error_count"] = error_count
            
            self.last_stats = stats
            self.last_update = datetime.datetime.now()
            
            return stats
        except Exception as e:
            logger.error(f"Error collecting memory statistics: {e}")
            if self.dashboard:
                self.dashboard.update_component_status("memory_access", "error", str(e))
            raise
    
    async def render_memory_panel(self):
        """Render the memory access panel for the dashboard"""
        try:
            # Get latest stats if needed
            if not hasattr(self, 'last_stats') or (datetime.datetime.now() - self.last_update).total_seconds() > self.update_interval * 2:
                await self.collect_memory_stats()
            
            # Create the panel data
            panel_data = {
                "title": "Memory Access Logs",
                "timestamp": datetime.datetime.now().isoformat(),
                "stats": getattr(self, 'last_stats', {}),
                "recent_access_logs": self.access_logs[-20:],  # Last 20 access logs
                "recent_error_logs": self.error_logs[-10:],  # Last 10 error logs
                "memory_tiers": {
                    "short_term": {
                        "description": "Fast, volatile memory for immediate context",
                        "implementation": "Redis or in-memory dict" 
                    },
                    "mid_term": {
                        "description": "Persistent storage for recent interactions",
                        "implementation": "SQLite"
                    },
                    "long_term": {
                        "description": "Vector database for semantic search",
                        "implementation": "Chroma"
                    }
                }
            }
            
            return panel_data
        except Exception as e:
            logger.error(f"Error rendering memory panel: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def get_access_logs(self, operation=None, memory_tier=None, agent=None, success=None, limit=50):
        """Get filtered access logs"""
        filtered_logs = self.access_logs
        
        # Apply filters
        if operation:
            filtered_logs = [log for log in filtered_logs if log["operation"] == operation]
        
        if memory_tier:
            filtered_logs = [log for log in filtered_logs if log["memory_tier"] == memory_tier]
        
        if agent:
            filtered_logs = [log for log in filtered_logs if log["agent"] == agent]
        
        if success is not None:
            filtered_logs = [log for log in filtered_logs if log["success"] == success]
        
        # Return limited results, most recent first
        return sorted(filtered_logs, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    async def get_status(self):
        """Get component status for dashboard"""
        try:
            # Check if monitoring is active
            if (datetime.datetime.now() - self.last_update).total_seconds() > self.update_interval * 3:
                return {
                    "status": "stalled",
                    "error": "Memory access monitoring has stalled"
                }
            
            # Count recent errors
            error_count = len([log for log in self.access_logs[-50:] if not log.get("success", True)])
            
            if error_count > 10:
                return {
                    "status": "warning",
                    "warning": f"High error rate in memory access: {error_count} recent errors"
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
        """Run diagnostics on the memory access system"""
        try:
            # Collect latest stats
            stats = await self.collect_memory_stats()
            
            # Analyze recent access logs
            recent_logs = self.access_logs[-min(100, len(self.access_logs)):]
            error_count = len([log for log in recent_logs if not log.get("success", True)])
            error_rate = error_count / len(recent_logs) if recent_logs else 0
            
            # Check for common error patterns
            error_types = {}
            for log in [log for log in recent_logs if not log.get("success", True)]:
                error_msg = log.get("error", "Unknown error")
                if error_msg in error_types:
                    error_types[error_msg] += 1
                else:
                    error_types[error_msg] = 1
            
            # Sort error types by frequency
            sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
            
            # Check for potential issues
            issues = []
            warnings = []
            
            if error_rate > 0.2:
                issues.append(f"High memory error rate: {error_rate:.1%}")
            elif error_rate > 0.1:
                warnings.append(f"Elevated memory error rate: {error_rate:.1%}")
            
            if sorted_errors:
                most_common_error, count = sorted_errors[0]
                if count > 5:
                    issues.append(f"Recurring error ({count} occurrences): {most_common_error}")
            
            # Test memory system if available
            memory_test_results = {}
            if self.memory_system:
                if hasattr(self.memory_system, "test_connectivity"):
                    memory_test_results["connectivity"] = await self.memory_system.test_connectivity()
                
                # Basic checks for each tier
                for tier in ["short_term", "mid_term", "long_term"]:
                    if hasattr(self.memory_system, tier):
                        tier_obj = getattr(self.memory_system, tier)
                        if tier_obj:
                            memory_test_results[tier] = "available"
                        else:
                            memory_test_results[tier] = "unavailable"
                            warnings.append(f"Memory tier '{tier}' is unavailable")
            
            return {
                "status": "critical" if issues else "warning" if warnings else "healthy",
                "issues": issues,
                "warnings": warnings,
                "stats": stats,
                "error_rate": error_rate,
                "common_errors": sorted_errors[:5],
                "memory_test_results": memory_test_results
            }
        except Exception as e:
            logger.error(f"Error running memory diagnostics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def restart(self):
        """Restart the memory access monitor"""
        try:
            self.running = False
            await asyncio.sleep(1)
            
            # Clear logs
            self.access_logs = []
            self.error_logs = []
            
            # Restart
            self.running = True
            asyncio.create_task(self.start_monitoring())
            
            return {
                "success": True,
                "message": "Memory access monitor restarted"
            }
        except Exception as e:
            logger.error(f"Error restarting memory access monitor: {e}")
            return {
                "success": False,
                "error": str(e)
            }