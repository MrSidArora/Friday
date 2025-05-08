# Update api_interface.py

import aiohttp
import asyncio
import json
import logging
import os
from datetime import datetime

class ApiInterface:
    def __init__(self, http_controller, api_logger):
        self.http_controller = http_controller
        self.api_logger = api_logger
        self.logger = logging.getLogger("api_interface")
        
    async def web_request(self, url, method="GET", data=None, headers=None, reason=None):
        """Make a web request using the internet controller"""
        try:
            result = await self.http_controller.handle_request(
                "POST",
                "/web_request",
                {
                    "url": url,
                    "method": method,
                    "data": data,
                    "headers": headers,
                    "reason": reason
                }
            )
            
            response, status_code = result
            
            if status_code >= 400:
                self.logger.error(f"Web request failed: {response.get('error', 'Unknown error')}")
                return None
                
            return response
        except Exception as e:
            self.logger.error(f"Error making web request: {str(e)}")
            return None
            
    async def search_web(self, query, reason=None):
        """Perform a web search using Google"""
        # In a real implementation, you'd use a proper search API
        # This is a simplified example
        
        # Placeholder implementation
        search_url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            "key": os.environ.get("GOOGLE_API_KEY", ""),
            "cx": os.environ.get("GOOGLE_SEARCH_ENGINE_ID", ""),
            "q": query
        }
        
        url = f"{search_url}?key={params['key']}&cx={params['cx']}&q={query}"
        
        if not reason:
            reason = f"Friday needs to search the web for: {query}"
            
        response = await self.web_request(
            url=url,
            method="GET",
            reason=reason
        )
        
        # Log the API call
        self.api_logger.log_api_call(
            service="google",
            endpoint="search",
            usage_data={"queries": 1},
            error=None if response and response.get("success", False) else "Search failed"
        )
        
        if not response or not response.get("success", False):
            return {
                "success": False,
                "error": "Web search failed",
                "results": []
            }
            
        # Parse the search response
        try:
            search_data = response["data"]
            results = []
            
            if "items" in search_data:
                for item in search_data["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    })
                    
            return {
                "success": True,
                "query": query,
                "results": results
            }
        except Exception as e:
            self.logger.error(f"Error parsing search results: {str(e)}")
            return {
                "success": False,
                "error": f"Error parsing search results: {str(e)}",
                "results": []
            }
            
    async def call_openai_api(self, endpoint, data, reason=None):
        """Call the OpenAI API"""
        base_url = "https://api.openai.com/v1"
        url = f"{base_url}/{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"
        }
        
        if not reason:
            reason = f"Friday needs to call the OpenAI API for: {endpoint}"
            
        start_time = datetime.now()
        
        response = await self.web_request(
            url=url,
            method="POST",
            data=json.dumps(data),
            headers=headers,
            reason=reason
        )
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        if not response or not response.get("success", False):
            # Log the failed API call
            self.api_logger.log_api_call(
                service="openai",
                endpoint=endpoint,
                usage_data={"duration": duration},
                error="API call failed"
            )
            
            return {
                "success": False,
                "error": "API call failed"
            }
            
        # Log the successful API call
        response_data = response["data"]
        usage_data = {}
        
        if endpoint == "chat/completions":
            usage_data = {
                "total_tokens": response_data.get("usage", {}).get("total_tokens", 0),
                "duration": duration
            }
        elif endpoint == "audio/transcriptions":
            # For Whisper, we don't get token usage, so estimate based on duration
            usage_data = {
                "minutes": duration / 60,  # Convert seconds to minutes
                "duration": duration
            }
            
        self.api_logger.log_api_call(
            service="openai",
            endpoint=endpoint.split("/")[0],  # "chat" or "audio"
            usage_data=usage_data,
            response_data=response_data
        )
            
        return response_data