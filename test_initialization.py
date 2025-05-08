# test_initialization.py
import asyncio
from core.memory_system import MemorySystem
from core.request_router import RequestRouter
from core.security_monitor import SecurityMonitor
from core.model_manager import ModelManager

async def test_components():
    """Test that all core components initialize and interact properly."""
    print("Testing Friday AI core components...")
    
    # Initialize components
    print("\n1. Initializing Security Monitor")
    security = SecurityMonitor()
    security.start_monitoring()
    security_status = security.get_system_health()
    print(f"   Security Status: {security_status['status']}")
    
    print("\n2. Initializing Memory System")
    memory = MemorySystem()
    memory_status = await memory.get_memory_status()
    print(f"   Memory Status: {memory_status}")
    
    print("\n3. Initializing Model Manager")
    model = ModelManager()
    model_status = model.get_model_status()
    print(f"   Model Status: {model_status}")
    
    print("\n4. Initializing Request Router")
    router = RequestRouter(memory, model)
    
    print("\n5. Testing Request Routing")
    test_queries = [
        "What is the capital of France?",
        "Open the calculator app",
        "Tell me a story about robots",
        "Show me the system status"
    ]
    
    for query in test_queries:
        print(f"\n   Query: {query}")
        response = await router.route_request(query)
        print(f"   Response Type: {response.get('type', 'unknown')}")
        print(f"   Response: {response.get('text', 'No response')}")
    
    print("\n6. Testing Memory Storage")
    await memory.store_short_term("test_key", {"message": "This is a test"})
    retrieved = await memory.get_short_term("test_key")
    print(f"   Stored and retrieved from short-term memory: {retrieved}")
    
    interaction_id = await memory.store_interaction(
        user_input="Hello Friday",
        friday_response="Hello! How can I help you today?"
    )
    print(f"   Stored interaction with ID: {interaction_id}")
    
    recent = await memory.get_recent_interactions(1)
    print(f"   Retrieved recent interaction: {recent}")
    
    print("\nTest completed!")
    
    # Clean up
    security.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(test_components())