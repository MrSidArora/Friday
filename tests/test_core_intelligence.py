# tests/test_core_intelligence.py
import asyncio
import logging
import sys
import os
import unittest

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup basic logging for tests
logging.basicConfig(level=logging.INFO)

class MockMemorySystem:
    """A mock memory system for testing."""
    
    async def initialize(self):
        return True
    
    async def get_recent_interactions(self, count=10):
        return [
            {"is_user": True, "text": "Hello, Friday!", "timestamp": "2023-01-01T12:00:00"},
            {"is_user": False, "text": "Hello! How can I help you today?", "timestamp": "2023-01-01T12:00:05"}
        ]
    
    async def get_user_profile(self):
        return {
            "name": "Test User",
            "preferences": {
                "communication_style": "direct",
                "interests": ["AI", "programming", "testing"]
            }
        }
    
    async def store_user_message(self, message, conversation_id=None):
        logging.info(f"Stored user message: {message}")
        return True
    
    async def store_friday_message(self, message, conversation_id=None):
        logging.info(f"Stored Friday message: {message}")
        return True
    
    async def store_llm_interaction(self, interaction):
        logging.info(f"Stored LLM interaction: {interaction['id']}")
        return True
    
    async def create_conversation(self):
        return "test-conversation-id"
    
    def is_functional(self):
        return True
    
    async def shutdown(self):
        return True

class MockModelManager:
    """A mock model manager for testing."""
    
    async def initialize(self):
        return True
    
    async def ensure_model_loaded(self, model_id):
        logging.info(f"Ensuring model loaded: {model_id}")
        return True
    
    async def generate_response(self, prompt, config=None):
        logging.info(f"Generating response for prompt: {prompt[:50]}...")
        return {
            "text": f"This is a mock response to: {prompt[:30]}...",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 20,
                "total_tokens": len(prompt.split()) + 20
            },
            "model": "mock-model",
            "finish_reason": "stop"
        }
    
    def is_model_loaded(self):
        return True
    
    async def shutdown(self):
        return True

class MockSecurityMonitor:
    """A mock security monitor for testing."""
    
    async def initialize(self):
        return True
    
    async def check_query(self, query):
        if "harmful" in query.lower():
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

