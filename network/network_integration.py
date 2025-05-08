# friday/network/network_integration.py

import os
import logging
import asyncio
from network.internet_controller import InternetController
from network.api_logger import ApiLogger
from network.api_interface import ApiInterface

class NetworkModule:
    def __init__(self, http_controller):
        self.http_controller = http_controller
        self.is_online = False
        
        # Set up logging
        self.logger = logging.getLogger("network_module")
        
        # Initialize components
        self.internet_controller = InternetController()
        self.api_logger = ApiLogger()
        self.api_interface = ApiInterface(http_controller, self.api_logger)
        
        # Connect the internet controller to the UI
        self.internet_controller.set_confirmation_callback(self.http_controller.request_domain_approval)
        
        # Let the HTTP controller know about this network module
        if hasattr(self.http_controller, 'set_network_module'):
            self.http_controller.set_network_module(self)
        
    async def initialize(self):
        """Initialize the network module"""
        await self.internet_controller.initialize()
        self.logger.info("Network module initialized")
        
    async def shutdown(self):
        """Shutdown the network module"""
        await self.internet_controller.close()
        self.logger.info("Network module shut down")
        
    def get_api_interface(self):
        """Get the API interface for use by other components"""
        return self.api_interface
        
    def get_monthly_usage(self):
        """Get the current monthly API usage"""
        return self.api_logger.get_monthly_usage()

    def set_online_status(self, online):
        """Enable or disable internet access"""
        self.is_online = online
        self.logger.info(f"Online status set to: {online}")
    
        # If online is False, internet controller should require confirmation for all requests
        # If online is True, internet controller should use normal confirmation rules
        self.internet_controller.set_require_confirmation_for_all(not online)
    
        return {"success": True}
        
    async def test_connectivity(self):
        """Test internet connectivity"""
        test_url = "https://www.wikipedia.org"
        result = await self.internet_controller.request(
            url=test_url,
            method="GET",
            reason="Testing internet connectivity",
            require_confirmation=False  # Don't require confirmation for this test
        )
        
        return {
            "online": result["success"],
            "details": result
        }