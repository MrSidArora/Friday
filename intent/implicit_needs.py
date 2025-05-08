# intent/implicit_needs.py
import logging

class ImplicitNeedsRecognizer:
    """Recognizes unstated needs in user requests."""
    
    def __init__(self, memory_system, llm_interface):
        """Initialize the implicit needs recognizer."""
        self.memory = memory_system
        self.llm = llm_interface
        self.logger = logging.getLogger('friday.implicit_needs')
        self.need_categories = [
            "information",
            "task_assistance",
            "emotional_support",
            "efficiency",
            "organization",
            "creativity",
            "learning",
            "reminder",
            "feedback",
            "social_connection"
        ]
    
    async def identify_implicit_needs(self, query, intent_analysis, context_analysis):
        """Identify implicit needs in the user's query."""
        # Start with any implicit needs already identified in intent analysis
        implicit_needs = intent_analysis.get("implicit_needs", [])
        
        # Enhance with deeper analysis
        enhanced_needs = await self._analyze_needs(query, intent_analysis, context_analysis)
        
        # Combine and deduplicate
        all_needs = implicit_needs.copy()
        for need in enhanced_needs:
            if need["need"] not in [n for n in all_needs]:
                all_needs.append(need["need"])
        
        return {
            "needs": all_needs,
            "detailed_analysis": enhanced_needs
        }
    
    async def _analyze_needs(self, query, intent_analysis, context_analysis):
        """Perform deeper analysis of potential implicit needs."""
        # Create a prompt for the LLM to analyze implicit needs
        prompt = self._create_needs_analysis_prompt(query, intent_analysis, context_analysis)
        
        # Get analysis from LLM
        response = await self.llm.ask(prompt=prompt, context=None)
        
        # Parse the response
        needs = self._parse_needs_analysis(response["text"])
        
        # Enrich with confidence scores and examples
        enriched_needs = []
        for need in needs:
            enriched_need = {
                "need": need,
                "confidence": self._calculate_need_confidence(need, query, intent_analysis, context_analysis),
                "examples": self._generate_need_examples(need)
            }
            enriched_needs.append(enriched_need)
        
        # Sort by confidence
        enriched_needs.sort(key=lambda x: x["confidence"], reverse=True)
        
        return enriched_needs
    
    def _create_needs_analysis_prompt(self, query, intent_analysis, context_analysis):
        """Create a prompt for implicit needs analysis."""
        # Extract relevant context
        recent_interactions = self._format_recent_interactions(
            context_analysis.get("context", {}).get("recent_interactions", [])
        )
        
        time_context = context_analysis.get("context", {}).get("time_context", {})
        time_of_day = time_context.get("time_of_day", "unknown")
        day_of_week = time_context.get("day_of_week", "unknown")
        
        primary_intent = intent_analysis.get("primary_intent", "unknown")
        
        prompt = f"""
        Analyze the user's query to identify unstated needs they might have.
        
        User Query: "{query}"
        
        Primary Intent: {primary_intent}
        
        Context:
        - Time of day: {time_of_day}
        - Day of week: {day_of_week}
        - Recent interactions: {recent_interactions}
        
        Consider these categories of implicit needs:
        - information: Need for knowledge or understanding
        - task_assistance: Need for help completing tasks
        - emotional_support: Need for empathy or encouragement
        - efficiency: Need to save time or effort
        - organization: Need for structure or planning
        - creativity: Need for new ideas or inspiration
        - learning: Need to develop skills or knowledge
        - reminder: Need to remember something important
        - feedback: Need for evaluation or assessment
        - social_connection: Need for human-like interaction
        
        For each need category that applies, provide:
        1. The need category
        2. Why you think this need is present
        3. How confident you are (low, medium, high)
        
        Format as "Category: [need]" for each identified need.
        """
        
        return prompt
    
    def _format_recent_interactions(self, interactions):
        """Format recent interactions for the prompt."""
        if not interactions:
            return "None"
        
        formatted = []
        for i, interaction in enumerate(interactions[-3:]):  # Just use the 3 most recent
            speaker = "User" if interaction.get("is_user", False) else "Friday"
            text = interaction.get("text", "")
            formatted.append(f"{speaker}: {text}")
        
        return "\n".join(formatted)
    
    def _parse_needs_analysis(self, analysis_text):
        """Parse the LLM response to extract identified needs."""
        needs = []
        
        # Look for lines with the format "Category: [need]"
        import re
        need_matches = re.findall(r'(?i)category:\s*\[([a-z_]+)\]', analysis_text)
        
        for match in need_matches:
            need = match.lower()
            if need in self.need_categories and need not in needs:
                needs.append(need)
        
        # If no structured format was found, try a less rigid approach
        if not needs:
            for category in self.need_categories:
                if category.lower() in analysis_text.lower():
                    # Look for indicators of confidence
                    pattern = re.compile(rf'(?i){category}.*?(high|medium|strong|significant|clear)', re.DOTALL)
                    if pattern.search(analysis_text):
                        if category not in needs:
                            needs.append(category)
        
        return needs
    
    def _calculate_need_confidence(self, need, query, intent_analysis, context_analysis):
        """Calculate confidence score for an identified need."""
        # This is a simplified implementation
        # In a real system, this would use more sophisticated methods
        
        base_confidence = 0.5
        
        # Adjust based on presence of need-related keywords in query
        keywords = self._get_need_keywords(need)
        query_lower = query.lower()
        keyword_matches = sum(1 for keyword in keywords if keyword in query_lower)
        keyword_factor = min(0.3, keyword_matches * 0.1)
        
        # Adjust based on intent compatibility
        primary_intent = intent_analysis.get("primary_intent", "unknown")
        intent_factor = self._get_intent_need_compatibility(primary_intent, need)
        
        # Final confidence calculation
        confidence = base_confidence + keyword_factor + intent_factor
        
        # Cap between 0.4 and 0.9
        return max(0.4, min(0.9, confidence))
    
    def _get_need_keywords(self, need):
        """Get keywords associated with a need category."""
        keywords = {
            "information": ["what", "how", "tell me", "explain", "know", "understand", "learn about"],
            "task_assistance": ["help", "do", "make", "create", "fix", "solve", "assist"],
            "emotional_support": ["feel", "stressed", "worried", "happy", "sad", "anxious", "overwhelmed"],
            "efficiency": ["quick", "fast", "efficient", "time", "busy", "hurry", "streamline"],
            "organization": ["organize", "plan", "schedule", "track", "manage", "list", "categorize"],
            "creativity": ["idea", "creative", "design", "imagine", "inspiration", "novel", "unique"],
            "learning": ["learn", "study", "practice", "understand", "master", "skill", "improve"],
            "reminder": ["remind", "forget", "remember", "later", "tomorrow", "upcoming", "schedule"],
            "feedback": ["review", "evaluate", "opinion", "think", "assessment", "critique", "feedback"],
            "social_connection": ["talk", "chat", "conversation", "connect", "discuss", "share", "together"]
        }
        
        return keywords.get(need, [])
    
    def _get_intent_need_compatibility(self, intent, need):
        """Determine compatibility between intent and need."""
        # High compatibility pairs
        high_compatibility = {
            "information_seeking": ["information", "learning"],
            "task_execution": ["task_assistance", "efficiency", "organization"],
            "opinion_seeking": ["feedback", "information"],
            "emotional_support": ["emotional_support", "social_connection"],
            "clarification": ["information", "learning"]
        }
        
        # Check if there's high compatibility
        if intent in high_compatibility and need in high_compatibility[intent]:
            return 0.2  # Significant boost
        
        # Medium compatibility - almost all intents could have some needs
        return 0.1
    
    def _generate_need_examples(self, need):
        """Generate examples of how to address a specific need."""
        examples = {
            "information": [
                "Here's what I found about [topic]...",
                "Let me explain how [subject] works..."
            ],
            "task_assistance": [
                "I can help you complete [task] by...",
                "Let me take care of [task] for you..."
            ],
            "emotional_support": [
                "I understand that [situation] can be challenging...",
                "It's natural to feel [emotion] when..."
            ],
            "efficiency": [
                "Here's a faster way to accomplish [task]...",
                "To save time, you could try..."
            ],
            "organization": [
                "Let me help you organize your [items]...",
                "Here's a structured approach for [task]..."
            ],
            "creativity": [
                "Here are some creative ideas for [task]...",
                "Have you considered approaching [problem] from [perspective]?"
            ],
            "learning": [
                "Let me teach you about [subject]...",
                "Here's how you can master [skill]..."
            ],
            "reminder": [
                "Don't forget about [event/task]...",
                "I'll remind you about [task] when..."
            ],
            "feedback": [
                "Based on [criteria], I think [opinion]...",
                "Here's my assessment of [subject]..."
            ],
            "social_connection": [
                "I'm here to chat whenever you need...",
                "Let's discuss [topic] further..."
            ]
        }
        
        return examples.get(need, ["I can help with that."])