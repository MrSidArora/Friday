# core/model_adapters/mixtral_adapter.py
import os
import logging
import asyncio
import subprocess
import json
import time
from datetime import datetime

class MixtralAdapter:
    """Adapter for Mixtral 8x7B quantized model."""
    
    def __init__(self, model_path=None, config=None):
        """Initialize the Mixtral adapter."""
        self.model_path = model_path or os.environ.get("MIXTRAL_MODEL_PATH", "models/mixtral-8x7b-instruct-v0.1-4bit")
        self.config = config or {}
        self.logger = logging.getLogger('friday.mixtral_adapter')
        self.loaded = False
        self.model_process = None
        self.api_url = self.config.get("api_url", "http://localhost:8000/v1")
        self.startup_timeout = self.config.get("startup_timeout", 60)  # seconds
    
    async def load_model(self):
        """Load the Mixtral model."""
        if self.loaded:
            return True
        
        try:
            # Check if model files exist
            if not os.path.exists(self.model_path):
                self.logger.error(f"Model path does not exist: {self.model_path}")
                return False
            
            # Start model server subprocess
            cmd = [
                "python", "-m", "llama_cpp.server", 
                "--model", self.model_path,
                "--n_ctx", str(self.config.get("context_size", 4096)),
                "--n_gpu_layers", str(self.config.get("gpu_layers", 33)),
                "--port", str(self.config.get("port", 8000))
            ]
            
            self.logger.info(f"Starting Mixtral model server with command: {' '.join(cmd)}")
            
            # Start the process and capture output
            self.model_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for model to load (check if server is responding)
            start_time = time.time()
            while time.time() - start_time < self.startup_timeout:
                # Try to ping the server
                try:
                    import requests
                    response = requests.get(f"{self.api_url}/health")
                    if response.status_code == 200:
                        self.loaded = True
                        self.logger.info("Mixtral model loaded successfully")
                        return True
                except:
                    # Wait and try again
                    await asyncio.sleep(1)
            
            # If we get here, the server didn't start in time
            self.logger.error("Failed to start Mixtral model server within timeout")
            if self.model_process:
                self.model_process.terminate()
                self.model_process = None
            return False
        
        except Exception as e:
            self.logger.error(f"Error loading Mixtral model: {e}")
            if self.model_process:
                self.model_process.terminate()
                self.model_process = None
            return False
    
    async def unload_model(self):
        """Unload the Mixtral model."""
        if not self.loaded:
            return True
        
        try:
            if self.model_process:
                self.model_process.terminate()
                self.model_process = None
            
            self.loaded = False
            self.logger.info("Mixtral model unloaded")
            return True
        
        except Exception as e:
            self.logger.error(f"Error unloading Mixtral model: {e}")
            return False
    
    async def generate(self, prompt, settings=None):
        """Generate a response from the model."""
        if not self.loaded:
            raise Exception("Model is not loaded")
        
        try:
            # Prepare request settings
            request_settings = {
                "temperature": 0.7,
                "max_tokens": 1024,
                "top_p": 0.9,
                "stop": [],
                "stream": False
            }
            
            # Update with user settings if provided
            if settings:
                request_settings.update(settings)
            
            # Make API request
            import requests
            response = requests.post(
                f"{self.api_url}/completions",
                json={
                    "prompt": prompt,
                    "temperature": request_settings["temperature"],
                    "max_tokens": request_settings["max_tokens"],
                    "top_p": request_settings["top_p"],
                    "stop": request_settings["stop"],
                    "stream": request_settings["stream"]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")
            
            result = response.json()
            
            # Format response
            formatted_response = {
                "text": result["choices"][0]["text"],
                "usage": {
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0)
                },
                "model": "mixtral-8x7b-instruct-v0.1-4bit",
                "finish_reason": result["choices"][0].get("finish_reason", "stop")
            }
            
            return formatted_response
        
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            raise
    
    def is_loaded(self):
        """Check if the model is loaded."""
        return self.loaded
    
    def get_model_info(self):
        """Get information about the model."""
        return {
            "model_id": "mixtral-8x7b-instruct-v0.1-4bit",
            "model_path": self.model_path,
            "loaded": self.loaded,
            "parameters": "8x7B parameters (MoE)",
            "quantization": "4-bit quantized",
            "context_size": self.config.get("context_size", 4096),
            "gpu_layers": self.config.get("gpu_layers", 33)
        }