"""
Friday AI - Request Router
Classifies and routes incoming requests to appropriate handlers based on intent and content.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable

class RequestRouter:
    def __init__(self, memory_system=None, model_manager=None, llm_interface=None):
        """Initialize the request router.
        
        Args:
            memory_system: Reference to the memory system
            model_manager: Reference to the model manager
            llm_interface: Reference to the LLM interface
        """
        self.memory_system = memory_system
        self.model_manager = model_manager
        self.llm_interface = llm_interface
        self.logger = logging.getLogger("request_router")

        # Register handlers for different request types
        self.handlers = {
            "conversation": self._handle_conversation,
            "command": self._handle_command,
            "question": self._handle_question,
            "system": self._handle_system
        }
        
        # Command patterns for quick identification
        self.command_patterns = [
            r"^(Friday,? )?(please |can you |would you )?(open|run|execute|start|launch) ",
            r"^(Friday,? )?(please |can you |would you )?(find|search|look for|locate) ",
            r"^(Friday,? )?(please |can you |would you )?(close|exit|quit|stop|shut down) ",
            r"^(Friday,? )?(please |can you |would you )?(create|make|generate|write) ",
            r"^(Friday,? )?(please |can you |would you )?(play|pause|resume|stop|skip) ",
            r"^(Friday,? )?(please |can you |would you )?(set|configure|change|update) "
        ]
        
        # System command indicators
        self.system_patterns = [
            r"(system|memory|model|security) (status|health|usage)",
            r"(reload|reset|restart|shutdown) (friday|system|memory|model)",
            r"(enable|disable) (feature|module|component)",
            r"update (configuration|settings)"
        ]
        
        # External API indicators
        self.external_api_indicators = [
            "weather", "news", "stock", "translate", "map", "flight", "movie"
        ]
    
    async def route_request(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Route the incoming request to the appropriate handler.
        
        Args:
            user_input: User's input text
            context: Additional context about the request
            
        Returns:
            Response from the appropriate handler
        """
        if not context:
            context = {}
            
        # Store user input in memory if available
        if self.memory_system:
            try:
                await self.memory_system.store_interaction({
                    "role": "user",
                    "content": user_input,
                    "timestamp": None  # Memory system will add timestamp
                })
                self.logger.debug("User interaction stored in memory")
            except Exception as e:
                self.logger.error(f"Error storing user interaction in memory: {e}")
            
        # Classify the request
        request_type, confidence = await self._classify_request(user_input)
        
        # Log the classification
        self.logger.info(f"Request classified as {request_type} with confidence {confidence}")
        
        # Prepare intent information for LLM
        intent = {
            "query_type": request_type,
            "classification_confidence": confidence,
            "requires_external_resources": False,
            "requires_internet": False
        }
        
        # Check if request might need internet access
        if request_type == "question":
            needs_search = self._check_if_needs_search(user_input)
            intent["requires_external_resources"] = needs_search
            intent["requires_internet"] = needs_search
            # Don't include debug info in the response
            self.logger.debug(f"Need to search: {needs_search}")
        
        # Try to use LLM interface if available
        if self.llm_interface:
            try:
                # Check if model is loaded
                model_loaded = self.model_manager and self.model_manager.is_model_loaded() if self.model_manager else False
                
                if not model_loaded and self.model_manager:
                    # Try to load model if not loaded
                    self.logger.info("Model not loaded, attempting to load default model")
                    try:
                        model_loaded = await self.model_manager.load_default_model()
                        self.logger.info(f"Model loading result: {model_loaded}")
                    except Exception as e:
                        self.logger.error(f"Error loading model: {e}")
                
                if model_loaded or not self.model_manager:
                    # Process with LLM
                    self.logger.info("Processing request with LLM interface")
                    self.logger.info(f"Calling LLM interface with input: '{user_input[:30]}...'")
                    response = await self.llm_interface.ask(user_input, context=context, intent=intent)
                    self.logger.info("LLM response received successfully")
                    
                    # Store response in memory if available
                    if self.memory_system and isinstance(response, dict) and "text" in response:
                        try:
                            await self.memory_system.store_interaction({
                                "role": "friday",
                                "content": response["text"],
                                "timestamp": None  # Memory system will add timestamp
                            })
                            self.logger.debug("Friday response stored in memory")
                        except Exception as e:
                            self.logger.error(f"Error storing Friday response in memory: {e}")
                    
                    return response
                else:
                    # No model available
                    self.logger.warning("No model available for processing")
                    response = {
                        "text": f"I've received your message but my language model is not loaded at the moment. I'll use my basic capabilities to assist you."
                    }
                    
                    # Use basic handlers as fallback
                    handler_response = await self.handlers[request_type](user_input, {**context, "intent": intent})
                    
                    # Merge responses, prioritizing basic handler
                    response = {**response, **handler_response}
                    return response
            except Exception as e:
                self.logger.error(f"Error getting response from LLM interface: {e}")
                # Fallback to basic handling
                return await self._basic_fallback_response(user_input, request_type, context, intent)
        else:
            # No LLM interface available
            self.logger.warning("LLM interface not available")
            return await self._basic_fallback_response(user_input, request_type, context, intent)
    
    async def _basic_fallback_response(self, user_input: str, request_type: str, context: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a basic fallback response when LLM is not available.
        
        Args:
            user_input: User's input text
            request_type: Type of request
            context: Request context
            intent: Intent information
            
        Returns:
            Response dictionary
        """
        # Use the appropriate handler based on request type
        handler = self.handlers.get(request_type, self._handle_conversation)
        try:
            response = await handler(user_input, {**context, "intent": intent})
            
            # Store response in memory if available
            if self.memory_system and "text" in response:
                try:
                    await self.memory_system.store_interaction({
                        "role": "friday",
                        "content": response["text"],
                        "timestamp": None  # Memory system will add timestamp
                    })
                except Exception as e:
                    self.logger.error(f"Error storing Friday response in memory: {e}")
                    
            return response
        except Exception as e:
            self.logger.error(f"Error in request handler: {e}")
            return {
                "text": "I'm sorry, I encountered an issue while processing your request. Let me know if you'd like to try something else.",
                "type": request_type,
                "error": True
            }
    
    async def _classify_request(self, user_input: str) -> Tuple[str, float]:
        """Classify the type of request.
        
        Args:
            user_input: User's input text
            
        Returns:
            Tuple of (request_type, confidence)
        """
        # Check for direct command patterns
        for pattern in self.command_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return "command", 0.9
        
        # Check for system commands
        for pattern in self.system_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return "system", 0.9
        
        # Check for question indicators
        if "?" in user_input or user_input.lower().startswith(("what", "who", "where", "when", "why", "how", "can", "could", "would", "is", "are", "do", "does")):
            return "question", 0.8
        
        # Default to conversation with medium confidence
        return "conversation", 0.6
    
    async def _handle_conversation(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general conversation requests.
        
        Args:
            user_input: User's input text
            context: Request context
            
        Returns:
            Response dictionary
        """
        # Basic response for when no LLM is available
        return {
        "text": f"I received your message: '{user_input}'. I'm currently running with limited capabilities because my language model isn't fully loaded. You can try restarting the system or check the logs to ensure the model is properly initialized.",
        "type": "conversation"
        }
    
    async def _handle_command(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle command requests.
        
        Args:
            user_input: User's input text
            context: Request context
            
        Returns:
            Response dictionary
        """
        # Basic command response for when no LLM is available
        return {
            "text": "I understand you'd like me to perform a task. I'll need my language model to be fully loaded to process complex commands.",
            "type": "command"
        }
    
    async def _handle_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle question requests.
        
        Args:
            user_input: User's input text
            context: Request context
            
        Returns:
            Response dictionary
        """
        # Basic question response for when no LLM is available
        return {
            "text": "I'll need my language model to be fully loaded to answer your question comprehensively.",
            "type": "question"
        }
    
    async def _handle_system(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system-related requests.
        
        Args:
            user_input: User's input text
            context: Request context
            
        Returns:
            Response dictionary
        """
        # Basic system response for when no LLM is available
        # Try to gather actual system information if possible
        model_status = "not loaded"
        if self.model_manager:
            try:
                model_status = "loaded" if self.model_manager.is_model_loaded() else "not loaded"
            except:
                pass
                
        return {
            "text": f"Friday system is operational. Language model is {model_status}.",
            "type": "system"
        }
    
    def _check_if_needs_search(self, user_input: str) -> bool:
        """Check if a question likely needs external search.
        
        Args:
            user_input: User's input text
            
        Returns:
            Boolean indicating if search is needed
        """
        lowered = user_input.lower()
        
        # Check for current events/data indicators
        current_indicators = ["current", "latest", "recent", "today", "now", "trending"]
        if any(indicator in lowered for indicator in current_indicators):
            return True
            
        # Check for external API indicators
        if any(indicator in lowered for indicator in self.external_api_indicators):
            return True
        
        # Default to not needing search
        return False