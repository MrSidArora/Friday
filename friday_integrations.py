"""
Friday AI - Integrations Setup

This module sets up the integrations for Friday AI, including
system information, web search, and model context enrichment.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional

# Import core components
from core.model_manager import ModelManager
from core.memory_system import MemorySystem
from core.request_router import RequestRouter
from core.security_monitor import SecurityMonitor
from core.llm_interface import LLMInterface

# Import network components
from network.internet_controller import InternetController
from network.network_integration import NetworkModule

# Import UI components
from ui.http_controller import HttpController

# Import new integration components
from utils.system_info import SystemInfoProvider
from network.web_search_manager import WebSearchManager
from core.model_context_provider import ModelContextProvider
from ui.api_endpoints import ApiEndpoints

logger = logging.getLogger("friday_integrations")

class FridayIntegrations:
    def __init__(self, friday_system):
        """Initialize Friday integrations.
        
        Args:
            friday_system: FridaySystem instance
        """
        self.friday_system = friday_system
        self.system_info_provider = None
        self.web_search_manager = None
        self.model_context_provider = None
        self.api_endpoints = None
        
    async def initialize(self):
        """Initialize all integrations."""
        logger.info("Initializing Friday integrations...")
        
        # Initialize system info provider
        self.system_info_provider = await self._init_system_info_provider()
        
        # Initialize web search manager
        self.web_search_manager = await self._init_web_search_manager()
        
        # Initialize model context provider
        self.model_context_provider = await self._init_model_context_provider()
        
        # Initialize API endpoints
        self.api_endpoints = await self._init_api_endpoints()
        
        # Connect the model context provider to the LLM interface
        await self._connect_model_context_provider()
        
        logger.info("Friday integrations initialized successfully")
        
    async def _init_system_info_provider(self):
        """Initialize the system information provider.
        
        Returns:
            SystemInfoProvider instance
        """
        try:
            # Create config path if it doesn't exist
            config_path = "configs/system_info_config.json"
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Create default config if it doesn't exist
            if not os.path.exists(config_path):
                default_config = {
                    "weather_api_key": None,
                    "weather_location": None,
                    "update_interval": 5,
                    "monitor_processes": True,
                    "monitor_startup_items": True,
                    "monitor_sensors": True,
                    "monitor_network": True
                }
                
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                
            # Initialize provider
            provider = SystemInfoProvider(config_path)
            logger.info("System info provider initialized")
            return provider
        except Exception as e:
            logger.error(f"Error initializing system info provider: {e}")
            return None
            
    async def _init_web_search_manager(self):
        """Initialize the web search manager.
        
        Returns:
            WebSearchManager instance
        """
        try:
            # Get the internet controller
            if not hasattr(self.friday_system, 'internet_controller'):
                logger.error("Friday system does not have internet controller")
                return None
                
            internet_controller = self.friday_system.internet_controller
            
            # Create config path if it doesn't exist
            config_path = "configs/web_search_config.json"
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Create default config if it doesn't exist
            if not os.path.exists(config_path):
                default_config = {
                    "search_engines": {
                        "default": "duckduckgo",
                        "duckduckgo": {
                            "enabled": True,
                            "base_url": "https://html.duckduckgo.com/html/?q=",
                            "requires_api_key": False
                        },
                        "google": {
                            "enabled": False,
                            "base_url": "https://www.googleapis.com/customsearch/v1",
                            "requires_api_key": True,
                            "api_key": None,
                            "cx": None
                        },
                        "bing": {
                            "enabled": False,
                            "base_url": "https://api.bing.microsoft.com/v7.0/search",
                            "requires_api_key": True,
                            "api_key": None
                        }
                    },
                    "max_results": 5,
                    "safe_search": True,
                    "log_searches": True,
                    "cache_enabled": True,
                    "cache_ttl": 3600,
                    "max_snippets_per_query": 3,
                    "max_snippet_length": 200
                }
                
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                
            # Initialize manager
            manager = WebSearchManager(internet_controller, config_path)
            logger.info("Web search manager initialized")
            return manager
        except Exception as e:
            logger.error(f"Error initializing web search manager: {e}")
            return None
            
    async def _init_model_context_provider(self):
        """Initialize the model context provider.
        
        Returns:
            ModelContextProvider instance
        """
        try:
            # Create config path if it doesn't exist
            config_path = "configs/model_context_config.json"
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Create default config if it doesn't exist
            if not os.path.exists(config_path):
                default_config = {
                    "enabled": True,
                    "auto_add_context": True,
                    "context_types": {
                        "date_time": True,
                        "system_metrics": True,
                        "weather": False,
                        "system_info": True
                    },
                    "context_update_interval": 60,
                    "max_context_tokens": 500
                }
                
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                
            # Initialize provider
            provider = ModelContextProvider(
                system_info_provider=self.system_info_provider,
                web_search_manager=self.web_search_manager,
                config_path=config_path
            )
            logger.info("Model context provider initialized")
            return provider
        except Exception as e:
            logger.error(f"Error initializing model context provider: {e}")
            return None
            
    async def _init_api_endpoints(self):
        """Initialize the API endpoints.
        
        Returns:
            ApiEndpoints instance
        """
        try:
            # Get the HTTP controller
            if not hasattr(self.friday_system, 'http_controller'):
                logger.error("Friday system does not have HTTP controller")
                return None
                
            http_controller = self.friday_system.http_controller
            
            # Initialize endpoints
            endpoints = ApiEndpoints(
                http_controller=http_controller,
                system_info_provider=self.system_info_provider,
                web_search_manager=self.web_search_manager,
                model_context_provider=self.model_context_provider
            )
            logger.info("API endpoints initialized")
            return endpoints
        except Exception as e:
            logger.error(f"Error initializing API endpoints: {e}")
            return None
            
    async def _connect_model_context_provider(self):
        """Connect the model context provider to the LLM interface."""
        try:
            # Get the LLM interface
            if not hasattr(self.friday_system, 'llm_interface') or not self.friday_system.llm_interface:
                logger.error("Friday system does not have LLM interface")
                return
                
            llm_interface = self.friday_system.llm_interface
            
            # Check if model context provider is available
            if not self.model_context_provider:
                logger.error("Model context provider not available")
                return
                
            # Monkey patch the LLM interface's ask method to add context
            original_ask = llm_interface.ask
            
            async def enhanced_ask(prompt, context=None, intent=None):
                # Enrich the prompt with context
                enriched_prompt = await self.model_context_provider.enrich_prompt_with_context(prompt)
                
                # Call the original ask method with the enriched prompt
                return await original_ask(enriched_prompt, context, intent)
                
            # Replace the ask method
            llm_interface.ask = enhanced_ask
            
            logger.info("Model context provider connected to LLM interface")
        except Exception as e:
            logger.error(f"Error connecting model context provider: {e}")
            
    async def shutdown(self):
        """Shut down all integrations."""
        logger.info("Shutting down Friday integrations...")
        
        # Nothing to do yet
        
        logger.info("Friday integrations shut down")