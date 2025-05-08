"""
Friday AI - Web Search Manager

This module provides web search capabilities to Friday AI, building on top of
the existing internet_controller.py for safe web access.
"""

import os
import re
import json
import logging
import asyncio
import aiohttp
import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urlencode, quote_plus

from network.internet_controller import InternetController

logger = logging.getLogger("web_search_manager")

class WebSearchManager:
    def __init__(self, internet_controller: InternetController, config_path: Optional[str] = None):
        """Initialize the web search manager.
        
        Args:
            internet_controller: InternetController instance for safe web access
            config_path: Path to configuration file
        """
        self.internet_controller = internet_controller
        self.config = self._load_config(config_path)
        self.search_history = []
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
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
                    "cx": None  # Search engine ID
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
            "cache_ttl": 3600,  # 1 hour
            "max_snippets_per_query": 3,
            "max_snippet_length": 200
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    
                # Merge configs (not a deep merge, but good enough for our purposes)
                for key, value in loaded_config.items():
                    if key in default_config:
                        if isinstance(default_config[key], dict) and isinstance(value, dict):
                            # Merge dictionaries
                            for subkey, subvalue in value.items():
                                default_config[key][subkey] = subvalue
                        else:
                            default_config[key] = value
                    else:
                        default_config[key] = value
            except Exception as e:
                logger.error(f"Error loading web search config: {e}")
                
        return default_config
        
    async def search(self, query: str, search_engine: Optional[str] = None, 
                    num_results: Optional[int] = None, safe_search: Optional[bool] = None) -> Dict[str, Any]:
        """Perform a web search.
        
        Args:
            query: Search query
            search_engine: Search engine to use (default, duckduckgo, google, bing)
            num_results: Number of results to return
            safe_search: Whether to use safe search
            
        Returns:
            Dictionary with search results
        """
        # Use default values if not specified
        if search_engine is None:
            search_engine = self.config["search_engines"]["default"]
            
        if num_results is None:
            num_results = self.config["max_results"]
            
        if safe_search is None:
            safe_search = self.config["safe_search"]
            
        # Check if search engine is enabled
        engine_config = self.config["search_engines"].get(search_engine)
        if not engine_config:
            return {"success": False, "error": f"Unknown search engine: {search_engine}"}
            
        if not engine_config.get("enabled", False):
            return {"success": False, "error": f"Search engine {search_engine} is disabled"}
            
        # Check if API key is required and available
        if engine_config.get("requires_api_key", False) and not engine_config.get("api_key"):
            return {"success": False, "error": f"Search engine {search_engine} requires an API key"}
            
        # Log the search if enabled
        if self.config["log_searches"]:
            self._log_search(query, search_engine)
            
        # Dispatch to appropriate search method
        if search_engine == "duckduckgo":
            return await self._search_duckduckgo(query, num_results, safe_search)
        elif search_engine == "google":
            return await self._search_google(query, num_results, safe_search)
        elif search_engine == "bing":
            return await self._search_bing(query, num_results, safe_search)
        else:
            return {"success": False, "error": f"Unsupported search engine: {search_engine}"}
            
    async def _search_duckduckgo(self, query: str, num_results: int, safe_search: bool) -> Dict[str, Any]:
        """Search using DuckDuckGo.
        
        Args:
            query: Search query
            num_results: Number of results to return
            safe_search: Whether to use safe search
            
        Returns:
            Dictionary with search results
        """
        # Build search URL
        engine_config = self.config["search_engines"]["duckduckgo"]
        search_url = f"{engine_config['base_url']}{quote_plus(query)}"
        
        if safe_search:
            search_url += "&kp=1"  # Safe search parameter for DuckDuckGo
            
        # Make the request through the internet controller
        response = await self.internet_controller.request(
            url=search_url,
            method="GET",
            reason=f"Web search for: {query}",
            require_confirmation=False  # Assuming search engines are pre-approved
        )
        
        if not response.get("success", False):
            return {"success": False, "error": response.get("error", "Unknown error")}
            
        # Parse the results
        try:
            # We need BeautifulSoup to parse the HTML
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                return {"success": False, "error": "BeautifulSoup not installed. Run 'pip install beautifulsoup4' to enable web search."}
                
            soup = BeautifulSoup(response.get("data", ""), "html.parser")
            results = []
            
            # Find search results
            for result_element in soup.select(".result"):
                # Extract title
                title_element = result_element.select_one(".result__title")
                if not title_element:
                    continue
                    
                title = title_element.get_text(strip=True)
                
                # Extract URL
                url_element = title_element.select_one("a")
                if not url_element:
                    continue
                    
                url = url_element.get("href", "")
                
                # Extract actual URL from DuckDuckGo redirect
                if url.startswith("/"):
                    # Parse the redirect URL to get the actual URL
                    try:
                        from urllib.parse import parse_qs, urlparse
                        parsed = urlparse(url)
                        query_params = parse_qs(parsed.query)
                        if "uddg" in query_params:
                            url = query_params["uddg"][0]
                    except Exception as e:
                        logger.error(f"Error parsing DuckDuckGo redirect URL: {e}")
                        
                # Extract snippet
                snippet_element = result_element.select_one(".result__snippet")
                snippet = snippet_element.get_text(strip=True) if snippet_element else ""
                
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
                
                if len(results) >= num_results:
                    break
                    
            # Return results
            return {
                "success": True,
                "query": query,
                "search_engine": "duckduckgo",
                "safe_search": safe_search,
                "results": results
            }
        except Exception as e:
            logger.error(f"Error parsing DuckDuckGo results: {e}")
            return {"success": False, "error": f"Error parsing search results: {str(e)}"}
            
    async def _search_google(self, query: str, num_results: int, safe_search: bool) -> Dict[str, Any]:
        """Search using Google Custom Search API.
        
        Args:
            query: Search query
            num_results: Number of results to return
            safe_search: Whether to use safe search
            
        Returns:
            Dictionary with search results
        """
        # Get Google search configuration
        engine_config = self.config["search_engines"]["google"]
        api_key = engine_config.get("api_key")
        cx = engine_config.get("cx")  # Search engine ID
        
        if not api_key or not cx:
            return {"success": False, "error": "Google search requires API key and search engine ID"}
            
        # Build search URL
        search_params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": min(num_results, 10)  # Google API max is 10
        }
        
        if safe_search:
            search_params["safe"] = "active"
            
        search_url = f"{engine_config['base_url']}?{urlencode(search_params)}"
        
        # Make the request through the internet controller
        response = await self.internet_controller.request(
            url=search_url,
            method="GET",
            reason=f"Google search for: {query}",
            require_confirmation=False
        )
        
        if not response.get("success", False):
            return {"success": False, "error": response.get("error", "Unknown error")}
            
        # Parse the results
        try:
            data = json.loads(response.get("data", "{}"))
            
            if "items" not in data:
                return {"success": False, "error": "No results found"}
                
            results = []
            for item in data["items"]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
                
                if len(results) >= num_results:
                    break
                    
            # Return results
            return {
                "success": True,
                "query": query,
                "search_engine": "google",
                "safe_search": safe_search,
                "results": results
            }
        except Exception as e:
            logger.error(f"Error parsing Google search results: {e}")
            return {"success": False, "error": f"Error parsing search results: {str(e)}"}
            
    async def _search_bing(self, query: str, num_results: int, safe_search: bool) -> Dict[str, Any]:
        """Search using Bing API.
        
        Args:
            query: Search query
            num_results: Number of results to return
            safe_search: Whether to use safe search
            
        Returns:
            Dictionary with search results
        """
        # Get Bing search configuration
        engine_config = self.config["search_engines"]["bing"]
        api_key = engine_config.get("api_key")
        
        if not api_key:
            return {"success": False, "error": "Bing search requires API key"}
            
        # Build search URL
        search_params = {
            "q": query,
            "count": num_results
        }
        
        if safe_search:
            search_params["safeSearch"] = "Strict"
            
        search_url = f"{engine_config['base_url']}?{urlencode(search_params)}"
        
        # Make the request through the internet controller
        headers = {
            "Ocp-Apim-Subscription-Key": api_key
        }
        
        response = await self.internet_controller.request(
            url=search_url,
            method="GET",
            headers=headers,
            reason=f"Bing search for: {query}",
            require_confirmation=False
        )
        
        if not response.get("success", False):
            return {"success": False, "error": response.get("error", "Unknown error")}
            
        # Parse the results
        try:
            data = json.loads(response.get("data", "{}"))
            
            if "webPages" not in data or "value" not in data["webPages"]:
                return {"success": False, "error": "No results found"}
                
            results = []
            for item in data["webPages"]["value"]:
                results.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", "")
                })
                
                if len(results) >= num_results:
                    break
                    
            # Return results
            return {
                "success": True,
                "query": query,
                "search_engine": "bing",
                "safe_search": safe_search,
                "results": results
            }
        except Exception as e:
            logger.error(f"Error parsing Bing search results: {e}")
            return {"success": False, "error": f"Error parsing search results: {str(e)}"}
            
    async def browse_url(self, url: str, reason: str = None) -> Dict[str, Any]:
        """Retrieve and parse a web page.
        
        Args:
            url: URL to browse
            reason: Reason for browsing
            
        Returns:
            Dictionary with page content
        """
        # Make the request through the internet controller
        response = await self.internet_controller.request(
            url=url,
            method="GET",
            reason=reason or f"Browsing web page: {url}"
        )
        
        if not response.get("success", False):
            return {"success": False, "error": response.get("error", "Unknown error")}
            
        # Parse the page
        try:
            # We need BeautifulSoup to parse the HTML
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                return {"success": False, "error": "BeautifulSoup not installed. Run 'pip install beautifulsoup4' to enable web browsing."}
                
            # Parse the HTML
            soup = BeautifulSoup(response.get("data", ""), "html.parser")
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Extract main content (this is a simplistic approach)
            # In a real implementation, you would use more sophisticated content extraction
            content = ""
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Try to find the main content
            main_content = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"}) or soup.find("div", {"class": "content"})
            if main_content:
                content = main_content.get_text(separator="\n", strip=True)
            else:
                # Fall back to body text
                content = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
                
            # Clean up the content
            content = re.sub(r'\n+', '\n', content)  # Remove multiple newlines
            content = re.sub(r'\s+', ' ', content)   # Remove multiple spaces
            
            # Extract metadata
            meta_tags = {}
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property")
                if name:
                    content = meta.get("content")
                    if content:
                        meta_tags[name] = content
                        
            # Return the parsed page
            return {
                "success": True,
                "url": url,
                "title": title,
                "content": content,
                "meta": meta_tags
            }
        except Exception as e:
            logger.error(f"Error parsing web page: {e}")
            return {"success": False, "error": f"Error parsing web page: {str(e)}"}
            
    async def search_and_browse(self, query: str, search_engine: Optional[str] = None, 
                               num_results: Optional[int] = None, safe_search: Optional[bool] = None) -> Dict[str, Any]:
        """Perform a web search and browse the top results.
        
        Args:
            query: Search query
            search_engine: Search engine to use
            num_results: Number of results to browse
            safe_search: Whether to use safe search
            
        Returns:
            Dictionary with search results and page content
        """
        # Perform the search
        search_results = await self.search(query, search_engine, num_results, safe_search)
        
        if not search_results.get("success", False):
            return search_results
            
        # Browse each result
        results = search_results.get("results", [])
        browsed_results = []
        
        for result in results:
            url = result.get("url")
            if not url:
                continue
                
            # Browse the page
            page_content = await self.browse_url(url, f"Browsing search result for: {query}")
            
            # Add page content to the result
            browsed_result = result.copy()
            if page_content.get("success", False):
                browsed_result["page_title"] = page_content.get("title", "")
                browsed_result["page_content"] = self._summarize_content(page_content.get("content", ""))
                browsed_result["page_meta"] = page_content.get("meta", {})
            else:
                browsed_result["page_error"] = page_content.get("error", "Unknown error")
                
            browsed_results.append(browsed_result)
            
        # Return the browsed results
        return {
            "success": True,
            "query": query,
            "search_engine": search_results.get("search_engine", "unknown"),
            "safe_search": search_results.get("safe_search", False),
            "results": browsed_results
        }
        
    def _summarize_content(self, content: str, max_length: int = 500) -> str:
        """Summarize page content to a reasonable length.
        
        Args:
            content: Page content
            max_length: Maximum length of summary
            
        Returns:
            Summarized content
        """
        if len(content) <= max_length:
            return content
            
        # Simple truncation with ellipsis
        return content[:max_length] + "..."
        
    def _log_search(self, query: str, search_engine: str):
        """Log a search query.
        
        Args:
            query: Search query
            search_engine: Search engine used
        """
        # Add to search history
        self.search_history.append({
            "query": query,
            "search_engine": search_engine,
            "timestamp": str(datetime.datetime.now())
        })
        
        # Keep history to reasonable size
        if len(self.search_history) > 100:
            self.search_history = self.search_history[-100:]
            
        logger.info(f"Web search: {query} (using {search_engine})")
        
    def get_search_history(self) -> List[Dict[str, Any]]:
        """Get the search history.
        
        Returns:
            List of search history items
        """
        return self.search_history
        
    def clear_search_history(self):
        """Clear the search history."""
        self.search_history = []
        logger.info("Search history cleared")
        
