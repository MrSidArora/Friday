# test_network_stack.py

import asyncio
import logging
import os
from network.internet_controller import InternetController
from network.api_logger import ApiLogger
from network.api_interface import ApiInterface

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_network_stack")

# Mock HTTP controller for testing
class MockHttpController:
    async def handle_request(self, method, endpoint, data):
        logger.info(f"Mock request: {method} {endpoint}")
        logger.info(f"Data: {data}")
        
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
        logger.info(f"Domain approval request: {domain}")
        logger.info(f"Reason: {reason}")
        
        # Auto-approve for testing
        user_input = input(f"Approve domain '{domain}'? (y/n, default: y): ")
        return {"approved": user_input.lower() != 'n'}

async def test_network_stack():
    # Create mock HTTP controller
    http_controller = MockHttpController()
    
    # Create API logger
    api_logger = ApiLogger()
    
    # Create API interface with the mock controller
    api_interface = ApiInterface(http_controller, api_logger)
    
    logger.info("Testing web request...")
    web_result = await api_interface.web_request(
        url="https://httpbin.org/get?param=test",
        method="GET",
        reason="Testing web request"
    )
    
    if web_result and web_result.get("success", False):
        logger.info("Web request successful!")
        logger.info(f"Response data (sample): {str(web_result.get('data', ''))[:100]}...")
    else:
        logger.error(f"Web request failed: {web_result}")
        
    logger.info("\nTesting search...")
    # Set the API key for testing
    os.environ["GOOGLE_API_KEY"] = input("Enter Google API key for testing (or press Enter to skip): ")
    os.environ["GOOGLE_SEARCH_ENGINE_ID"] = input("Enter Google Search Engine ID (or press Enter to skip): ")
    
    if os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_SEARCH_ENGINE_ID"):
        search_result = await api_interface.search_web(
            query="Friday AI personal assistant",
            reason="Testing search functionality"
        )
        
        if search_result and search_result.get("success", False):
            logger.info("Search successful!")
            logger.info(f"Found {len(search_result.get('results', []))} results")
            for i, result in enumerate(search_result.get('results', [])[:3]):
                logger.info(f"Result {i+1}: {result.get('title')} - {result.get('url')}")
        else:
            logger.error(f"Search failed: {search_result}")
    else:
        logger.info("Skipping search test (no API key provided)")
        
    logger.info("\nTesting OpenAI API...")
    # Set the API key for testing
    os.environ["OPENAI_API_KEY"] = input("Enter OpenAI API key for testing (or press Enter to skip): ")
    
    if os.environ.get("OPENAI_API_KEY"):
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
            logger.info("OpenAI API call successful!")
            try:
                message = openai_result.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info(f"Response: {message[:100]}...")
            except:
                logger.info(f"Response structure: {openai_result.keys()}")
        else:
            logger.error(f"OpenAI API call failed: {openai_result}")
    else:
        logger.info("Skipping OpenAI API test (no API key provided)")
        
    logger.info("\nChecking API usage logs...")
    usage = api_logger.get_monthly_usage()
    logger.info(f"Current monthly usage: {usage}")
    
    logger.info("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(test_network_stack())