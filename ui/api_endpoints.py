
"""
Friday AI - API Endpoints

This module provides HTTP API endpoints for connecting the UI with 
system information and web search capabilities.
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger("api_endpoints")

class ApiEndpoints:
    def __init__(self, http_controller, system_info_provider=None, web_search_manager=None, model_context_provider=None):
        """Initialize API endpoints.
        
        Args:
            http_controller: HTTP controller to register endpoints with
            system_info_provider: SystemInfoProvider instance
            web_search_manager: WebSearchManager instance
            model_context_provider: ModelContextProvider instance
        """
        self.http_controller = http_controller
        self.system_info_provider = system_info_provider
        self.web_search_manager = web_search_manager
        self.model_context_provider = model_context_provider
        
        # Register endpoints
        self._register_endpoints()
        
    def _register_endpoints(self):
        """Register API endpoints with the HTTP controller."""
        if not hasattr(self.http_controller, 'handle_request'):
            logger.error("HTTP controller does not have handle_request method")
            return
        
        # Store the original handle_request method
        self.original_handle_request = self.http_controller.handle_request
        
        # Replace with our enhanced version
        self.http_controller.handle_request = self._enhanced_handle_request
        
        logger.info("API endpoints registered with HTTP controller")
        
    async def _enhanced_handle_request(self, method, endpoint, data):
        """Enhanced request handler that adds our API endpoints.
        
        Args:
            method: HTTP method
            endpoint: Endpoint path
            data: Request data
            
        Returns:
            Response data and status code
        """
        # Handle our API endpoints
        if endpoint == "/api/system_info":
            return await self._handle_system_info(data)
            
        elif endpoint == "/api/web_search":
            return await self._handle_web_search(data)
            
        elif endpoint == "/api/browse_url":
            return await self._handle_browse_url(data)
            
        elif endpoint == "/api/get_context":
            return await self._handle_get_context(data)
            
        elif endpoint == "/api/enrich_prompt":
            return await self._handle_enrich_prompt(data)
            
        # Fall back to the original handler for other endpoints
        return await self.original_handle_request(method, endpoint, data)
        
    async def _handle_system_info(self, data: Dict[str, Any]) -> tuple:
        """Handle system info endpoint.
        
        Args:
            data: Request data
            
        Returns:
            Response data and status code
        """
        if not self.system_info_provider:
            return {"error": "System info provider not available"}, 404
            
        try:
            # Get system metrics
            metrics = await self.system_info_provider.get_system_metrics()
            
            # Get basic info
            basic_info = await self.system_info_provider.get_basic_info()
            
            # Get date/time info
            date_time = await self.system_info_provider.get_date_time_info()
            
            # Try to get top processes if requested
            processes = None
            if data and data.get("include_processes", False):
                processes = await self.system_info_provider.get_top_processes(limit=5)
                
            # Try to get weather if available
            weather = None
            if data and data.get("include_weather", False):
                weather = await self.system_info_provider.get_weather()
                
            # Combine all info
            response = {
                "success": True,
                "metrics": metrics,
                "info": basic_info,
                "date_time": date_time
            }
            
            if processes:
                response["processes"] = processes
                
            if weather and not isinstance(weather, dict) or not weather.get("error"):
                response["weather"] = weather
                
            return response, 200
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}, 500
            
    async def _handle_web_search(self, data: Dict[str, Any]) -> tuple:
        """Handle web search endpoint.
        
        Args:
            data: Request data
            
        Returns:
            Response data and status code
        """
        if not self.web_search_manager:
            return {"error": "Web search manager not available"}, 404
            
        # Check required fields
        if not data or "query" not in data:
            return {"error": "Missing required field: query"}, 400
            
        query = data["query"]
        search_engine = data.get("search_engine")
        num_results = data.get("num_results")
        safe_search = data.get("safe_search")
        browse_results = data.get("browse_results", False)
        
        try:
            # Perform search
            if browse_results:
                results = await self.web_search_manager.search_and_browse(
                    query=query,
                    search_engine=search_engine,
                    num_results=num_results,
                    safe_search=safe_search
                )
            else:
                results = await self.web_search_manager.search(
                    query=query,
                    search_engine=search_engine,
                    num_results=num_results,
                    safe_search=safe_search
                )
                
            return results, 200
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return {"error": str(e)}, 500
            
    async def _handle_browse_url(self, data: Dict[str, Any]) -> tuple:
        """Handle browse URL endpoint.
        
        Args:
            data: Request data
            
        Returns:
            Response data and status code
        """
        if not self.web_search_manager:
            return {"error": "Web search manager not available"}, 404
            
        # Check required fields
        if not data or "url" not in data:
            return {"error": "Missing required field: url"}, 400
            
        url = data["url"]
        reason = data.get("reason")
        
        try:
            # Browse URL
            result = await self.web_search_manager.browse_url(url, reason)
            return result, 200
        except Exception as e:
            logger.error(f"Error browsing URL: {e}")
            return {"error": str(e)}, 500
            
    async def _handle_get_context(self, data: Dict[str, Any]) -> tuple:
        """Handle get context endpoint.
        
        Args:
            data: Request data
            
        Returns:
            Response data and status code
        """
        if not self.model_context_provider:
            return {"error": "Model context provider not available"}, 404
            
        try:
            # Get current context
            context = await self.model_context_provider.get_current_context()
            
            # Format if requested
            if data and data.get("formatted", False):
                formatted_context = self.model_context_provider.format_context_for_model(context)
                return {"success": True, "context": context, "formatted": formatted_context}, 200
            else:
                return {"success": True, "context": context}, 200
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return {"error": str(e)}, 500
            
    async def _handle_enrich_prompt(self, data: Dict[str, Any]) -> tuple:
        """Handle enrich prompt endpoint.
        
        Args:
            data: Request data
            
        Returns:
            Response data and status code
        """
        if not self.model_context_provider:
            return {"error": "Model context provider not available"}, 404
            
        # Check required fields
        if not data or "prompt" not in data:
            return {"error": "Missing required field: prompt"}, 400
            
        prompt = data["prompt"]
        include_web_search = data.get("include_web_search", False)
        web_search_query = data.get("web_search_query")
        
        try:
            # Start with context enrichment
            enriched_prompt = await self.model_context_provider.enrich_prompt_with_context(prompt)
            
            # Add web search if requested
            if include_web_search and self.model_context_provider.web_search_manager:
                search_result = await self.model_context_provider.search_and_enrich(
                    prompt=enriched_prompt,
                    query=web_search_query
                )
                
                if search_result.get("success", False):
                    enriched_prompt = search_result["enriched_prompt"]
                    
                return {
                    "success": True,
                    "original_prompt": prompt,
                    "enriched_prompt": enriched_prompt,
                    "web_search_included": search_result.get("success", False),
                    "web_search_results": search_result.get("search_results")
                }, 200
            else:
                return {
                    "success": True,
                    "original_prompt": prompt,
                    "enriched_prompt": enriched_prompt,
                    "web_search_included": False
                }, 200
        except Exception as e:
            logger.error(f"Error enriching prompt: {e}")
            return {"error": str(e)}, 500