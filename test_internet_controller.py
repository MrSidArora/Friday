# test_internet_controller.py

import asyncio
import logging
from internet_controller import InternetController

logging.basicConfig(level=logging.INFO)

# Mock confirmation callback
async def mock_confirmation(domain, reason):
    print(f"\nDomain approval request: {domain}")
    print(f"Reason: {reason}")
    user_input = input("Approve? (y/n): ")
    return {"approved": user_input.lower() == 'y'}

async def test_internet_controller():
    controller = InternetController()
    controller.set_confirmation_callback(mock_confirmation)
    
    await controller.initialize()
    
    try:
        # Test an approved domain (Wikipedia)
        print("\nTesting pre-approved domain (wikipedia.org)...")
        result = await controller.request(
            url="https://en.wikipedia.org/wiki/API",
            method="GET",
            reason="Testing pre-approved domain access"
        )
        
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Response status: {result['status']}")
            print(f"Content snippet: {result['data'][:100]}...")
            
        # Test a new domain (requires approval)
        print("\nTesting new domain (example.com)...")
        result = await controller.request(
            url="https://example.com",
            method="GET",
            reason="Testing new domain approval"
        )
        
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Response status: {result['status']}")
            print(f"Content snippet: {result['data'][:100]}...")
            
        # Test whitelist management
        print("\nGetting current whitelist...")
        whitelist = controller.get_whitelist()
        print(f"Domains in whitelist: {', '.join(whitelist.keys())}")
        
        print("\nAdding new domain to whitelist...")
        add_result = await controller.add_domain_to_whitelist(
            domain="python.org",
            reason="Testing whitelist management",
            auto_approve=False
        )
        print(f"Domain added successfully: {add_result['success']}")
        
        print("\nRemoving domain from whitelist...")
        remove_result = controller.remove_domain_from_whitelist("example.com")
        print(f"Domain removed successfully: {remove_result['success']}")
        
    finally:
        await controller.close()

if __name__ == "__main__":
    asyncio.run(test_internet_controller())