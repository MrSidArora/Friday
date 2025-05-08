# api_interface.py

import aiohttp
import asyncio
import json
import logging

class ApiInterface:
    def __init__(self, http_controller):
        self.http_controller = http_controller
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
        """Perform a web search (example implementation using DuckDuckGo)"""
        # This is a simplified example using DuckDuckGo's HTML
        url = f"https://html.duckduckgo.com/html/?q={query}"
        
        if not reason:
            reason = f"Friday needs to search the web for: {query}"
            
        response = await self.web_request(
            url=url,
            method="GET",
            reason=reason
        )
        
        if not response or not response.get("success", False):
            return {
                "success": False,
                "error": "Web search failed",
                "results": []
            }
            
        # In a real implementation, we would parse the HTML to extract search results
        # This is a placeholder
        return {
            "success": True,
            "query": query,
            "results": [
                # Sample results format
                {
                    "title": "Example result",
                    "url": "https://example.com",
                    "snippet": "This is an example search result snippet."
                }
            ]
        }
        
    async def call_openai_api(self, endpoint, data, reason=None):
        """Call the OpenAI API (example implementation)"""
        base_url = "https://api.openai.com/v1"
        url = f"{base_url}/{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"
        }
        
        if not reason:
            reason = f"Friday needs to call the OpenAI API for: {endpoint}"
            
        response = await self.web_request(
            url=url,
            method="POST",
            data=json.dumps(data),
            headers=headers,
            reason=reason
        )
        
        if not response or not response.get("success", False):
            return {
                "success": False,
                "error": "API call failed"
            }
            
        return response["data"]