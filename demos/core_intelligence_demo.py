# demos/core_intelligence_demo.py (fixed version)
import asyncio
import logging
import sys
import os

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

class MockMemorySystem:
    """A mock memory system for the demo."""
    
    async def initialize(self):
        return True
    
    async def get_recent_interactions(self, count=10):
        return [
            {"is_user": True, "text": "Hello, Friday!", "timestamp": "2023-01-01T12:00:00"},
            {"is_user": False, "text": "Hello! How can I help you today?", "timestamp": "2023-01-01T12:00:05"}
        ]
    
    async def get_user_profile(self):
        return {
            "name": "Demo User",
            "preferences": {
                "communication_style": "friendly",
                "interests": ["AI", "technology", "productivity"]
            }
        }
    
    async def store_user_message(self, message, conversation_id=None):
        logging.info(f"Stored user message: {message}")
        return True
    
    async def store_friday_message(self, message, conversation_id=None):
        logging.info(f"Stored Friday message: {message}")
        return True
    
    async def store_llm_interaction(self, interaction):
        logging.info(f"Stored LLM interaction with ID: {interaction['id']}")
        return True
    
    async def create_conversation(self):
        return "demo-conversation-id"
    
    def is_functional(self):
        return True
    
    async def shutdown(self):
        return True

class MockModelManager:
    """A mock model manager for the demo."""
    
    async def initialize(self):
        return True
    
    async def ensure_model_loaded(self, model_id):
        logging.info(f"Ensuring model loaded: {model_id}")
        return True
    
    async def generate_response(self, prompt, config=None):
        logging.info(f"Generating response for prompt: {prompt[:100]}...")
        
        # Simple logic to generate responses based on prompt content
        response_text = "I'm not sure how to respond to that."
        
        if "hello" in prompt.lower() or "greeting" in prompt.lower():
            response_text = "Hello! I'm Friday, your AI assistant. How can I help you today?"
        
        elif "how are you" in prompt.lower():
            response_text = "I'm functioning well, thank you for asking! How can I assist you today?"
        
        elif "your name" in prompt.lower():
            response_text = "My name is Friday. I'm an AI assistant designed to help you with a variety of tasks."
        
        elif "what can you do" in prompt.lower() or "capabilities" in prompt.lower():
            response_text = "I can help with answering questions, providing information, managing schedules, and assisting with a wide range of tasks as your AI assistant."
        
        elif "weather" in prompt.lower():
            response_text = "I don't currently have access to real-time weather data, but once I'm fully implemented, I'll be able to provide weather forecasts for your location."
        
        elif "thank" in prompt.lower():
            response_text = "You're welcome! Is there anything else I can help you with?"
        
        elif "quantum" in prompt.lower():
            response_text = "Quantum computing uses quantum bits or qubits that can be in multiple states at once, unlike classical bits. This allows quantum computers to solve certain problems much faster than traditional computers. Cool stuff, right?"
        
        return {
            "text": response_text,
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(prompt.split()) + len(response_text.split())
            },
            "model": "friday-demo-model",
            "finish_reason": "stop"
        }
    
    def is_model_loaded(self):
        return True
    
    async def shutdown(self):
        return True

class MockSecurityMonitor:
    """A mock security monitor for the demo."""
    
    async def initialize(self):
        return True
    
    async def check_query(self, query):
        if any(word in query.lower() for word in ["harmful", "malicious", "hack", "exploit"]):
            return {
                "allowed": False,
                "reason": "potentially_harmful",
                "message": "I cannot process potentially harmful queries."
            }
        return {
            "allowed": True,
            "reason": "safe",
            "message": ""
        }
    
    def is_active(self):
        return True
    
    async def shutdown(self):
        return True

async def run_demo():
    """Run a demonstration of the core intelligence."""
    try:
        # Import the real core intelligence
        from core.core_intelligence import CoreIntelligence
        from personality.friday_persona import FridayPersona
        from personality.preferences import UserPreferences
        from personality.proactive_engine import ProactiveEngine
        from demos.mock_response_generator import MockResponseGenerator
        
        # Create with mock dependencies
        memory = MockMemorySystem()
        model_manager = MockModelManager()
        security = MockSecurityMonitor()
        
        print("\n=== Friday AI Core Intelligence Demo ===\n")
        
        # Create a simplified LLM interface
        class MockLLMInterface:
            def __init__(self, model_manager):
                self.model_manager = model_manager
                
            async def ask(self, prompt, context=None):
                response = await self.model_manager.generate_response(prompt)
                return {
                    "text": response["text"],
                    "metadata": {
                        "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                        "model_id": response.get("model", "mock-model"),
                        "finish_reason": response.get("finish_reason", "stop")
                    },
                    "success": True
                }
        
        # Initialize the core intelligence with a simplified structure
        print("Initializing core intelligence...")
        core = CoreIntelligence(memory, model_manager, security)
        
        # Skip the full initialization and set up components manually
        core.llm_interface = MockLLMInterface(model_manager)
        core.personality = FridayPersona()
        core.preferences = UserPreferences()
        core.response_generator = MockResponseGenerator(core.llm_interface)
        core.proactive_engine = ProactiveEngine(memory, core.personality, core.preferences)
        core.proactive_engine.start_proactive_monitoring()
        core.initialized = True
        
        print("Core intelligence initialized successfully!")
        
        # Demo conversation
        print("\n=== Starting Demo Conversation ===\n")
        
        # Process a few sample queries
        demo_queries = [
            "Hello Friday!",
            "How are you today?",
            "What's your name?",
            "What can you do?",
            "Can you tell me about the weather?",
            "Thanks for the information!"
        ]
        
        for query in demo_queries:
            print(f"\nUser: {query}")
            response = await core.process_query(query)
            print(f"Friday: {response['text']}")
            
            # Check for proactive suggestions
            suggestion = core.get_proactive_suggestion()
            if suggestion:
                print(f"\n[Proactive Suggestion: {suggestion['message']}]")
        
        # Show personality modification
        print("\n=== Personality Modification Demo ===\n")
        
        print("Current formality level:", core.get_personality_aspect("tone.formality"))
        print("Updating formality to be more casual...")
        core.update_personality_aspect("tone.formality", 0.2)
        print("New formality level:", core.get_personality_aspect("tone.formality"))
        
        print("\nUser: Can you explain quantum computing?")
        response = await core.process_query("Can you explain quantum computing?")
        print(f"Friday (more casual): {response['text']}")
        
        # Clean up
        print("\n=== Shutting Down ===\n")
        await core.shutdown()
        print("Core intelligence shut down successfully!")
        
        return True
        
    except Exception as e:
        logging.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = asyncio.run(run_demo())
    sys.exit(0 if success else 1)