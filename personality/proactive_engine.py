# personality/proactive_engine.py
import json
import os
import logging
from datetime import datetime, timedelta
import threading
import time
import random

class ProactiveEngine:
    """Generates proactive suggestions based on user patterns and context."""
    
    def __init__(self, memory_system, personality, preferences, triggers_path="personality/proactive_triggers.json"):
        """Initialize the proactive suggestion engine."""
        self.memory = memory_system
        self.personality = personality
        self.preferences = preferences
        self.triggers_path = triggers_path
        self.logger = logging.getLogger('friday.proactive')
        self.triggers = self._load_triggers()
        self.suggestion_queue = []
        self.suggestion_history = []
        self._suggestion_thread = None
        self._running = False
    
    def _load_triggers(self):
        """Load proactive triggers from JSON file."""
        try:
            if os.path.exists(self.triggers_path):
                with open(self.triggers_path, 'r') as file:
                    return json.load(file)
            else:
                # Create default triggers if file doesn't exist
                default_triggers = self._create_default_triggers()
                self._save_triggers(default_triggers)
                return default_triggers
        except Exception as e:
            self.logger.error(f"Error loading proactive triggers: {e}")
            return self._create_default_triggers()
    
    def _create_default_triggers(self):
        """Create default proactive triggers."""
        return {
            "time_based": [
                {
                    "name": "morning_greeting",
                    "condition": {"time_range": ["06:00", "10:00"]},
                    "suggestion_template": "Good morning! Here's your schedule for today: {daily_schedule}",
                    "priority": 0.8,
                    "cooldown_hours": 20
                },
                {
                    "name": "evening_summary",
                    "condition": {"time_range": ["19:00", "22:00"]},
                    "suggestion_template": "Here's a summary of your day: {day_summary}",
                    "priority": 0.7,
                    "cooldown_hours": 20
                }
            ],
            "pattern_based": [
                {
                    "name": "repeated_searches",
                    "condition": {"repeated_searches": {"count": 3, "timespan_minutes": 15}},
                    "suggestion_template": "I notice you've searched for {search_term} several times. Would you like me to help find more comprehensive information?",
                    "priority": 0.9,
                    "cooldown_hours": 1
                },
                {
                    "name": "task_reminder",
                    "condition": {"mentioned_task": {"timespan_hours": 24, "not_completed": True}},
                    "suggestion_template": "Earlier, you mentioned a task to {task_description}. Would you like to work on that now?",
                    "priority": 0.8,
                    "cooldown_hours": 4
                }
            ],
            "context_based": [
                {
                    "name": "low_system_resources",
                    "condition": {"system_resource": {"type": "memory", "threshold": 0.9}},
                    "suggestion_template": "I notice your system memory is running low. Would you like me to help close unused applications?",
                    "priority": 0.95,
                    "cooldown_hours": 2
                },
                {
                    "name": "learning_opportunity",
                    "condition": {"repeated_difficulties": {"topic": "{topic}", "count": 3}},
                    "suggestion_template": "I've noticed you've had some challenges with {topic}. Would you like me to provide some learning resources?",
                    "priority": 0.7,
                    "cooldown_hours": 48
                }
            ]
        }
    
    def _save_triggers(self, triggers):
        """Save proactive triggers to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.triggers_path), exist_ok=True)
            with open(self.triggers_path, 'w') as file:
                json.dump(triggers, file, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving proactive triggers: {e}")
    
    def start_proactive_monitoring(self):
        """Start the background thread for proactive monitoring."""
        if self._suggestion_thread is None or not self._suggestion_thread.is_alive():
            self._running = True
            self._suggestion_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._suggestion_thread.start()
            self.logger.info("Proactive monitoring started")
    
    def stop_proactive_monitoring(self):
        """Stop the background thread for proactive monitoring."""
        self._running = False
        if self._suggestion_thread and self._suggestion_thread.is_alive():
            self._suggestion_thread.join(timeout=1.0)
            self.logger.info("Proactive monitoring stopped")
    
    def _monitoring_loop(self):
        """Background loop for monitoring triggers and generating suggestions."""
        while self._running:
            try:
                # Check if proactivity is enabled in personality
                proactivity_level = self.personality.get_personality_aspect("behavior.proactivity")
                if proactivity_level is None or proactivity_level < 0.3:
                    # Low proactivity, check less frequently
                    time.sleep(60)
                    continue
                
                # Check triggers
                self._check_time_based_triggers()
                self._check_pattern_based_triggers()
                self._check_context_based_triggers()
                
                # Sleep proportional to proactivity (more proactive = check more often)
                sleep_seconds = max(10, int(60 * (1 - proactivity_level)))
                time.sleep(sleep_seconds)
            except Exception as e:
                self.logger.error(f"Error in proactive monitoring loop: {e}")
                time.sleep(30)  # Sleep on error to avoid tight loop
    
    def _check_time_based_triggers(self):
        """Check time-based triggers."""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        for trigger in self.triggers.get("time_based", []):
            try:
                # Extract time range
                start_time, end_time = trigger["condition"]["time_range"]
                
                # Check if current time is within range
                if self._is_time_in_range(current_time_str, start_time, end_time):
                    # Check if this trigger is in cooldown
                    if not self._is_trigger_in_cooldown(trigger["name"]):
                        # Generate suggestion
                        suggestion = self._generate_suggestion(trigger)
                        if suggestion:
                            self._add_suggestion(suggestion)
            except Exception as e:
                self.logger.error(f"Error checking time trigger {trigger.get('name', 'unknown')}: {e}")
    
    def _check_pattern_based_triggers(self):
        """Check pattern-based triggers."""
        for trigger in self.triggers.get("pattern_based", []):
            try:
                if not self._is_trigger_in_cooldown(trigger["name"]):
                    # Check conditions - this would integrate with memory system
                    if self._pattern_matches(trigger["condition"]):
                        suggestion = self._generate_suggestion(trigger)
                        if suggestion:
                            self._add_suggestion(suggestion)
            except Exception as e:
                self.logger.error(f"Error checking pattern trigger {trigger.get('name', 'unknown')}: {e}")
    
    def _check_context_based_triggers(self):
        """Check context-based triggers."""
        for trigger in self.triggers.get("context_based", []):
            try:
                if not self._is_trigger_in_cooldown(trigger["name"]):
                    # Check conditions - this would integrate with system monitoring
                    if self._context_matches(trigger["condition"]):
                        suggestion = self._generate_suggestion(trigger)
                        if suggestion:
                            self._add_suggestion(suggestion)
            except Exception as e:
                self.logger.error(f"Error checking context trigger {trigger.get('name', 'unknown')}: {e}")
    
    def _is_time_in_range(self, time_str, start_time, end_time):
        """Check if a time string is within a specified range."""
        from datetime import datetime
        time_format = "%H:%M"
        time_obj = datetime.strptime(time_str, time_format).time()
        start_obj = datetime.strptime(start_time, time_format).time()
        end_obj = datetime.strptime(end_time, time_format).time()
        
        if start_obj <= end_obj:
            return start_obj <= time_obj <= end_obj
        else:  # Handle ranges that cross midnight
            return time_obj >= start_obj or time_obj <= end_obj
    
    def _is_trigger_in_cooldown(self, trigger_name):
        """Check if a trigger is currently in cooldown period."""
        for history in self.suggestion_history:
            if history["trigger_name"] == trigger_name:
                cooldown_hours = 0
                for trigger_type in self.triggers.values():
                    for trigger in trigger_type:
                        if trigger["name"] == trigger_name:
                            cooldown_hours = trigger.get("cooldown_hours", 0)
                            break
                
                cooldown_ends = history["timestamp"] + timedelta(hours=cooldown_hours)
                if datetime.now() < cooldown_ends:
                    return True
        
        return False
    
    def _pattern_matches(self, condition):
        """Check if a pattern-based condition matches."""
        # This is a placeholder implementation
        # In a real implementation, this would check the memory system for patterns
        
        # Simulate some patterns for testing
        if "repeated_searches" in condition:
            # 10% chance of matching for testing
            return random.random() < 0.1
        elif "mentioned_task" in condition:
            # 5% chance of matching for testing
            return random.random() < 0.05
        
        return False
    
    def _context_matches(self, condition):
        """Check if a context-based condition matches."""
        # This is a placeholder implementation
        # In a real implementation, this would check system resources or other context
        
        # Simulate some contexts for testing
        if "system_resource" in condition:
            resource_type = condition["system_resource"]["type"]
            if resource_type == "memory":
                # 2% chance of system memory being high for testing
                return random.random() < 0.02
        elif "repeated_difficulties" in condition:
            # 1% chance of learning difficulties for testing
            return random.random() < 0.01
        
        return False
    
    def _generate_suggestion(self, trigger):
        """Generate a suggestion based on a trigger."""
        template = trigger["suggestion_template"]
        
        # In a real implementation, template variables would be filled from context
        # This is a placeholder implementation
        
        filled_template = template
        
        # Replace template variables with mock data for now
        if "{daily_schedule}" in template:
            filled_template = template.replace("{daily_schedule}", "a meeting at 10 AM and project work at 2 PM")
        elif "{day_summary}" in template:
            filled_template = template.replace("{day_summary}", "You completed 3 tasks and spent 4 hours on the project")
        elif "{search_term}" in template:
            filled_template = template.replace("{search_term}", "Python async programming")
        elif "{task_description}" in template:
            filled_template = template.replace("{task_description}", "finish the report")
        elif "{topic}" in template:
            filled_template = template.replace("{topic}", "regex patterns")
        
        return {
            "trigger_name": trigger["name"],
            "message": filled_template,
            "priority": trigger.get("priority", 0.5),
            "timestamp": datetime.now()
        }
    
    def _add_suggestion(self, suggestion):
        """Add a suggestion to the queue and history."""
        # Add to queue
        self.suggestion_queue.append(suggestion)
        
        # Sort by priority
        self.suggestion_queue.sort(key=lambda x: x["priority"], reverse=True)
        
        # Limit queue size
        max_queue_size = 10
        if len(self.suggestion_queue) > max_queue_size:
            self.suggestion_queue = self.suggestion_queue[:max_queue_size]
        
        # Add to history
        self.suggestion_history.append(suggestion)
        
        # Limit history size
        max_history = 100
        if len(self.suggestion_history) > max_history:
            self.suggestion_history = self.suggestion_history[-max_history:]
        
        self.logger.info(f"Added suggestion: {suggestion['message'][:50]}...")
    
    def get_next_suggestion(self):
        """Get the next suggested action if available."""
        if not self.suggestion_queue:
            return None
        
        # Default behavior is to pop from queue (use and remove)
        suggestion = self.suggestion_queue.pop(0)
        
        return suggestion
    
    def peek_next_suggestion(self):
        """Preview the next suggestion without removing it."""
        if not self.suggestion_queue:
            return None
        
        return self.suggestion_queue[0]
    
    def add_custom_suggestion(self, message, priority=0.5, trigger_name="custom"):
        """Manually add a custom suggestion."""
        suggestion = {
            "trigger_name": trigger_name,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now()
        }
        
        self._add_suggestion(suggestion)
        return suggestion
    
    def clear_suggestions(self):
        """Clear all pending suggestions."""
        count = len(self.suggestion_queue)
        self.suggestion_queue = []
        return count
    
    def add_custom_trigger(self, trigger_type, trigger_data):
        """Add a custom trigger configuration."""
        if trigger_type not in self.triggers:
            self.triggers[trigger_type] = []
        
        # Check if trigger with this name already exists
        for existing in self.triggers[trigger_type]:
            if existing["name"] == trigger_data["name"]:
                # Update existing trigger
                existing.update(trigger_data)
                self._save_triggers(self.triggers)
                return True
        
        # Add new trigger
        self.triggers[trigger_type].append(trigger_data)
        self._save_triggers(self.triggers)
        return True