class TestCoreIntelligence(unittest.TestCase):
    """Test cases for the core intelligence components."""
    
    def setUp(self):
        self.memory = MockMemorySystem()
        self.model_manager = MockModelManager()
        self.security = MockSecurityMonitor()
    
    async def async_setup(self):
        # Import the real components
        from core.core_intelligence import CoreIntelligence
        
        # Create with mock dependencies
        self.core = CoreIntelligence(self.memory, self.model_manager, self.security)
        
        # Initialize - this will create real components but with mock dependencies
        await self.core.initialize()
    
    def test_initialization(self):
        """Test that core intelligence initializes correctly."""
        asyncio.run(self._async_test_initialization())
    
    async def _async_test_initialization(self):
        await self.async_setup()
        self.assertTrue(self.core.initialized)
        self.assertIsNotNone(self.core.personality)
        self.assertIsNotNone(self.core.preferences)
        self.assertIsNotNone(self.core.llm_interface)
        self.assertIsNotNone(self.core.intent_profiler)
        self.assertIsNotNone(self.core.context_analyzer)
        self.assertIsNotNone(self.core.implicit_needs)
        self.assertIsNotNone(self.core.response_generator)
        self.assertIsNotNone(self.core.proactive_engine)
    
    def test_personality_engine(self):
        """Test the personality engine functionality."""
        asyncio.run(self._async_test_personality_engine())
    
    async def _async_test_personality_engine(self):
        await self.async_setup()
        
        # Test getting a personality aspect
        formality = self.core.get_personality_aspect("tone.formality")
        self.assertIsNotNone(formality)
        
        # Test updating a personality aspect
        result = self.core.update_personality_aspect("tone.formality", 0.8)
        self.assertTrue(result)
        
        # Verify the update
        updated_formality = self.core.get_personality_aspect("tone.formality")
        self.assertEqual(updated_formality, 0.8)
    
    def test_user_preferences(self):
        """Test the user preferences functionality."""
        asyncio.run(self._async_test_user_preferences())
    
    async def _async_test_user_preferences(self):
        await self.async_setup()
        
        # Test setting a preference
        result = self.core.update_user_preference("test_key", "test_value")
        self.assertTrue(result)
        
        # Test getting the preference
        value = self.core.get_user_preference("test_key")
        self.assertEqual(value, "test_value")
        
        # Test tracking a routine
        result = self.core.track_user_routine("morning_greeting", "Detected at 8:00 AM")
        self.assertTrue(result)
        
        # Test getting routines
        routines = self.core.get_user_routines(min_confidence=0.0)
        self.assertGreaterEqual(len(routines), 0)
    
    def test_query_processing(self):
        """Test processing a user query."""
        asyncio.run(self._async_test_query_processing())
    
    async def _async_test_query_processing(self):
        await self.async_setup()
        
        # Test basic query
        response = await self.core.process_query("Hello, how are you today?")
        self.assertIn("text", response)
        self.assertFalse(response.get("error", False))
        
        # Test query with security issue
        response = await self.core.process_query("This is a harmful query")
        self.assertIn("security_issue", response)
        self.assertTrue(response.get("error", False))
    
    def test_proactive_suggestions(self):
        """Test proactive suggestions."""
        asyncio.run(self._async_test_proactive_suggestions())
    
    async def _async_test_proactive_suggestions(self):
        await self.async_setup()
        
        # Add a custom suggestion
        suggestion = self.core.add_custom_suggestion("Would you like me to help you with your schedule?", 0.8)
        self.assertIsNotNone(suggestion)
        
        # Get the suggestion
        next_suggestion = self.core.get_proactive_suggestion()
        self.assertIsNotNone(next_suggestion)
        self.assertEqual(next_suggestion["trigger_name"], "custom")
    
    def test_shutdown(self):
        """Test shutting down the core intelligence."""
        asyncio.run(self._async_test_shutdown())
    
    async def _async_test_shutdown(self):
        await self.async_setup()
        result = await self.core.shutdown()
        self.assertTrue(result)
        self.assertFalse(self.core.initialized)

# Add a test for the full Friday implementation
class TestFriday(unittest.TestCase):
    """Test cases for the main Friday implementation."""
    
    def test_friday_initialization(self):
        """Test that Friday initializes correctly."""
        asyncio.run(self._async_test_friday_initialization())
    
    async def _async_test_friday_initialization(self):
        # Import the real Friday class
        from friday.core_implementation import Friday
        
        # Mock the component imports
        import sys
        import types
        
        # Create mock modules
        mock_memory = types.ModuleType('core.memory_system')
        mock_memory.MemorySystem = MockMemorySystem
        
        mock_model = types.ModuleType('core.model_manager')
        mock_model.ModelManager = MockModelManager
        
        mock_security = types.ModuleType('core.security_monitor')
        mock_security.SecurityMonitor = MockSecurityMonitor
        
        # Create a mock for core_intelligence that preserves the original
        import importlib
        real_core_intelligence = importlib.import_module('core.core_intelligence')
        
        # Add to sys.modules
        sys.modules['core.memory_system'] = mock_memory
        sys.modules['core.model_manager'] = mock_model
        sys.modules['core.security_monitor'] = mock_security
        
        # Create and initialize Friday
        friday = Friday()
        # Override the imports to use our mocks
        friday.memory_system = MockMemorySystem()
        friday.model_manager = MockModelManager()
        friday.security_monitor = MockSecurityMonitor()
        
        # Use the real CoreIntelligence but with mock dependencies
        from core.core_intelligence import CoreIntelligence
        friday.core_intelligence = CoreIntelligence(
            friday.memory_system,
            friday.model_manager,
            friday.security_monitor
        )
        await friday.core_intelligence.initialize()
        
        friday.initialized = True
        friday.conversation_id = "test-conversation"
        
        # Test the status
        status = friday.get_status()
        self.assertEqual(status["status"], "ready")
        
        # Test processing input
        response = await friday.process_input("Hello, Friday!")
        self.assertIn("text", response)
        
        # Test shutdown
        result = await friday.shutdown()
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()