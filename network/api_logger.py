import os
import json
import logging
from datetime import datetime

class ApiLogger:
    def __init__(self, log_path="logs/api_usage.log"):
        self.log_path = log_path
        
        # Set up logging
        self.logger = logging.getLogger("api_logger")
        self.logger.setLevel(logging.INFO)
        
        if not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(os.path.dirname(log_path))
            
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # API rate and cost estimates
        self.api_costs = {
            "openai": {
                "chat": 0.002,  # Cost per 1K tokens
                "whisper": 0.006  # Cost per minute
            },
            "google": {
                "search": 0.01  # Cost per query
            }
        }
        
        # Monthly usage tracking
        self.current_month = datetime.now().strftime("%Y-%m")
        self.monthly_usage = self._load_monthly_usage()
        
    def _load_monthly_usage(self):
        """Load the current monthly usage from file"""
        usage_file = f"logs/monthly_usage_{self.current_month}.json"
        
        if os.path.exists(usage_file):
            try:
                with open(usage_file, 'r') as f:
                    return json.load(f)
            except:
                pass
                
        # Default structure if file doesn't exist or can't be loaded
        return {
            "openai": {
                "chat_tokens": 0,
                "whisper_minutes": 0,
                "estimated_cost": 0.0
            },
            "google": {
                "search_queries": 0,
                "estimated_cost": 0.0
            },
            "total_estimated_cost": 0.0
        }
        
    def _save_monthly_usage(self):
        """Save the current monthly usage to file"""
        usage_file = f"logs/monthly_usage_{self.current_month}.json"
        
        try:
            with open(usage_file, 'w') as f:
                json.dump(self.monthly_usage, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving monthly usage: {str(e)}")
            
    def log_api_call(self, service, endpoint, usage_data, response_data=None, error=None):
        """Log an API call with usage data"""
        # Check if month has changed
        current_month = datetime.now().strftime("%Y-%m")
        if current_month != self.current_month:
            self.current_month = current_month
            self.monthly_usage = self._load_monthly_usage()
            
        # Calculate estimated cost
        estimated_cost = 0.0
        
        if service == "openai":
            if endpoint == "chat":
                tokens = usage_data.get("total_tokens", 0)
                estimated_cost = (tokens / 1000) * self.api_costs["openai"]["chat"]
                self.monthly_usage["openai"]["chat_tokens"] += tokens
            elif endpoint == "whisper":
                minutes = usage_data.get("minutes", 0)
                estimated_cost = minutes * self.api_costs["openai"]["whisper"]
                self.monthly_usage["openai"]["whisper_minutes"] += minutes
                
            self.monthly_usage["openai"]["estimated_cost"] += estimated_cost
                
        elif service == "google":
            if endpoint == "search":
                queries = usage_data.get("queries", 1)
                estimated_cost = queries * self.api_costs["google"]["search"]
                self.monthly_usage["google"]["search_queries"] += queries
                self.monthly_usage["google"]["estimated_cost"] += estimated_cost
                
        # Update total cost
        self.monthly_usage["total_estimated_cost"] += estimated_cost
        
        # Prepare log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "endpoint": endpoint,
            "usage_data": usage_data,
            "estimated_cost": estimated_cost,
            "monthly_cost_to_date": self.monthly_usage["total_estimated_cost"]
        }
        
        if error:
            log_entry["error"] = str(error)
            
        # Log the entry
        self.logger.info(json.dumps(log_entry))
        
        # Save updated monthly usage
        self._save_monthly_usage()
        
        return {
            "estimated_cost": estimated_cost,
            "monthly_cost_to_date": self.monthly_usage["total_estimated_cost"]
        }
        
    def get_monthly_usage(self):
        """Get the current monthly usage stats"""
        return self.monthly_usage