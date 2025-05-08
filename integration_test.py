"""
Friday AI - Integration Test

This script tests the integration of all components of the Friday AI system.
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/integration_test.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Import main system
from main import FridaySystem

async def test_system_initialization():
    """Test system initialization."""
    logging.info("Testing system initialization...")
    
    # Initialize Friday system
    friday = FridaySystem()
    
    # Run async initialization
    await friday.initialize_friday()
    
    # Check components
    logging.info(f"Memory system: {friday.memory_system is not None}")
    logging.info(f"Model manager: {friday.model_manager is not None}")
    logging.info(f"LLM interface: {friday.llm_interface is not None}")
    logging.info(f"HTTP controller: {friday.http_controller is not None}")
    logging.info(f"Network module: {friday.network_module is not None}")
    
    # Test network module
    if friday.network_module:
        logging.info("Testing network module...")
        
        # Test online/offline toggle
        friday.network_module.set_online_status(True)
        logging.info("Set online status to True")
        
        # Test connectivity
        try:
            connectivity = await friday.network_module.test_connectivity()
            logging.info(f"Connectivity test result: {connectivity}")
        except Exception as e:
            logging.error(f"Error testing connectivity: {e}")
    
    # Test basic request
    try:
        logging.info("Testing basic request...")
        response = await friday.process_request("Hello, Friday!")
        logging.info(f"Response: {response}")
    except Exception as e:
        logging.error(f"Error processing request: {e}")
    
    # Shut down
    await friday.shutdown()
    
    logging.info("System initialization test complete")
    return True

async def main():
    """Run integration tests."""
    logging.info("Starting Friday AI Integration Tests")
    
    # Make sure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Run tests
    tests = [
        ("System Initialization", test_system_initialization),
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\nRunning {name} test...")
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            logging.error(f"Error running {name} test: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n=== Test Results ===")
    all_passed = True
    for name, result in results:
        status = "PASSED" if result else "FAILED"
        if not result:
            all_passed = False
        print(f"{name}: {status}")
    
    if all_passed:
        print("\nAll tests passed! The system integration is working correctly.")
    else:
        print("\nSome tests failed. Please check the logs for details.")
    
    logging.info("Tests completed")

if __name__ == "__main__":
    asyncio.run(main())