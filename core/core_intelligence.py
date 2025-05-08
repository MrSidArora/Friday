# core/core_intelligence.py
import logging
import asyncio

class CoreIntelligence:
    """Integrates and coordinates the core intelligence components of Friday."""
    
    def __init__(self, memory_system, model_manager, security_monitor):
        """Initialize the core intelligence."""
        self.memory = memory_system
        self.model_manager = model_manager
        self.security = security_monitor
        self.logger = logging.getLogger('friday.core_intelligence')
        
        # Initialize sub-components
        self.personality = None
        self.preferences = None
        self.proactive_engine = None
        self.llm_interface = None
        self.intent_profiler = None
        self.context_analyzer = None
        self.implicit_needs = None
        self.response_generator = None
        
        # Status flag
        self.initialized = False
    
    async def initialize(self):
        """Initialize all core intelligence components."""
        try:
            # Import components
            from personality.friday_persona import FridayPersona
            from personality.preferences import UserPreferences
            from personality.proactive_engine import ProactiveEngine
            from core.llm_interface import LLMInterface
            from intent.intent_profiler import IntentProfiler
            from intent.context_analyzer import ContextAnalyzer
            from intent.implicit_needs import ImplicitNeedsRecognizer
            from intent.response_generator import ResponseGenerator
            
            # Initialize components
            self.logger.info("Initializing personality engine...")
            self.personality = FridayPersona()
            
            self.logger.info("Initializing user preferences...")
            self.preferences = UserPreferences()
            
            self.logger.info("Initializing LLM interface...")
            self.llm_interface = LLMInterface(self.model_manager, self.personality, self.memory)
            
            self.logger.info("Initializing intent profiler...")
            self.intent_profiler = IntentProfiler(self.memory, self.llm_interface)
            
            self.logger.info("Initializing context analyzer...")
            self.context_analyzer = ContextAnalyzer(self.memory, self.llm_interface)
            
            self.logger.info("Initializing implicit needs recognizer...")
            self.implicit_needs = ImplicitNeedsRecognizer(self.memory, self.llm_interface)
            
            self.logger.info("Initializing response generator...")
            self.response_generator = ResponseGenerator(
                self.llm_interface,
                self.intent_profiler,
                self.context_analyzer,
                self.implicit_needs,
                self.personality
            )
            
            self.logger.info("Initializing proactive engine...")
            self.proactive_engine = ProactiveEngine(self.memory, self.personality, self.preferences)
            
            # Start the proactive monitoring
            self.proactive_engine.start_proactive_monitoring()
            
            self.initialized = True
            self.logger.info("Core intelligence initialization complete.")
            return True
        
        except Exception as e:
            self.logger.error(f"Error initializing core intelligence: {e}")
            return False
    
    async def process_query(self, user_query, conversation_id=None):
        """Process a user query and generate a response."""
        if not self.initialized:
            return {"text": "Core intelligence is not fully initialized yet.", "error": True}
        
        try:
            # Check security
            security_check = await self.security.check_query(user_query)
            if not security_check["allowed"]:
                return {
                    "text": security_check["message"],
                    "error": True,
                    "security_issue": security_check["reason"]
                }
            
            # Store query in memory
            await self.memory.store_user_message(user_query, conversation_id)
            
            # Process query through response generator
            response = await self.response_generator.generate_response(user_query, conversation_id)
            
            # Store response in memory
            await self.memory.store_friday_message(response["text"], conversation_id)
            
            # Check for proactive suggestions
            suggestion = self.proactive_engine.peek_next_suggestion()
            if suggestion:
                response["suggestion"] = suggestion
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {"text": f"I encountered an issue processing your request. {str(e)}", "error": True}
    
    async def handle_clarification(self, original_query, clarification_response, original_intent, conversation_id=None):
        """Handle a clarification response from the user."""
        if not self.initialized:
            return {"text": "Core intelligence is not fully initialized yet.", "error": True}
        
        try:
            # Store clarification in memory
            await self.memory.store_user_message(clarification_response, conversation_id)
            
            # Process through response generator
            response = await self.response_generator.handle_clarification(
                original_query,
                clarification_response,
                original_intent
            )
            
            # Store response in memory
            await self.memory.store_friday_message(response["text"], conversation_id)
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error handling clarification: {e}")
            return {"text": f"I encountered an issue processing your clarification. {str(e)}", "error": True}
    
    def get_proactive_suggestion(self):
        """Get the next proactive suggestion if available."""
        if not self.initialized or not self.proactive_engine:
            return None
        
        return self.proactive_engine.get_next_suggestion()
    
    def update_user_preference(self, key, value, category="general"):
        """Update a user preference."""
        if not self.initialized or not self.preferences:
            return False
        
        return self.preferences.set_preference(key, value, category)
    
    def get_user_preference(self, key, default=None):
        """Get a user preference."""
        if not self.initialized or not self.preferences:
            return default
        
        return self.preferences.get_preference(key, default)
    
    def update_personality_aspect(self, aspect_path, value):
        """Update a personality aspect."""
        if not self.initialized or not self.personality:
            return False
        
        return self.personality.update_personality_aspect(aspect_path, value)
    
    def get_personality_aspect(self, aspect_path):
        """Get a personality aspect."""
        if not self.initialized or not self.personality:
            return None
        
        return self.personality.get_personality_aspect(aspect_path)
    
    def track_user_routine(self, name, pattern):
        """Track a user routine pattern."""
        if not self.initialized or not self.preferences:
            return False
        
        return self.preferences.track_routine(name, pattern)
    
    def get_user_routines(self, min_confidence=0.5):
        """Get user routines above a confidence threshold."""
        if not self.initialized or not self.preferences:
            return []
        
        return self.preferences.get_routines(min_confidence)
    
    def add_custom_suggestion(self, message, priority=0.5):
        """Add a custom proactive suggestion."""
        if not self.initialized or not self.proactive_engine:
            return None
        
        return self.proactive_engine.add_custom_suggestion(message, priority)
    
    def get_llm_performance(self):
        """Get LLM performance metrics."""
        if not self.initialized or not self.llm_interface:
            return {}
        
        return self.llm_interface.get_performance_report()
    
    async def shutdown(self):
        """Gracefully shut down the core intelligence."""
        if not self.initialized:
            return True
        
        try:
            # Stop proactive monitoring
            if self.proactive_engine:
                self.proactive_engine.stop_proactive_monitoring()
            
            # Additional cleanup as needed
            
            self.initialized = False
            self.logger.info("Core intelligence shutdown complete.")
            return True
        
        except Exception as e:
            self.logger.error(f"Error during core intelligence shutdown: {e}")
            return False