"""
Friday AI - Network Integration Test
This script tests the integration of all network components.
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
        logging.FileHandler("logs/test_network.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Import network components - make sure these paths are correct
sys.path.append('.')  # Add the project root to the path
from network.internet_controller import InternetController
from network.api_logger import ApiLogger
from network.api_interface import ApiInterface
from network.network_integration import NetworkModule

# Mock HTTP controller for testing
class MockHttpController:
    async def handle_request(self, method, endpoint, data):
        logging.info(f"Mock request: {method} {endpoint}")
        logging.info(f"Data: {data}")
        
        # Simple mock response
        if endpoint == "/web_request":
            url = data.get("url", "")
            method = data.get("method", "GET")
            
            # Simple implementation to actually make the request
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    if method == "GET":
                        async with session.get(url) as response:
                            status = response.status
                            try:
                                json_data = await response.json()
                                return {"success": True, "data": json_data, "status": status}, 200
                            except:
                                text_data = await response.text()
                                return {"success": True, "data": text_data, "status": status}, 200
                except Exception as e:
                    return {"success": False, "error": str(e)}, 400
                    
        return {"success": False, "error": "Not implemented"}, 400
        
    async def request_domain_approval(self, domain, reason):
        logging.info(f"Domain approval request: {domain}")
        logging.info(f"Reason: {reason}")
        
        # Auto-approve for testing
        print(f"\nDomain approval request: {domain}")
        print(f"Reason: {reason}")
        user_input = input(f"Approve domain '{domain}'? (y/n, default: y): ")
        return {"approved": user_input.lower() != 'n'}

# Test functions
async def test_internet_controller():
    """Test the Internet Controller functionality."""
    logging.info("\n=== Testing Internet Controller ===")
    
    controller = InternetController()
    
    # Define an async callback for confirmation
    async def mock_confirmation_callback(domain, reason):
        logging.info(f"Mock confirmation request for domain: {domain}")
        return {"approved": True}
    
    controller.set_confirmation_callback(mock_confirmation_callback)
    
    await controller.initialize()
    
    try:
        # Test whitelist loading and saving
        logging.info("Testing whitelist management...")
        whitelist = controller.get_whitelist()
        logging.info(f"Initial whitelist: {whitelist.keys()}")
        
        # Test domain addition
        add_result = await controller.add_domain_to_whitelist(
            "python.org", 
            "Testing domain addition", 
            auto_approve=True
        )
        logging.info(f"Domain addition result: {add_result}")
        
        # Test URL request
        logging.info("Testing web request...")
        result = await controller.request(
            url="https://httpbin.org/get?param=test",
            method="GET",
            reason="Testing controller request"
        )
        
        if result["success"]:
            logging.info("Web request successful!")
            logging.info(f"Status: {result.get('status')}")
        else:
            logging.error(f"Web request failed: {result.get('error')}")
        
        # Test domain removal
        remove_result = controller.remove_domain_from_whitelist("python.org")
        logging.info(f"Domain removal result: {remove_result}")
        
        return True
    except Exception as e:
        logging.error(f"Internet Controller test failed: {e}")
        return False
    finally:
        await controller.close()

async def test_api_logger():
    """Test the API Logger functionality."""
    logging.info("\n=== Testing API Logger ===")
    
    try:
        logger = ApiLogger()
        
        # Test logging different API calls
        logging.info("Logging OpenAI API call...")
        openai_result = logger.log_api_call(
            service="openai",
            endpoint="chat",
            usage_data={"total_tokens": 150},
            response_data={"id": "test-id"}
        )
        logging.info(f"API cost estimate: {openai_result}")
        
        logging.info("Logging Google API call...")
        google_result = logger.log_api_call(
            service="google",
            endpoint="search",
            usage_data={"queries": 1},
            response_data={"items": []}
        )
        logging.info(f"API cost estimate: {google_result}")
        
        # Test getting monthly usage
        usage = logger.get_monthly_usage()
        logging.info(f"Monthly usage: {usage}")
        
        return True
    except Exception as e:
        logging.error(f"API Logger test failed: {e}")
        return False

async def test_api_interface():
    """Test the API Interface functionality."""
    logging.info("\n=== Testing API Interface ===")
    
    http_controller = MockHttpController()
    api_logger = ApiLogger()
    api_interface = ApiInterface(http_controller, api_logger)
    
    try:
        # Test web request
        logging.info("Testing web request...")
        web_result = await api_interface.web_request(
            url="https://httpbin.org/get?param=test",
            method="GET",
            reason="Testing API interface"
        )
        
        if web_result and web_result.get("success", False):
            logging.info("Web request successful!")
        else:
            logging.error(f"Web request failed: {web_result}")
        
        # Skip API tests if keys aren't available
        if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            logging.info("Skipping API tests (no API keys available)")
            return True
        
        # Test OpenAI API if key is available
        if os.environ.get("OPENAI_API_KEY"):
            logging.info("Testing OpenAI API...")
            openai_result = await api_interface.call_openai_api(
                endpoint="chat/completions",
                data={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello, what can you do?"}
                    ]
                },
                reason="Testing OpenAI API"
            )
            
            if openai_result and not openai_result.get("error"):
                logging.info("OpenAI API call successful!")
            else:
                logging.error(f"OpenAI API call failed: {openai_result}")
        
        # Test Google Search API if keys are available
        if os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_SEARCH_ENGINE_ID"):
            logging.info("Testing Google Search API...")
            search_result = await api_interface.search_web(
                query="Friday AI test",
                reason="Testing search functionality"
            )
            
            if search_result and search_result.get("success", False):
                logging.info("Search successful!")
            else:
                logging.error(f"Search failed: {search_result}")
        
        return True
    except Exception as e:
        logging.error(f"API Interface test failed: {e}")
        return False

async def test_network_module():
    """Test the Network Module integration."""
    logging.info("\n=== Testing Network Module ===")
    
    http_controller = MockHttpController()
    
    try:
        # Initialize the network module
        network_module = NetworkModule(http_controller)
        await network_module.initialize()
        
        # Test online/offline toggle
        logging.info("Testing online/offline toggle...")
        
        # Set to online
        network_module.set_online_status(True)
        logging.info("Set online status to: True")
        
        # Set to offline
        network_module.set_online_status(False)
        logging.info("Set online status to: False")
        
        # Test connectivity
        logging.info("Testing connectivity...")
        connectivity = await network_module.test_connectivity()
        logging.info(f"Connectivity test result: {connectivity}")
        
        # Get API interface
        api_interface = network_module.get_api_interface()
        logging.info(f"API interface available: {api_interface is not None}")
        
        # Get monthly usage
        monthly_usage = network_module.get_monthly_usage()
        logging.info(f"Monthly usage available: {monthly_usage is not None}")
        
        await network_module.shutdown()
        return True
    except Exception as e:
        logging.error(f"Network Module test failed: {e}")
        return False

async def main():
    """Run all tests."""
    logging.info("Starting Friday AI Network Integration Tests")
    
    # Make sure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Ask for API keys for testing (optional)
    use_apis = input("Do you want to test API integrations (requires API keys)? (y/n): ").lower() == 'y'
    
    if use_apis:
        openai_key = input("Enter OpenAI API key (or press Enter to skip): ")
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
            
        google_key = input("Enter Google API key (or press Enter to skip): ")
        if google_key:
            os.environ["GOOGLE_API_KEY"] = google_key
            search_engine_id = input("Enter Google Search Engine ID: ")
            os.environ["GOOGLE_SEARCH_ENGINE_ID"] = search_engine_id
    
    # Run tests
    tests = [
        ("Internet Controller", test_internet_controller),
        ("API Logger", test_api_logger),
        ("API Interface", test_api_interface),
        ("Network Module", test_network_module)
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
        print("\nAll tests passed! The network integration is working correctly.")
    else:
        print("\nSome tests failed. Please check the logs for details.")
    
    logging.info("Tests completed")

if __name__ == "__main__":
    asyncio.run(main())