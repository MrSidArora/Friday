# enhanced_test.py
import os
import sys
import asyncio
import argparse
import json
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import core components
from core.memory_system import MemorySystem
from core.request_router import RequestRouter
from core.security_monitor import SecurityMonitor
from core.model_manager import ModelManager

async def test_memory_system():
    """Test the memory system component."""
    print("\n--- Testing Memory System ---")
    
    # Initialize memory system
    memory = MemorySystem("configs/memory_config.json")
    
    # Test short-term memory
    print("\nTesting short-term memory...")
    await memory.store_short_term("test_key", {"message": "Hello, Friday!"})
    retrieved = await memory.get_short_term("test_key")
    print(f"Retrieved from short-term memory: {retrieved}")
    
    # Test mid-term memory
    print("\nTesting mid-term memory...")
    interaction_id = await memory.store_interaction(
        user_input="What's the weather like today?",
        friday_response="I'm sorry, I don't have access to current weather information."
    )
    print(f"Stored interaction with ID: {interaction_id}")
    
    # Test user preferences
    await memory.store_user_preference("theme", "dark")
    await memory.store_user_preference("voice", "female")
    
    # Retrieve recent interactions
    interactions = await memory.get_recent_interactions(5)
    print(f"Recent interactions: {len(interactions)}")
    for i, interaction in enumerate(interactions):
        print(f"  {i+1}. User: {interaction['user_input'][:30]}... Friday: {interaction['friday_response'][:30]}...")
    
    # Retrieve user profile
    profile = await memory.get_user_profile()
    print(f"User profile: {profile}")
    
    # Test long-term memory
    print("\nTesting long-term memory...")
    
    # Store knowledge
    knowledge_id = await memory.store_knowledge(
        "The Mixtral 8x7B is a mixture-of-experts model with 8 experts, each 7B parameters in size.",
        {"category": "AI", "topic": "language models"}
    )
    print(f"Stored knowledge with ID: {knowledge_id}")
    
    # Search knowledge
    results = await memory.search_knowledge("What is Mixtral?")
    print(f"Knowledge search results: {len(results)}")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result['text'][:50]}...")
    
    # Get memory status
    status = await memory.get_memory_status()
    print(f"\nMemory status: {json.dumps(status, indent=2)}")
    
    return memory

async def test_security_monitor():
    """Test the security monitoring component."""
    print("\n--- Testing Security Monitor ---")
    
    # Initialize security monitor
    security = SecurityMonitor("configs/security_config.json")
    
    # Start monitoring
    security.start_monitoring()
    print("Monitoring started")
    
    # Get system health
    health = security.get_system_health()
    print(f"\nSystem health: {json.dumps(health, indent=2)}")
    
    # Get detailed status
    status = security.get_detailed_status()
    print(f"\nDetailed status: {json.dumps(status, indent=2)}")
    
    # Log some test events
    security.log_api_access("test_api", {"param1": "value1", "param2": "value2"})
    security.log_internet_access("https://example.com", "Testing internet access logging")
    
    # Get alerts
    alerts = security.get_alerts()
    print(f"\nCurrent alerts: {len(alerts)}")
    for i, alert in enumerate(alerts):
        print(f"  {i+1}. {alert['level'].upper()}: {alert['title']} - {alert['message']}")
    
    return security

async def test_model_manager():
    """Test the model manager component."""
    print("\n--- Testing Model Manager ---")
    
    # Initialize model manager
    model = ModelManager("configs/model_config.json")
    
    # Get available models
    models = model.get_available_models()
    print(f"\nAvailable models: {len(models)}")
    for name, config in models.items():
        print(f"  - {name}: {config['type']} ({config['quantization']})")
    
    # Get model status
    status = model.get_model_status()
    print(f"\nModel status: {json.dumps(status, indent=2)}")
    
    # Try loading a model (simulated)
    model_name = next(iter(models.keys()))
    success = model.load_model(model_name)
    print(f"\nLoaded model '{model_name}': {success}")
    
    # Get updated status
    status = model.get_model_status()
    print(f"Updated model status: {json.dumps(status, indent=2)}")
    
    return model

async def test_request_router(memory, model):
    """Test the request router component."""
    print("\n--- Testing Request Router ---")
    
    # Initialize request router
    router = RequestRouter(memory, model)
    
    # Test various request types
    test_requests = [
        "What is artificial intelligence?",
        "Open the calculator application",
        "Tell me a story about a robot",
        "Show me the system status",
        "What's the weather like in New York?",
        "Set a reminder for tomorrow at 9 AM"
    ]
    
    for request in test_requests:
        print(f"\nProcessing request: \"{request}\"")
        response = await router.route_request(request)
        print(f"Request type: {response.get('type', 'unknown')}")
        print(f"Response: {response.get('text', 'No response')}")
        print(f"Additional data: {', '.join([f'{k}={v}' for k, v in response.items() if k not in ['text', 'type']])}")
    
    return router

async def main():
    parser = argparse.ArgumentParser(description="Friday AI Component Tests")
    parser.add_argument("--component", choices=["all", "memory", "security", "model", "router"], 
                        default="all", help="Component to test")
    args = parser.parse_args()
    
    try:
        # Ensure the config directory exists
        if not os.path.exists("configs"):
            print("Setting up configuration files...")
            from setup import setup_friday_environment
            setup_friday_environment()
        
        # Run tests based on component selection
        if args.component in ["all", "memory"]:
            memory = await test_memory_system()
        else:
            memory = None
            
        if args.component in ["all", "security"]:
            security = await test_security_monitor()
        else:
            security = None
            
        if args.component in ["all", "model"]:
            model = await test_model_manager()
        else:
            model = None
            
        if args.component in ["all", "router"]:
            if not memory:
                memory = await test_memory_system()
            if not model:
                model = await test_model_manager()
            router = await test_request_router(memory, model)
        
        print("\n--- All Tests Completed Successfully ---")
        
        # Clean up
        if security:
            security.stop_monitoring()
            
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)