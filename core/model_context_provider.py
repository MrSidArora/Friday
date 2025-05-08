"""
Friday AI - Model Context Provider

This module provides real-time context information to the LLM model,
including system information, date/time, weather, and other contextual data.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List

logger = logging.getLogger("model_context_provider")

class ModelContextProvider:
    def __init__(self, system_info_provider=None, web_search_manager=None, config_path=None):
        """Initialize the model context provider.
        
        Args:
            system_info_provider: SystemInfoProvider instance
            web_search_manager: WebSearchManager instance
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.system_info_provider = system_info_provider
        self.web_search_manager = web_search_manager
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "enabled": True,
            "auto_add_context": True,
            "context_types": {
                "date_time": True,
                "system_metrics": True,
                "weather": False,  # Disabled by default as it requires API key
                "system_info": True
            },
            "context_update_interval": 60,  # seconds
            "max_context_tokens": 500
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    
                # Merge configs
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
                logger.error(f"Error loading model context config: {e}")
                
        return default_config
        
    async def get_current_context(self) -> Dict[str, Any]:
        """Get the current context information.
        
        Returns:
            Dictionary with context information
        """
        if not self.config["enabled"]:
            return {"enabled": False}
            
        context = {"enabled": True}
        context_types = self.config["context_types"]
        
        # Get date/time information
        if context_types.get("date_time", True) and self.system_info_provider:
            try:
                context["date_time"] = await self.system_info_provider.get_date_time_info()
            except Exception as e:
                logger.error(f"Error getting date/time info: {e}")
                
        # Get system metrics
        if context_types.get("system_metrics", True) and self.system_info_provider:
            try:
                context["system_metrics"] = await self.system_info_provider.get_system_metrics()
            except Exception as e:
                logger.error(f"Error getting system metrics: {e}")
                
        # Get weather information
        if context_types.get("weather", False) and self.system_info_provider:
            try:
                context["weather"] = await self.system_info_provider.get_weather()
            except Exception as e:
                logger.error(f"Error getting weather info: {e}")
                
        # Get system information
        if context_types.get("system_info", True) and self.system_info_provider:
            try:
                context["system_info"] = await self.system_info_provider.get_basic_info()
            except Exception as e:
                logger.error(f"Error getting system info: {e}")
                
        return context
        
    def format_context_for_model(self, context: Dict[str, Any]) -> str:
        """Format context information for the model.
        
        Args:
            context: Context information
            
        Returns:
            Formatted context string
        """
        if not context.get("enabled", False):
            return ""
            
        # Format the context as a markdown-style string
        context_parts = []
        
        # Date and time
        if "date_time" in context:
            date_time = context["date_time"]
            context_parts.append(f"## Current Date and Time\n"
                               f"- Current date: {date_time.get('date', 'Unknown')}\n"
                               f"- Current time: {date_time.get('time', 'Unknown')}\n"
                               f"- Day: {date_time.get('day_of_week', 'Unknown')}\n")
                               
        # System metrics
        if "system_metrics" in context:
            metrics = context["system_metrics"]
            cpu = metrics.get("cpu", {})
            memory = metrics.get("memory", {})
            disk = metrics.get("disk", {})
            
            context_parts.append(f"## System Resource Usage\n"
                              f"- CPU usage: {cpu.get('usage_percent', 0)}%\n"
                              f"- Memory usage: {memory.get('usage_percent', 0)}% ({memory.get('used', 'Unknown')} / {memory.get('total', 'Unknown')})\n"
                              f"- Disk usage: {disk.get('usage_percent', 0)}% ({disk.get('used', 'Unknown')} / {disk.get('total', 'Unknown')})\n")
                              
        # Weather information
        if "weather" in context and not isinstance(context["weather"], dict) or not context["weather"].get("error"):
            weather = context["weather"]
            context_parts.append(f"## Current Weather\n"
                              f"- Location: {weather.get('location', 'Unknown')}\n"
                              f"- Temperature: {weather.get('temperature', {}).get('current', 'Unknown')}°C\n"
                              f"- Condition: {weather.get('condition', {}).get('description', 'Unknown')}\n"
                              f"- Humidity: {weather.get('humidity', 'Unknown')}%\n")
                              
        # System information
        if "system_info" in context:
            info = context["system_info"]
            context_parts.append(f"## System Information\n"
                              f"- Platform: {info.get('platform', 'Unknown')} {info.get('version', '')}\n"
                              f"- Processor: {info.get('processor', 'Unknown')}\n"
                              f"- Hostname: {info.get('hostname', 'Unknown')}\n"
                              f"- Uptime: {info.get('uptime', 'Unknown')}\n")
                              
        # Join all context parts with newlines
        return "\n".join(context_parts)
        
    async def enrich_prompt_with_context(self, prompt: str) -> str:
        """Enrich a prompt with context information.
        
        Args:
            prompt: Original prompt
            
        Returns:
            Prompt enriched with context
        """
        if not self.config["enabled"] or not self.config["auto_add_context"]:
            return prompt
            
        try:
            # Get current context
            context = await self.get_current_context()
            
            # Format context for model
            context_str = self.format_context_for_model(context)
            
            if not context_str:
                return prompt
                
            # Add context to prompt
            return f"{context_str}\n\n{prompt}"
        except Exception as e:
            logger.error(f"Error enriching prompt with context: {e}")
            return prompt
        
    async def search_and_enrich(self, prompt: str, query: Optional[str] = None) -> Dict[str, Any]:
        """Search the web and enrich a prompt with the results.
        
        Args:
            prompt: Original prompt
            query: Search query (if None, will be derived from prompt)
            
        Returns:
            Dictionary with enriched prompt and search results
        """
        if not self.web_search_manager:
            return {"success": False, "error": "Web search manager not available"}
            
        # If no query is provided, try to derive one from the prompt
        if not query:
            query = prompt  # In a real implementation, you would use an LLM to derive a good search query
            
        # Perform the search
        search_results = await self.web_search_manager.search(query)
        
        if not search_results.get("success", False):
            return {"success": False, "error": search_results.get("error", "Unknown error"), "prompt": prompt}
            
        # Format search results for the model
        results_str = self._format_search_results(search_results)
        
        # Enrich the prompt with search results
        enriched_prompt = f"{prompt}\n\n{results_str}"
        
        return {
            "success": True,
            "original_prompt": prompt,
            "enriched_prompt": enriched_prompt,
            "search_results": search_results
        }
        
    def _format_search_results(self, search_results: Dict[str, Any]) -> str:
        """Format search results for the model.
        
        Args:
            search_results: Search results
            
        Returns:
            Formatted search results string
        """
        results = search_results.get("results", [])
        if not results:
            return "No search results found."
            
        # Format as a markdown list
        formatted = f"## Search Results for '{search_results.get('query', 'Unknown query')}'\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get("snippet", "No snippet available")
            
            formatted += f"{i}. **{title}**\n"
            formatted += f"   URL: {url}\n"
            formatted += f"   {snippet}\n\n"
            
        return formatted
        
    async def answer_with_web_search(self, prompt: str) -> Dict[str, Any]:
        """Answer a question by searching the web and using the results.
        
        Args:
            prompt: Question to answer
            
        Returns:
            Dictionary with answer and search results
        """
        if not self.web_search_manager:
            return {"success": False, "error": "Web search manager not available"}
            
        # Search and browse
        search_results = await self.web_search_manager.search_and_browse(prompt)
        
        if not search_results.get("success", False):
            return {"success": False, "error": search_results.get("error", "Unknown error")}
            
        # Format the results for the model
        formatted_results = self._format_search_and_browse_results(search_results)
        
        # In a real implementation, you would send the formatted results to an LLM
        # along with the original prompt to generate an answer
        
        return {
            "success": True,
            "question": prompt,
            "search_results": search_results,
            "formatted_results": formatted_results
        }
        
    def _format_search_and_browse_results(self, search_results: Dict[str, Any]) -> str:
        """Format search and browse results for the model.
        
        Args:
            search_results: Search and browse results
            
        Returns:
            Formatted results string
        """
        results = search_results.get("results", [])
        if not results:
            return "No search results found."
            
        # Format as a markdown document
        formatted = f"## Research Results for '{search_results.get('query', 'Unknown query')}'\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get("snippet", "No snippet available")
            page_title = result.get("page_title", title)
            page_content = result.get("page_content", "No content available")
            page_error = result.get("page_error", "")
            
            formatted += f"### {i}. {title}\n"
            formatted += f"URL: {url}\n\n"
            formatted += f"**Snippet**: {snippet}\n\n"
            
            if page_error:
                formatted += f"**Error**: {page_error}\n\n"
            else:
                formatted += f"**Page Title**: {page_title}\n\n"
                formatted += f"**Content Summary**:\n{page_content}\n\n"
                
            formatted += "---\n\n"
            
        return formatted