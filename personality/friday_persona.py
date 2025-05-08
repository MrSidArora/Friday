# personality/friday_persona.py
import json
import os
import logging
from datetime import datetime

class FridayPersona:
    """Manages Friday's personality characteristics and behaviors."""
    
    def __init__(self, config_path="personality/friday-persona.json"):
        """Initialize the personality engine with configuration."""
        self.config_path = config_path
        self.personality = self._load_personality_config()
        self.logger = logging.getLogger('friday.personality')
        
    def _load_personality_config(self):
        """Load personality configuration from JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as file:
                    return json.load(file)
            else:
                # Create default personality if config doesn't exist
                default_personality = self._create_default_personality()
                self._save_personality_config(default_personality)
                return default_personality
        except Exception as e:
            logging.error(f"Error loading personality config: {e}")
            return self._create_default_personality()
    
    def _create_default_personality(self):
        """Create default personality configuration."""
        return {
            "name": "Friday",
            "tone": {
                "formality": 0.5,      # 0.0 (casual) to 1.0 (formal)
                "friendliness": 0.7,   # 0.0 (neutral) to 1.0 (very friendly)
                "humor": 0.5           # 0.0 (serious) to 1.0 (humorous)
            },
            "behavior": {
                "proactivity": 0.7,    # How proactive in suggestions
                "verbosity": 0.5,      # Response length preference
                "explanation_depth": 0.7  # Detail level in explanations
            },
            "ethics": {
                "privacy_priority": 0.9,  # Privacy protection level
                "user_autonomy": 0.9,     # User control emphasis
                "brutal_honesty_enabled": True
            },
            "intent_modeling": {
                "inference_confidence": 0.6,  # Confidence threshold for acting on inferred intent
                "clarification_frequency": 0.4  # How often to ask for clarification vs. inference
            }
        }
    
    def _save_personality_config(self, personality):
        """Save personality configuration to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as file:
                json.dump(personality, file, indent=2)
        except Exception as e:
            logging.error(f"Error saving personality config: {e}")
    
    def get_personality_aspect(self, aspect_path):
        """Get a specific personality aspect using dot notation path."""
        try:
            current = self.personality
            for key in aspect_path.split('.'):
                current = current[key]
            return current
        except (KeyError, TypeError):
            self.logger.warning(f"Personality aspect not found: {aspect_path}")
            return None
    
    def update_personality_aspect(self, aspect_path, value):
        """Update a specific personality aspect using dot notation path."""
        try:
            path_parts = aspect_path.split('.')
            current = self.personality
            
            # Navigate to the parent of the target aspect
            for key in path_parts[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Set the value
            current[path_parts[-1]] = value
            self._save_personality_config(self.personality)
            return True
        except Exception as e:
            self.logger.error(f"Error updating personality aspect {aspect_path}: {e}")
            return False
    
    def get_prompt_modifiers(self):
        """Generate prompt modifiers based on personality settings."""
        modifiers = {
            "tone_modifiers": [],
            "behavior_modifiers": [],
            "ethical_guidelines": []
        }
        
        # Add tone modifiers
        tone = self.personality.get("tone", {})
        if tone.get("formality", 0.5) < 0.3:
            modifiers["tone_modifiers"].append("Use casual language and informal expressions")
        elif tone.get("formality", 0.5) > 0.7:
            modifiers["tone_modifiers"].append("Maintain formal language and professional tone")
            
        if tone.get("friendliness", 0.7) > 0.7:
            modifiers["tone_modifiers"].append("Be warm and encouraging in responses")
            
        if tone.get("humor", 0.5) > 0.6:
            modifiers["tone_modifiers"].append("Include occasional light humor when appropriate")
        
        # Add behavior modifiers
        behavior = self.personality.get("behavior", {})
        if behavior.get("verbosity", 0.5) < 0.3:
            modifiers["behavior_modifiers"].append("Provide concise, direct answers")
        elif behavior.get("verbosity", 0.5) > 0.7:
            modifiers["behavior_modifiers"].append("Offer detailed, comprehensive responses")
            
        if behavior.get("explanation_depth", 0.7) > 0.6:
            modifiers["behavior_modifiers"].append("Explain concepts thoroughly with examples")
        
        # Add ethical guidelines
        ethics = self.personality.get("ethics", {})
        if ethics.get("privacy_priority", 0.9) > 0.7:
            modifiers["ethical_guidelines"].append("Prioritize user privacy in all interactions")
            
        if ethics.get("brutal_honesty_enabled", True):
            modifiers["ethical_guidelines"].append("Provide honest feedback even when difficult")
        
        return modifiers