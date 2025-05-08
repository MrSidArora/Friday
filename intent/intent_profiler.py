# intent/intent_profiler.py
import json
import logging
import uuid
from datetime import datetime, timedelta

class IntentProfiler:
    """Advanced intent modeling system to understand user intentions."""
    
    def __init__(self, memory_system, llm_interface):
        """Initialize the intent profiler."""
        self.memory = memory_system
        self.llm = llm_interface
        self.logger = logging.getLogger('friday.intent')
        self.intent_patterns = {}
        self.confidence_thresholds = {
            "high": 0.85,
            "medium": 0.65,
            "low": 0.45
        }
        self._load_intent_patterns()
    
    def _load_intent_patterns(self):
        """Load intent patterns from the database."""
        try:
            # This would typically load from a database - using in-memory for now
            self.intent_patterns = {
                "information_seeking": {
                    "patterns": [
                        "who is", "what is", "how does", "when did", "where is",
                        "tell me about", "explain", "describe", "define"
                    ],
                    "examples": [
                        "Who is Marie Curie?",
                        "What is quantum physics?",
                        "Tell me about climate change"
                    ],
                    "confidence": 0.9
                },
                "task_execution": {
                    "patterns": [
                        "please", "can you", "would you", "I need you to",
                        "open", "create", "send", "find", "search", "run"
                    ],
                    "examples": [
                        "Open the browser",
                        "Create a new document",
                        "Find files related to Friday AI"
                    ],
                    "confidence": 0.85
                },
                "opinion_seeking": {
                    "patterns": [
                        "what do you think", "your opinion", "do you believe",
                        "would you say", "is it better", "which is better"
                    ],
                    "examples": [
                        "What do you think about AI ethics?",
                        "Which is better for web development, React or Vue?"
                    ],
                    "confidence": 0.8
                },
                "emotional_support": {
                    "patterns": [
                        "I feel", "I'm feeling", "I am sad", "I'm happy",
                        "I'm stressed", "I'm worried", "I'm excited",
                        "this is frustrating", "that makes me"
                    ],
                    "examples": [
                        "I'm feeling overwhelmed with work",
                        "I'm excited about the new project"
                    ],
                    "confidence": 0.75
                },
                "clarification": {
                    "patterns": [
                        "what do you mean", "I don't understand", "clarify",
                        "could you explain", "you lost me", "that's confusing"
                    ],
                    "examples": [
                        "What do you mean by perceptron?",
                        "Could you clarify that last point?"
                    ],
                    "confidence": 0.9
                }
            }
        except Exception as e:
            self.logger.error(f"Error loading intent patterns: {e}")
            self.intent_patterns = {}
    
    async def analyze_intent(self, user_query, conversation_context):
        """Analyze explicit and implicit intent in user query."""
        # Prepare context for analysis
        context_window = await self.memory.get_recent_interactions(10)
        user_profile = await self.memory.get_user_profile()
        
        # Create intent analysis prompt
        intent_prompt = self._create_intent_analysis_prompt(
            user_query,
            context_window,
            user_profile
        )
        
        # Get intent analysis from LLM
        intent_analysis = await self.llm.ask(
            prompt=intent_prompt,
            context=conversation_context
        )
        
        # Parse and structure the intent analysis
        structured_intent = self._parse_intent_analysis(intent_analysis["text"])
        
        # Also do rule-based classification using known patterns
        rule_based_intent = self._classify_with_rules(user_query)
        
        # Combine LLM-based and rule-based intent analysis
        combined_intent = self._combine_intent_analyses(structured_intent, rule_based_intent)
        
        # Check confidence level
        if combined_intent["confidence"] < self.confidence_thresholds["low"]:
            # If confidence is too low, prepare clarification
            clarification = await self._prepare_clarification(
                user_query, 
                combined_intent
            )
            return {
                "requires_clarification": True,
                "clarification_question": clarification,
                "intent": combined_intent
            }
        
        return {
            "requires_clarification": False,
            "intent": combined_intent
        }
    
    def _create_intent_analysis_prompt(self, query, context, user_profile):
        """Create prompt for intent analysis."""
        prompt = f"""
        Analyze the user's query to identify both explicit and implicit intentions. Consider the recent conversation context and user profile.

        User Query: {query}

        Recent Context: {self._format_context(context)}

        User Profile:
        {self._format_profile(user_profile)}

        Please analyze and provide:
        1. Primary Intent: The main purpose of the query
        2. Secondary Intents: Any additional intentions that may be present
        3. Implicit Needs: Needs the user may have but hasn't directly expressed
        4. Emotional State: Any emotions detectable in the query
        5. Confidence Level: How certain are you about this analysis (0.0-1.0)

        Format your response with clear section headers.
        """
        return prompt
    
    def _format_context(self, context):
        """Format conversation context for the prompt."""
        if not context:
            return "No recent conversation."
        
        formatted = []
        for i, interaction in enumerate(context):
            speaker = "User" if interaction.get("is_user", False) else "Friday"
            text = interaction.get("text", "")
            timestamp = interaction.get("timestamp", "")
            formatted.append(f"{speaker} ({timestamp}): {text}")
        
        return "\n".join(formatted[-5:])  # Just use the 5 most recent interactions
    
    def _format_profile(self, profile):
        """Format user profile for the prompt."""
        if not profile:
            return "No user profile available."
        
        formatted = []
        for key, value in profile.items():
            formatted.append(f"{key}: {value}")
        
        return "\n".join(formatted)
    
    def _parse_intent_analysis(self, analysis_text):
        """Parse the LLM's analysis into structured intent data."""
        # This is a simplified parser that could be enhanced with regex or more sophisticated parsing
        intent = {
            "primary_intent": "unknown",
            "secondary_intents": [],
            "implicit_needs": [],
            "emotional_state": "neutral",
            "confidence": 0.0
        }
        
        current_section = None
        for line in analysis_text.split('\n'):
            line = line.strip()
            
            if not line:
                continue
            
            # Check for section headers
            if "primary intent:" in line.lower():
                current_section = "primary_intent"
                value = line.split(":", 1)[1].strip() if ":" in line else ""
                if value:
                    intent["primary_intent"] = value
            elif "secondary intent" in line.lower():
                current_section = "secondary_intents"
                if ":" in line:
                    value = line.split(":", 1)[1].strip()
                    if value:
                        intent["secondary_intents"].append(value)
            elif "implicit need" in line.lower():
                current_section = "implicit_needs"
                if ":" in line:
                    value = line.split(":", 1)[1].strip()
                    if value:
                        intent["implicit_needs"].append(value)
            elif "emotional state:" in line.lower():
                current_section = "emotional_state"
                value = line.split(":", 1)[1].strip() if ":" in line else ""
                if value:
                    intent["emotional_state"] = value
            elif "confidence level:" in line.lower():
                current_section = "confidence"
                if ":" in line:
                    try:
                        value = line.split(":", 1)[1].strip()
                        # Extract number from text like "0.85" or "85%"
                        import re
                        numbers = re.findall(r"[0-9.]+", value)
                        if numbers:
                            confidence = float(numbers[0])
                            # Convert percentage to decimal if needed
                            if confidence > 1.0:
                                confidence /= 100.0
                            intent["confidence"] = min(1.0, max(0.0, confidence))
                    except Exception as e:
                        self.logger.error(f"Error parsing confidence: {e}")
            elif current_section == "secondary_intents" and line:
                # Continue adding to current section
                intent["secondary_intents"].append(line)
            elif current_section == "implicit_needs" and line:
                intent["implicit_needs"].append(line)
        
        return intent
    
    def _classify_with_rules(self, query):
        """Classify intent using rule-based patterns."""
        query_lower = query.lower()
        
        top_category = None
        top_confidence = 0.0
        secondary_categories = []
        
        # Check against each category
        for category, data in self.intent_patterns.items():
            matched_patterns = 0
            for pattern in data["patterns"]:
                if pattern.lower() in query_lower:
                    matched_patterns += 1
            
            if matched_patterns > 0:
                # Calculate confidence based on matches and base confidence
                pattern_confidence = min(0.95, (matched_patterns / len(data["patterns"])) * data["confidence"])
                
                if pattern_confidence > top_confidence:
                    if top_confidence > 0:
                        secondary_categories.append({"category": top_category, "confidence": top_confidence})
                    top_category = category
                    top_confidence = pattern_confidence
                elif pattern_confidence > 0.3:  # Only add as secondary if somewhat confident
                    secondary_categories.append({"category": category, "confidence": pattern_confidence})
        
        # Sort secondary categories by confidence
        secondary_categories.sort(key=lambda x: x["confidence"], reverse=True)
        
        # If no matches, return default
        if top_category is None:
            return {
                "primary_intent": "unknown",
                "secondary_intents": [],
                "implicit_needs": [],
                "emotional_state": "neutral",
                "confidence": 0.1  # Very low confidence
            }
        
        return {
            "primary_intent": top_category,
            "secondary_intents": [sc["category"] for sc in secondary_categories[:2]],  # Top 2 secondary intents
            "implicit_needs": [],  # Rule-based doesn't detect implicit needs
            "emotional_state": "neutral",  # Rule-based doesn't detect emotion
            "confidence": top_confidence
        }
    
    def _combine_intent_analyses(self, llm_intent, rule_intent):
        """Combine LLM-based and rule-based intent analyses."""
        # If LLM has high confidence, prefer it
        if llm_intent["confidence"] >= self.confidence_thresholds["high"]:
            combined = llm_intent.copy()
            # Add rule-based secondary intents if not already present
            for intent in rule_intent["secondary_intents"]:
                if intent not in combined["secondary_intents"]:
                    combined["secondary_intents"].append(intent)
            return combined
        
        # If rule-based has high confidence, prefer it but keep LLM's implicit needs and emotion
        if rule_intent["confidence"] >= self.confidence_thresholds["high"]:
            combined = rule_intent.copy()
            combined["implicit_needs"] = llm_intent["implicit_needs"]
            combined["emotional_state"] = llm_intent["emotional_state"]
            return combined
        
        # If both have medium confidence but disagree, prefer the higher one but reduce confidence
        if llm_intent["primary_intent"] != rule_intent["primary_intent"]:
            if llm_intent["confidence"] >= rule_intent["confidence"]:
                combined = llm_intent.copy()
                combined["confidence"] = max(self.confidence_thresholds["medium"], 
                                          llm_intent["confidence"] * 0.9)
                # Add rule intent as secondary if not already there
                if rule_intent["primary_intent"] not in combined["secondary_intents"]:
                    combined["secondary_intents"].insert(0, rule_intent["primary_intent"])
            else:
                combined = rule_intent.copy()
                combined["confidence"] = max(self.confidence_thresholds["medium"], 
                                           rule_intent["confidence"] * 0.9)
                combined["implicit_needs"] = llm_intent["implicit_needs"]
                combined["emotional_state"] = llm_intent["emotional_state"]
                # Add LLM intent as secondary if not already there
                if llm_intent["primary_intent"] not in combined["secondary_intents"]:
                    combined["secondary_intents"].insert(0, llm_intent["primary_intent"])
            return combined
        
        # If they agree on primary intent, increase confidence
        combined = llm_intent.copy()
        combined["confidence"] = min(0.95, (llm_intent["confidence"] + rule_intent["confidence"]) / 1.5)
        # Merge secondary intents
        for intent in rule_intent["secondary_intents"]:
            if intent not in combined["secondary_intents"]:
                combined["secondary_intents"].append(intent)
        
        return combined
    
    async def _prepare_clarification(self, query, partial_intent):
        """Generate appropriate clarification for ambiguous intent."""
        primary = partial_intent["primary_intent"]
        secondary = partial_intent["secondary_intents"]
        confidence = partial_intent["confidence"]
        
        if primary == "unknown":
            return "I'm not sure what you're asking for. Could you rephrase or provide more details?"
        
        if confidence < 0.3:
            return f"I'm not confident I understand your request. Were you asking about {primary}?"
        
        if len(secondary) > 0:
            return f"I think you're asking about {primary}, but you might also be interested in {secondary[0]}. Is that right?"
        
        # Generate clarification based on the primary intent
        if primary == "information_seeking":
            return f"Are you looking for information about something specific related to {query}?"
        elif primary == "task_execution":
            return f"Do you want me to perform a specific task related to {query}?"
        elif primary == "opinion_seeking":
            return f"Are you asking for my perspective on {query}?"
        elif primary == "emotional_support":
            return f"Would you like to talk more about how you're feeling about {query}?"
        
        return f"Could you clarify what you'd like me to do regarding {query}?"
    
    async def learn_from_interaction(self, query, detected_intent, actual_intent, success):
        """Learn from this interaction to improve future intent detection."""
        if not success and detected_intent["confidence"] > self.confidence_thresholds["medium"]:
            # This was an incorrect high-confidence detection
            # We need to adjust our understanding
            await self._correct_intent_patterns(query, detected_intent, actual_intent)
            return True
        
        if success and detected_intent["confidence"] > self.confidence_thresholds["medium"]:
            # This was a successful high-confidence detection
            # Update our patterns to reinforce this
            await self._update_intent_patterns(query, detected_intent, actual_intent)
            return True
        
        return False
    
    async def _update_intent_patterns(self, query, detected_intent, actual_intent):
        """Update intent patterns based on successful detection."""
        # For successful detections, we might:
        # 1. Add the query as an example
        # 2. Extract new patterns
        
        primary_intent = detected_intent["primary_intent"]
        if primary_intent in self.intent_patterns:
            # Add as example if not too many examples already
            if len(self.intent_patterns[primary_intent]["examples"]) < 10:
                if query not in self.intent_patterns[primary_intent]["examples"]:
                    self.intent_patterns[primary_intent]["examples"].append(query)
            
            # Extract potential new patterns (simplified approach)
            # In a real system, this would be more sophisticated
            words = query.lower().split()
            for i in range(len(words) - 1):
                potential_pattern = f"{words[i]} {words[i+1]}"
                if (len(potential_pattern) > 5 and 
                    potential_pattern not in self.intent_patterns[primary_intent]["patterns"]):
                    # Add if pattern appears in multiple examples
                    example_count = sum(1 for ex in self.intent_patterns[primary_intent]["examples"] 
                                      if potential_pattern in ex.lower())
                    if example_count >= 2:
                        self.intent_patterns[primary_intent]["patterns"].append(potential_pattern)
        
        # In a real implementation, we would persist these updates to a database
        return True
    
    async def _correct_intent_patterns(self, query, detected_intent, actual_intent):
        """Correct intent patterns based on incorrect detection."""
        # For incorrect detections, we might:
        # 1. Remove misleading patterns
        # 2. Adjust confidence scores
        
        detected_primary = detected_intent["primary_intent"]
        actual_primary = actual_intent["primary_intent"]
        
        if detected_primary in self.intent_patterns:
            # Reduce confidence slightly
            self.intent_patterns[detected_primary]["confidence"] = max(
                0.5, self.intent_patterns[detected_primary]["confidence"] * 0.95
            )
            
            # Check what patterns matched and led to the misclassification
            matched_patterns = []
            for pattern in self.intent_patterns[detected_primary]["patterns"]:
                if pattern.lower() in query.lower():
                    matched_patterns.append(pattern)
            
            # If a pattern appears in multiple intent categories and led to misclassification,
            # consider removing it from the wrong category
            if matched_patterns and actual_primary in self.intent_patterns:
                for pattern in matched_patterns:
                    # Check if pattern also appears in the correct category
                    if pattern in self.intent_patterns[actual_primary]["patterns"]:
                        # Pattern is ambiguous, might want to remove from detected category
                        if pattern in self.intent_patterns[detected_primary]["patterns"]:
                            self.intent_patterns[detected_primary]["patterns"].remove(pattern)
        
        # Ensure the correct intent category exists
        if actual_primary not in self.intent_patterns and actual_primary != "unknown":
            self.intent_patterns[actual_primary] = {
                "patterns": [],
                "examples": [query],
                "confidence": 0.7
            }
        
        # In a real implementation, we would persist these updates to a database
        return True