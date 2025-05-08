# intent/response_generator.py
import logging

class ResponseGenerator:
    """Generates context-aware, intent-aware responses."""
    
    def __init__(self, llm_interface, intent_profiler, context_analyzer, implicit_needs, personality):
        """Initialize the response generator."""
        self.llm = llm_interface
        self.intent_profiler = intent_profiler
        self.context_analyzer = context_analyzer
        self.implicit_needs = implicit_needs
        self.personality = personality
        self.logger = logging.getLogger('friday.response_generator')
    
    async def generate_response(self, user_query, conversation_id=None):
        """Generate a response based on intents and context."""
        # Analyze intent
        intent_analysis = await self.intent_profiler.analyze_intent(user_query, None)
        
        # If clarification needed, return that immediately
        if intent_analysis.get("requires_clarification", False):
            return {
                "text": intent_analysis["clarification_question"],
                "requires_clarification": True,
                "detected_intent": intent_analysis["intent"]
            }
        
        # Analyze context
        context_analysis = await self.context_analyzer.analyze_context(user_query)
        
        # Analyze implicit needs
        needs_analysis = await self.implicit_needs.identify_implicit_needs(
            user_query, 
            intent_analysis["intent"], 
            context_analysis
        )
        
        # Get personality modifiers
        personality_modifiers = self.personality.get_prompt_modifiers()
        
        # Build comprehensive response prompt
        response_prompt = self._create_response_prompt(
            user_query,
            intent_analysis["intent"],
            context_analysis,
            needs_analysis,
            personality_modifiers
        )
        
        # Generate response using LLM
        response = await self.llm.ask(prompt=response_prompt, context=None)
        
        return {
            "text": response["text"],
            "detected_intent": intent_analysis["intent"],
            "implicit_needs": needs_analysis["needs"],
            "context_insights": context_analysis["context_insights"]
        }
    
    def _create_response_prompt(self, query, intent, context, needs, personality):
        """Create a comprehensive prompt for response generation."""
        # Extract key information
        primary_intent = intent["primary_intent"]
        secondary_intents = ", ".join(intent["secondary_intents"][:2]) if intent["secondary_intents"] else "none"
        emotional_state = intent["emotional_state"]
        
        # Format time context
        time_context = context["context"]["time_context"]
        time_of_day = time_context["time_of_day"]
        day_of_week = time_context["day_of_week"]
        
        # Format implicit needs
        top_needs = ", ".join(needs["needs"][:3]) if needs["needs"] else "none detected"
        
        # Format personality modifiers
        tone_modifiers = "\n- ".join(personality["tone_modifiers"]) if personality["tone_modifiers"] else "neutral tone"
        behavior_modifiers = "\n- ".join(personality["behavior_modifiers"]) if personality["behavior_modifiers"] else "standard behavior"
        ethical_guidelines = "\n- ".join(personality["ethical_guidelines"]) if personality["ethical_guidelines"] else "standard ethics"
        
        # Build the prompt
        prompt = f"""
        Generate a response to the user's query, taking into account their intent, context, implicit needs, and Friday's personality.
        
        User Query: "{query}"
        
        Intent Analysis:
        - Primary Intent: {primary_intent}
        - Secondary Intents: {secondary_intents}
        - Emotional State: {emotional_state}
        
        Context:
        - Time of Day: {time_of_day}
        - Day of Week: {day_of_week}
        
        Implicit Needs:
        - Top Needs: {top_needs}
        
        Friday's Personality:
        - Tone Modifiers:
          - {tone_modifiers}
        - Behavior Modifiers:
          - {behavior_modifiers}
        - Ethical Guidelines:
          - {ethical_guidelines}
        
        Generate a natural, helpful response that addresses the user's explicit query while also considering their implicit needs. Maintain Friday's personality throughout.
        
        Response:
        """
        
        return prompt
    
    async def handle_clarification(self, original_query, clarification_response, original_intent):
        """Handle user clarification to a previous intent question."""
        # Analyze if the clarification confirms or corrects the original intent
        updated_intent = await self._analyze_clarification(
            original_query,
            clarification_response,
            original_intent
        )
        
        # If the user provided a correction, learn from it
        if updated_intent["primary_intent"] != original_intent["primary_intent"]:
            await self.intent_profiler.learn_from_interaction(
                original_query,
                original_intent,
                updated_intent,
                False  # Not successful
            )
        else:
            # Intent was correct, just needed clarification
            await self.intent_profiler.learn_from_interaction(
                original_query,
                original_intent,
                updated_intent,
                True  # Successful
            )
        
        # Now generate a response with the updated intent
        context_analysis = await self.context_analyzer.analyze_context(original_query)
        
        needs_analysis = await self.implicit_needs.identify_implicit_needs(
            original_query, 
            updated_intent, 
            context_analysis
        )
        
        personality_modifiers = self.personality.get_prompt_modifiers()
        
        response_prompt = self._create_clarified_response_prompt(
            original_query,
            clarification_response,
            updated_intent,
            context_analysis,
            needs_analysis,
            personality_modifiers
        )
        
        response = await self.llm.ask(prompt=response_prompt, context=None)
        
        return {
            "text": response["text"],
            "updated_intent": updated_intent,
            "implicit_needs": needs_analysis["needs"]
        }
    
    async def _analyze_clarification(self, original_query, clarification_response, original_intent):
        """Analyze user's clarification to determine the correct intent."""
        prompt = f"""
        Analyze the user's clarification to determine the correct intent.
        
        Original Query: "{original_query}"
        Original Intent Detected: {original_intent["primary_intent"]}
        User Clarification: "{clarification_response}"
        
        Based on the clarification, what is the user's actual intent?
        1. Is the originally detected intent correct or incorrect?
        2. What is the correct primary intent?
        3. Are there any secondary intents?
        
        Format your response with clear section headers.
        """
        
        clarification_analysis = await self.llm.ask(prompt=prompt, context=None)
        
        # Parse the analysis to get the updated intent
        updated_intent = self._parse_clarification_analysis(
            clarification_analysis["text"],
            original_intent
        )
        
        return updated_intent
    
    def _parse_clarification_analysis(self, analysis_text, original_intent):
        """Parse the clarification analysis to extract the updated intent."""
        # This is a simplified parser
        updated_intent = original_intent.copy()
        
        # Look for confirmation or correction
        is_correct = True
        if "incorrect" in analysis_text.lower():
            is_correct = False
        
        # If the intent was incorrect, look for the correct intent
        if not is_correct:
            # Try to extract primary intent
            import re
            primary_match = re.search(r'(?i)primary intent:?\s*([a-z_]+)', analysis_text)
            if primary_match:
                updated_intent["primary_intent"] = primary_match.group(1).lower()
            
            # Try to extract secondary intents
            secondary_matches = re.findall(r'(?i)secondary intent[s]?:?\s*([a-z_,\s]+)', analysis_text)
            if secondary_matches:
                secondary_intents = []
                for match in secondary_matches:
                    intents = [i.strip() for i in match.split(',')]
                    secondary_intents.extend(intents)
                updated_intent["secondary_intents"] = secondary_intents
        
        return updated_intent
    
    def _create_clarified_response_prompt(self, original_query, clarification, intent, context, needs, personality):
        """Create a prompt for generating a response after clarification."""
        primary_intent = intent["primary_intent"]
        secondary_intents = ", ".join(intent["secondary_intents"][:2]) if intent["secondary_intents"] else "none"
        
        top_needs = ", ".join(needs["needs"][:3]) if needs["needs"] else "none detected"
        
        tone_modifiers = "\n- ".join(personality["tone_modifiers"]) if personality["tone_modifiers"] else "neutral tone"
        behavior_modifiers = "\n- ".join(personality["behavior_modifiers"]) if personality["behavior_modifiers"] else "standard behavior"
        
        prompt = f"""
        Generate a response now that the user's intent has been clarified.
        
        Original Query: "{original_query}"
        User Clarification: "{clarification}"
        
        Confirmed Intent:
        - Primary Intent: {primary_intent}
        - Secondary Intents: {secondary_intents}
        
        Implicit Needs:
        - Top Needs: {top_needs}
        
        Friday's Personality:
        - Tone Modifiers:
          - {tone_modifiers}
        - Behavior Modifiers:
          - {behavior_modifiers}
        
        Generate a natural, helpful response that addresses the user's clarified intent. Be conversational and acknowledge their clarification. Maintain Friday's personality throughout.
        
        Response:
        """
        
        return prompt