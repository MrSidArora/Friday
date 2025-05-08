"""
Friday AI - Ollama Integration Test Script
This script tests the integration with Ollama via the model manager and LLM interface.
"""

import asyncio
import sys
import os
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Simple memory system mock for testing
class MemorySystemMock:
    async def store_interaction(self, user_input, friday_response=None, context=None):
        print(f"Storing interaction: {user_input[:30]}... -> {friday_response[:30] if friday_response else 'None'}...")
        return True

async def main():
    print("Starting Ollama integration test...")
    
    try:
        # Import the required components - done here to catch import errors
        from core.model_manager import ModelManager
        from core.llm_interface import LLMInterface
        
        print("Successfully imported required modules")
        
        # Check for config files
        model_config_path = "configs/model_config.json"
        llm_config_path = "configs/llm_config.json"
        
        if not os.path.exists(model_config_path):
            print(f"WARNING: Config file not found: {model_config_path}")
            model_config_path = None
            
        if not os.path.exists(llm_config_path):
            print(f"WARNING: Config file not found: {llm_config_path}")
            llm_config_path = None
            
        # Initialize the model manager (constructor now doesn't run async code)
        print("Initializing model manager...")
        model_manager = ModelManager(config_path=model_config_path)
        
        # Now explicitly initialize the model manager asynchronously
        print("Performing async initialization of model manager...")
        init_success = await model_manager.initialize()
        if not init_success:
            print("Failed to initialize model manager. Check if Ollama is running.")
            return
            
        print(f"Model status after initialization: {model_manager.get_model_status()}")
        
        # Initialize the LLM interface
        memory_system = MemorySystemMock()
        llm_interface = LLMInterface(model_manager, memory_system, config_path=llm_config_path)
        
        # Make sure the model is loaded
        print("Ensuring model is loaded...")
        success = await llm_interface.initialize()
        if not success:
            print("Failed to initialize LLM interface!")
            return
        
        print("LLM interface initialized successfully!")
        
        # Define a test prompt
        test_prompt = "Hello Friday! Tell me a fun fact about artificial intelligence."
        
        # Define a streaming callback function
        def streaming_callback(chunk, done):
            print(chunk, end="", flush=True)
            if done:
                print("\n--- Response complete ---")
        
        # Test a basic query
        print(f"\nSending test prompt: '{test_prompt}'")
        print("Waiting for response (non-streaming)...")
        
        start_time = time.time()
        response = await llm_interface.ask(test_prompt)
        elapsed_time = time.time() - start_time
        
        print(f"\nResponse received in {elapsed_time:.2f} seconds:")
        print(f"Success: {response.get('success', False)}")
        print(f"Source: {response.get('source', 'unknown')}")
        print(f"Text: {response.get('text', 'No response text')}")
        
        # Test streaming response
        print("\n\nTesting streaming response...")
        print(f"Sending test prompt again: '{test_prompt}'")
        print("Response (streaming):")
        
        start_time = time.time()
        streaming_response = await llm_interface.ask(
            test_prompt, 
            streaming=True,
            callback=streaming_callback
        )
        elapsed_time = time.time() - start_time
        
        print(f"\nStreaming response completed in {elapsed_time:.2f} seconds")
        
        print("\nTest completed successfully!")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all required modules are installed and in the correct location.")
        print("The project structure should have a 'core' folder with model_manager.py and llm_interface.py")
        
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        print("Make sure all required files are in the correct location.")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())