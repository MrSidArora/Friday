"""
Friday AI - Model Manager
Handles loading, unloading, and management of LLM models via Ollama API.
"""

import os
import json
import time
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List

class ModelManager:
    def __init__(self, config_path: str = None):
        """Initialize the model manager.
        
        Args:
            config_path: Path to model configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize state
        self.loaded_model = None
        self.model_status = {
            "loaded": False,
            "name": None,
            "memory_usage": 0,
            "ready": False,
            "device": "none"
        }
        
        # Ollama API settings
        self.ollama_base_url = self.config.get("ollama_base_url", "http://localhost:11434/api")
        
        print("Model manager initialized successfully")
        
        # IMPORTANT: Don't call async methods in __init__
        # The async initialization will be done in initialize() method
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load model configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "model_directory": "models",
            "auto_load_model": False,
            "default_model": "mixtral",
            "ollama_base_url": "http://localhost:11434/api",
            "models": {
                "mixtral": {
                    "type": "ollama",
                    "ollama_model": "mixtral:latest",
                    "max_context_length": 8192,
                    "requires_gpu": True
                }
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with default config
                # Simple merge for now
                for key, value in loaded_config.items():
                    if key == "models" and isinstance(default_config["models"], dict) and isinstance(value, dict):
                        default_config["models"].update(value)
                    else:
                        default_config[key] = value
            except Exception as e:
                print(f"Error loading model config: {e}. Using defaults.")
        
        return default_config
    
    async def initialize(self) -> bool:
        """Initialize the model manager asynchronously.
        
        Returns:
            Success flag
        """
        # Check Ollama service availability
        service_available = await self._check_ollama_service()
        if not service_available:
            print("❌ Ollama service is not available - cannot initialize model manager")
            return False

        # ALWAYS check default model availability
        model_name = self.config.get("default_model")
        if model_name:
            print(f"Checking model availability: {model_name}")
            model_available = await self._check_model_availability(model_name)
            
            # Auto-load model if configured
            if model_available and self.config.get("auto_load_model"):
                success = await self.load_model(model_name)
                if success:
                    print(f"Successfully loaded model: {model_name}")
                else:
                    print(f"Failed to load model: {model_name}")
                return success
            elif not model_available:
                print(f"Model {model_name} is not available in Ollama")
                return False
            
            return True
        
        return False
    
    async def _check_ollama_service(self) -> bool:
        """Check if Ollama service is available.
        
        Returns:
            Boolean indicating if Ollama is available
        """
        try:
            result = await self._make_ollama_request("GET", "/version")
            if result.get("success", False):
                version = result.get("data", {}).get("version", "unknown")
                print(f"✅ Ollama service available (version: {version})")
                return True
            else:
                print(f"❌ Ollama service not available: {result.get('error')}")
                return False
        except Exception as e:
            print(f"❌ Error checking Ollama service: {e}")
            return False

    async def _check_model_availability(self, model_name: str) -> bool:
        """Check if a model is available in Ollama.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            Boolean indicating if model is available
        """
        # Get model config
        model_config = self.config["models"].get(model_name)
        if not model_config:
            print(f"Model '{model_name}' not found in configuration")
            return False
            
        # Get actual Ollama model name
        ollama_model = model_config.get("ollama_model", model_name)
        
        # List available models
        result = await self._make_ollama_request("GET", "/tags")
        if not result.get("success", False):
            print(f"Failed to get models list from Ollama: {result.get('error')}")
            return False
            
        # Check if model exists
        available_models = result.get("data", {}).get("models", [])
        model_exists = any(m.get("name") == ollama_model for m in available_models)
        
        if model_exists:
            print(f"✅ Model '{ollama_model}' is available in Ollama")
            return True
        else:
            print(f"❌ Model '{ollama_model}' is not available in Ollama")
            print(f"Available models: {[m.get('name') for m in available_models]}")
            return False
    
    async def load_model(self, model_name: str) -> bool:
        """Load a model via Ollama API.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            Success flag
        """
        # Check if model exists in config
        if model_name not in self.config["models"]:
            print(f"Model '{model_name}' not found in configuration")
            return False
        
        # Check if already loaded
        if self.model_status["loaded"] and self.model_status["name"] == model_name:
            print(f"Model '{model_name}' already loaded")
            return True
        
        # Unload current model if any
        if self.model_status["loaded"]:
            await self.unload_model()
        
        # Get model config
        model_config = self.config["models"][model_name]
        
        # Get actual Ollama model name
        ollama_model = model_config.get("ollama_model", model_name)
        
        # Check if model is available
        if not await self._check_model_availability(model_name):
            print(f"Model '{ollama_model}' not available in Ollama")
            return False
        
        try:
            # For Ollama, we don't actually "load" the model in the traditional sense
            # We just verify it's available and set it as the current model
            
            # Get model info - skip using the /show endpoint which might not be available
            # Instead, just use what we already have from the model check
            
            # Update status directly without extra API calls
            self.model_status = {
                "loaded": True,
                "name": model_name,
                "ollama_model": ollama_model,
                "memory_usage": 0,  # We don't have this info without /show endpoint
                "ready": True,
                "config": model_config,
                "device": "unknown"  # We don't know this without /show endpoint
            }
            
            print(f"Model '{model_name}' (Ollama: {ollama_model}) loaded successfully")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model_status = {
                "loaded": False,
                "name": None,
                "memory_usage": 0,
                "ready": False,
                "error": str(e)
            }
            return False
    
    async def unload_model(self) -> bool:
        """Unload the currently loaded model.
        
        Returns:
            Success flag
        """
        if not self.model_status["loaded"]:
            print("No model currently loaded")
            return False
        
        # For Ollama, we don't actually "unload" the model
        # We just update our status
        print(f"Unloading model '{self.model_status['name']}'...")
        
        try:
            # Reset model status
            self.model_status = {
                "loaded": False,
                "name": None,
                "memory_usage": 0,
                "ready": False,
                "device": "none"
            }
            
            print("Model unloaded successfully")
            return True
        except Exception as e:
            print(f"Error unloading model: {e}")
            return False

    def has_model_loaded(self) -> bool:
        """Check if a model is currently loaded.
    
        Returns:
            Boolean indicating if a model is loaded and ready
        """
        return self.model_status["loaded"] and self.model_status["ready"]

    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded.
        
        Returns:
            Boolean indicating if a model is loaded and ready
        """
        return self.has_model_loaded()

    async def load_default_model(self) -> bool:
        """Load the default model.
        
        Returns:
            Success flag
        """
        model_name = self.config.get("default_model")
        if not model_name:
            print("No default model specified in configuration")
            return False
            
        return await self.load_model(model_name)

    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status.
        
        Returns:
            Model status dictionary
        """
        return self.model_status
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get all available models from configuration.
        
        Returns:
            Dictionary of available models
        """
        return self.config["models"]
    
    async def _make_ollama_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the Ollama API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Response dictionary
        """
        url = f"{self.ollama_base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url) as response:
                        if response.status == 200:
                            json_data = await response.json()
                            return {
                                "success": True,
                                "data": json_data
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}: {await response.text()}"
                            }
                elif method == "POST":
                    headers = {"Content-Type": "application/json"}
                    async with session.post(url, json=data, headers=headers) as response:
                        if response.status == 200:
                            json_data = await response.json()
                            return {
                                "success": True,
                                "data": json_data
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}: {await response.text()}"
                            }
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported HTTP method: {method}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_response(self, prompt: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a response from the model using Ollama API.
        
        Args:
            prompt: Input prompt to the model
            params: Generation parameters
            
        Returns:
            Response dictionary with generated text
        """
        if not self.model_status["loaded"] or not self.model_status["ready"]:
            return {
                "success": False,
                "error": "No model loaded or model not ready",
                "text": None
            }
            
        # Default parameters
        default_params = {
            "num_predict": 512,  # Ollama's equivalent to max_new_tokens
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
        
        # Merge with provided params
        if params:
            for key, value in params.items():
                # Map common parameters to Ollama equivalents
                if key == "max_new_tokens":
                    default_params["num_predict"] = value
                elif key == "repetition_penalty":
                    default_params["repeat_penalty"] = value
                else:
                    default_params[key] = value
                
        try:
            # Prepare request data
            request_data = {
                "model": self.model_status["ollama_model"],
                "prompt": prompt,
                "options": default_params,
                "stream": False  # Don't stream the response
            }
            
            # Make request to Ollama API
            result = await self._make_ollama_request("POST", "/generate", request_data)
            
            if not result.get("success", False):
                print(f"Error from Ollama API: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error"),
                    "text": None
                }
                
            response_data = result.get("data", {})
            
            # Extract response text and token usage
            return {
                "success": True,
                "text": response_data.get("response", ""),
                "usage": {
                    "prompt_tokens": response_data.get("prompt_eval_count", 0),
                    "completion_tokens": response_data.get("eval_count", 0),
                    "total_tokens": (response_data.get("prompt_eval_count", 0) + 
                                    response_data.get("eval_count", 0))
                }
            }
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": None
            }
    
    async def generate_streaming_response(self, prompt: str, params: Dict[str, Any] = None):
        """Generate a streaming response from the model using Ollama API.
        
        Args:
            prompt: Input prompt to the model
            params: Generation parameters
            
        Yields:
            Response chunks
        """
        if not self.model_status["loaded"] or not self.model_status["ready"]:
            yield {
                "success": False,
                "error": "No model loaded or model not ready",
                "text": None,
                "done": True
            }
            return
            
        # Default parameters
        default_params = {
            "num_predict": 512,  # Ollama's equivalent to max_new_tokens
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
        
        # Merge with provided params
        if params:
            for key, value in params.items():
                # Map common parameters to Ollama equivalents
                if key == "max_new_tokens":
                    default_params["num_predict"] = value
                elif key == "repetition_penalty":
                    default_params["repeat_penalty"] = value
                else:
                    default_params[key] = value
        
        # Prepare request data
        request_data = {
            "model": self.model_status["ollama_model"],
            "prompt": prompt,
            "options": default_params,
            "stream": True  # Stream the response
        }
        
        url = f"{self.ollama_base_url}/generate"
        headers = {"Content-Type": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=request_data, headers=headers) as response:
                    if response.status != 200:
                        yield {
                            "success": False,
                            "error": f"HTTP {response.status}: {await response.text()}",
                            "text": None,
                            "done": True
                        }
                        return
                        
                    # Process the streaming response
                    full_text = ""
                    prompt_tokens = 0
                    completion_tokens = 0
                    
                    async for line in response.content:
                        if not line.strip():
                            continue
                            
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            full_text += chunk
                            
                            # Update token counts if available
                            if "prompt_eval_count" in data and prompt_tokens == 0:
                                prompt_tokens = data["prompt_eval_count"]
                            if "eval_count" in data:
                                completion_tokens = data["eval_count"]
                                
                            yield {
                                "success": True,
                                "chunk": chunk,
                                "done": data.get("done", False)
                            }
                            
                            # If we're done, break the loop
                            if data.get("done", False):
                                yield {
                                    "success": True,
                                    "text": full_text,
                                    "usage": {
                                        "prompt_tokens": prompt_tokens,
                                        "completion_tokens": completion_tokens,
                                        "total_tokens": prompt_tokens + completion_tokens
                                    },
                                    "done": True
                                }
                                break
                                
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON from Ollama: {line}")
                            continue
                    
        except Exception as e:
            print(f"Error generating streaming response: {e}")
            yield {
                "success": False,
                "error": str(e),
                "text": None,
                "done": True
            }
    
    async def list_ollama_models(self) -> List[str]:
        """List all available models in Ollama.
        
        Returns:
            List of available model names
        """
        result = await self._make_ollama_request("GET", "/tags")
        if not result.get("success", False):
            print(f"Failed to get models list from Ollama: {result.get('error')}")
            return []
            
        available_models = result.get("data", {}).get("models", [])
        return [m.get("name") for m in available_models]