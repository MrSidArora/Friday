# intent/context_analyzer.py
import logging
from datetime import datetime, timedelta

class ContextAnalyzer:
    """Analyzes conversation context to understand user intent in context."""
    
    def __init__(self, memory_system, llm_interface):
        """Initialize the context analyzer."""
        self.memory = memory_system
        self.llm = llm_interface
        self.logger = logging.getLogger('friday.context')
        self.context_window_size = 10  # Number of recent interactions to consider
    
    async def analyze_context(self, user_query):
        """Analyze the conversation context to enhance intent understanding."""
        # Get recent interactions
        recent_interactions = await self.memory.get_recent_interactions(self.context_window_size)
        
        # Get time context (time of day, day of week, etc.)
        time_context = self._get_time_context()
        
        # Get location context if available
        location_context = await self._get_location_context()
        
        # Get activity context (what the user has been doing)
        activity_context = await self._get_activity_context()
        
        # Combine contexts
        context = {
            "recent_interactions": recent_interactions,
            "time_context": time_context,
            "location_context": location_context,
            "activity_context": activity_context
        }
        
        # Look for context-dependent meanings
        context_insights = await self._analyze_context_dependencies(user_query, context)
        
        return {
            "context": context,
            "context_insights": context_insights
        }
    
    def _get_time_context(self):
        """Get information about the current time context."""
        now = datetime.now()
        
        # Time of day categories
        hour = now.hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 22:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        # Day of week
        day_of_week = now.strftime("%A").lower()
        
        # Weekend or weekday
        is_weekend = day_of_week in ["saturday", "sunday"]
        
        # Month and season (Northern Hemisphere)
        month = now.month
        if 3 <= month <= 5:
            season = "spring"
        elif 6 <= month <= 8:
            season = "summer"
        elif 9 <= month <= 11:
            season = "fall"
        else:
            season = "winter"
        
        return {
            "datetime": now.isoformat(),
            "time_of_day": time_of_day,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "month": now.strftime("%B").lower(),
            "season": season
        }
    
    async def _get_location_context(self):
        """Get information about the user's location context."""
        # This would typically integrate with a location service
        # For now, return a placeholder
        
        return {
            "available": False,
            "location": "unknown"
        }
    
    async def _get_activity_context(self):
        """Get information about the user's recent activities."""
        # This would integrate with activity tracking
        # For now, return a placeholder
        
        # Get active applications (in a real implementation)
        active_apps = ["unknown"]
        
        # Get recent documents (in a real implementation)
        recent_docs = []
        
        # Get current focus (in a real implementation)
        current_focus = "unknown"
        
        return {
            "active_applications": active_apps,
            "recent_documents": recent_docs,
            "current_focus": current_focus
        }
    
    async def _analyze_context_dependencies(self, query, context):
        """Analyze how context might affect the meaning of the query."""
        # This would typically use the LLM to evaluate context-dependent meanings
        # For now, implement a simplified version
        
        insights = {
            "references_resolved": [],
            "context_dependent_meanings": [],
            "time_relevant_factors": [],
            "activity_relevant_factors": []
        }
        
        # Check for references to resolve
        insights["references_resolved"] = await self._resolve_references(query, context["recent_interactions"])
        
        # Check for time-dependent meanings
        time_context = context["time_context"]
        if "today" in query.lower():
            insights["time_relevant_factors"].append({
                "term": "today",
                "resolution": datetime.now().strftime("%Y-%m-%d")
            })
        elif "tomorrow" in query.lower():
            tomorrow = datetime.now() + timedelta(days=1)
            insights["time_relevant_factors"].append({
                "term": "tomorrow",
                "resolution": tomorrow.strftime("%Y-%m-%d")
            })
        
        # Check for context-dependent meanings
        if "this" in query.lower() or "that" in query.lower():
            # Try to determine what "this" or "that" refers to
            insights["context_dependent_meanings"].append({
                "term": "this/that",
                "possible_meanings": ["recent topic", "last mentioned item"],
                "confidence": 0.6
            })
        
        # In a real implementation, we would use the LLM to analyze more complex
        # context dependencies
        
        return insights
    
    async def _resolve_references(self, query, recent_interactions):
        """Resolve references to previous conversation elements."""
        resolved_references = []
        
        # Check for pronouns that might refer to previous items
        pronouns = ["it", "this", "that", "they", "them", "these", "those"]
        
        for pronoun in pronouns:
            if f" {pronoun} " in f" {query.lower()} ":
                # Found a pronoun, try to resolve what it refers to
                resolution = await self._resolve_pronoun(pronoun, recent_interactions)
                if resolution:
                    resolved_references.append({
                        "pronoun": pronoun,
                        "likely_referent": resolution["referent"],
                        "confidence": resolution["confidence"]
                    })
        
        return resolved_references
    
    async def _resolve_pronoun(self, pronoun, recent_interactions):
        """Resolve what a pronoun likely refers to."""
        # This is a simplified implementation
        # In a real system, this would be more sophisticated
        
        # For simplicity, assume the pronoun refers to something in the last utterance
        if not recent_interactions:
            return None
        
        last_interaction = recent_interactions[-1]
        if not last_interaction.get("is_user", False):  # If last message was from Friday
            last_interaction = recent_interactions[-2] if len(recent_interactions) > 1 else None
        
        if not last_interaction:
            return None
        
        # Extract potential referents from the last user message
        # (This is a very simplified approach)
        import re
        last_text = last_interaction.get("text", "")
        
        # Look for nouns - this is oversimplified
        # In a real implementation, use NLP for proper noun extraction
        words = re.findall(r'\b[A-Za-z][a-z]{2,}\b', last_text)
        
        if words:
            # Just use the last noun-like word as a guess
            return {
                "referent": words[-1],
                "confidence": 0.5
            }
        
        return None