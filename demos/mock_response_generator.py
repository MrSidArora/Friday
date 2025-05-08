# demos/mock_response_generator.py
import logging

class MockResponseGenerator:
    """A simplified response generator for demos."""
    
    def __init__(self, llm_interface):
        """Initialize the response generator."""
        self.llm = llm_interface
        self.logger = logging.getLogger('friday.mock_response_generator')
    
    async def generate_response(self, user_query, conversation_id=None):
        """Generate a response based on the user query."""
        # Create a simple prompt for the LLM
        prompt = f"""
        Generate a response to the user's query:
        
        User Query: "{user_query}"
        """
        
        # Get response from LLM
        response = await self.llm.ask(prompt=prompt, context=None)
        
        return {
            "text": response["text"],
            "detected_intent": {"primary_intent": "unknown", "confidence": 0.5},
            "implicit_needs": [],
            "context_insights": []
        }
    
    async def handle_clarification(self, original_query, clarification_response, original_intent):
        """Handle user clarification to a previous intent question."""
        # Create a simple prompt for the LLM
        prompt = f"""
        Generate a response based on the user's clarification:
        
        Original Query: "{original_query}"
        User Clarification: "{clarification_response}"
        """
        
        # Get response from LLM
        response = await self.llm.ask(prompt=prompt, context=None)
        
        return {
            "text": response["text"],
            "updated_intent": original_intent,
            "implicit_needs": []
        }