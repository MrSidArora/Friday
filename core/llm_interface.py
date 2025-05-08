# core/llm_interface.py
"""
Friday AI - LLM Interface

This module provides an abstraction layer for interacting with LLMs,
including both local models through Ollama and external APIs if needed.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
import requests
import json

class LLMInterface:
    def __init__(self, model_manager, memory_system, config_path=None):
        """Initialize the LLM interface.
        
        Args:
            model_manager: ModelManager instance
            memory_system: MemorySystem instance
            config_path: Path to configuration file
        """
        self.model_manager = model_manager
        self.memory_system = memory_system
        self.config = self._load_config(config_path)
        self.api_interface = None
        self.logger = logging.getLogger("llm_interface")
        self.conversation_history = []
        
        # Initialize default template
        self.default_template = self.config.get("prompt_templates", {}).get(
            "conversation",
            "You are Friday, a helpful AI assistant.\n\nUser: {prompt}\nFriday:"
        )
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load model configuration from file."""
        default_config = {
            "default_model": "mixtral",
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "api_enabled": True,
            "streaming_enabled": True,
            "use_external_apis": False,
            "prompt_templates": {
                "conversation": "You are Friday, a helpful AI assistant. You are talking to a user named {user_name}.\n\nPrevious conversation:\n{conversation_history}\n\nUser: {prompt}\nFriday:",
                "reasoning": "You are Friday, a helpful AI assistant with strong reasoning capabilities. Think through this problem step by step.\n\nProblem: {prompt}\n\nSolution:",
                "code": "You are Friday, a helpful AI assistant skilled in programming. Generate code for the following request.\n\nRequest: {prompt}\n\nCode:",
                "summarization": "You are Friday, a helpful AI assistant. Summarize the following text concisely while preserving the key points.\n\nText: {prompt}\n\nSummary:"
            },
            "external_api_priority": ["openai", "google"]
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with default config
                for key, value in loaded_config.items():
                    if key == "prompt_templates" and isinstance(default_config["prompt_templates"], dict) and isinstance(value, dict):
                        default_config["prompt_templates"].update(value)
                    else:
                        default_config[key] = value
            except Exception as e:
                self.logger.error(f"Error loading LLM config: {e}. Using defaults.")
        
        return default_config
        
    async def setup_network(self, api_interface):
        """Set up network access for the LLM interface.
        
        Args:
            api_interface: ApiInterface instance
        """
        self.api_interface = api_interface
        self.logger.info("Network access set up for LLM interface")
        
    async def initialize(self) -> bool:
        """Initialize the LLM interface - ensure model is loaded."""
        self.logger.info("Initializing LLM interface...")
        
        # Check if we have a model manager
        if not self.model_manager:
            self.logger.error("No model manager available")
            return False
        
        # Check if model is already loaded
        try:
            if self.model_manager.is_model_loaded():
                self.logger.info("Model already loaded")
                return True
        except Exception as e:
            self.logger.error(f"Error checking if model is loaded: {e}")
            
        # Load the default model
        model_name = self.config.get("default_model")
        if not model_name:
            self.logger.error("No default model specified")
            return False
        
        # Load the model
        try:
            self.logger.info(f"Loading model: {model_name}")
            success = await self.model_manager.load_model(model_name)
            self.logger.info(f"Model loading result: {success}")
            return success
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
        
    async def ask(self, prompt, context=None, intent=None, 
                 template=None, streaming=None, callback=None):
        """Ask the LLM a question.
        
        Args:
            prompt: User's prompt
            context: Additional context for the prompt
            intent: Detected user intent
            template: Template to use (optional)
            streaming: Whether to stream the response (optional)
            callback: Callback function for streaming responses (optional)
            
        Returns:
            Response from the LLM
        """
        self.logger.info(f"Received prompt: {prompt[:50]}... with intent: {intent}")
        
        # Create a default response
        default_response = {
            "text": "I'm Friday, your AI assistant. How can I help you today?",
            "success": True,
            "source": "default"
        }
        
        # Store user prompt in memory if available
        if self.memory_system:
            try:
                await self.memory_system.store_interaction(
                    user_input=prompt,
                    friday_response=None,  # No response yet
                    context=context
                )
            except Exception as e:
                self.logger.error(f"Error storing user interaction: {e}")
        
        # Check if we need to use external API directly
        needs_internet = intent and intent.get("requires_internet", False)
        
        # Determine if local model should be tried first
        try_local_first = True
        if needs_internet and self.api_interface and self.config.get("use_external_apis", False):
            try_local_first = False
            
        # Determine if streaming should be used
        use_streaming = streaming if streaming is not None else self.config.get("streaming_enabled", False)
        
        # Processing logic
        if try_local_first and self.model_manager:
            # Try local model first
            try:
                self.logger.info("Attempting to get response from local model")
                local_response = await self._get_local_response(
                    prompt, context, intent, template, use_streaming, callback
                )
                
                if local_response.get("success", False):
                    response = local_response
                elif self.api_interface and self.config.get("use_external_apis", False):
                    self.logger.info("Local model failed, falling back to external API")
                    response = await self._get_external_response(prompt, context, intent)
                else:
                    # Create a fallback message
                    response = {
                        "text": "I'm sorry, I couldn't generate a response with my local model. " +
                                "Please try a different question or check the model status.",
                        "success": False,
                        "source": "local_fallback"
                    }
            except Exception as e:
                self.logger.error(f"Error with local model: {e}")
                if self.api_interface and self.config.get("use_external_apis", False):
                    self.logger.info("Error with local model, falling back to external API")
                    response = await self._get_external_response(prompt, context, intent)
                else:
                    self.logger.info("Using default response due to errors")
                    response = default_response
        elif self.api_interface and self.config.get("use_external_apis", False):
            # Try external API first
            try:
                self.logger.info("Directly using external API for response")
                response = await self._get_external_response(prompt, context, intent)
            except Exception as e:
                self.logger.error(f"Error with external API: {e}")
                response = default_response
        else:
            # No viable options, use default response
            self.logger.info("No viable response options, using default")
            response = default_response
            
        # Ensure response has text
        if not response.get("text"):
            response["text"] = default_response["text"]
            
        # Store response in memory if available
        if self.memory_system:
            try:
                # Update the interaction with Friday's response
                await self.memory_system.store_interaction(
                    user_input=prompt,
                    friday_response=response["text"],
                    context=context
                )
            except Exception as e:
                self.logger.error(f"Error storing Friday response: {e}")
                
        self.logger.info(f"Returning response from source: {response.get('source', 'unknown')}")
        return response
        
    async def _get_local_response(self, prompt, context, intent, 
                                template=None, streaming=False, callback=None):
        """Get a response from the local model."""
        # Add detailed logging
        self.logger.info("Attempting to get local response...")
        
        # Check if model manager exists and has a model loaded
        if not self.model_manager:
            self.logger.warning("No model manager available")
            return {"success": False, "error": "No model manager available"}
            
        # Check if model is loaded
        model_loaded = False
        try:
            model_loaded = self.model_manager.is_model_loaded()
            self.logger.info(f"Model loaded status: {model_loaded}")
        except Exception as e:
            self.logger.error(f"Error checking if model is loaded: {e}")
            
        if not model_loaded:
            # Try to initialize
            try:
                self.logger.info("Attempting to initialize and load model...")
                success = await self.initialize()
                self.logger.info(f"Model initialization success: {success}")
                if not success:
                    self.logger.warning("Failed to load model")
                    return {"success": False, "error": "No local model available"}
            except Exception as e:
                self.logger.error(f"Error initializing model: {e}")
                return {"success": False, "error": f"Error initializing model: {e}"}
        
        # Prepare the prompt
        self.logger.info("Preparing prompt...")
        prepared_prompt = self._prepare_prompt(prompt, context, intent, template)
        
        # Prepare generation parameters
        params = {
            "temperature": self.config.get("temperature", 0.7),
            "max_new_tokens": self.config.get("max_tokens", 1024),
            "top_p": self.config.get("top_p", 0.9),
            "repetition_penalty": self.config.get("repeat_penalty", 1.1)
        }
        
        # Record start time for metrics
        start_time = time.time()
        
        # Get response from model
        try:
            self.logger.info("Generating response from model...")
            
            if streaming and callback:
                # Use streaming response with callback
                full_text = ""
                async for chunk in self.model_manager.generate_streaming_response(prepared_prompt, params):
                    if not chunk["success"]:
                        return {
                            "success": False, 
                            "error": chunk.get("error", "Unknown streaming error"),
                            "source": "local"
                        }
                    
                    # Call the callback with the chunk
                    callback(chunk["chunk"], chunk["done"])
                    full_text += chunk["chunk"]
                    
                    # If we're done, collect the final response
                    if chunk["done"]:
                        elapsed_time = time.time() - start_time
                        
                        # If response is empty or just whitespace, consider it a failure
                        if not full_text or not full_text.strip():
                            return {
                                "success": False, 
                                "error": "Empty response from model",
                                "source": "local"
                            }
                            
                        return {
                            "text": full_text, 
                            "success": True, 
                            "source": "local",
                            "elapsed_time": elapsed_time
                        }
            else:
                # Use non-streaming response
                model_response = await self.model_manager.generate_response(
                    prompt=prepared_prompt,
                    params=params
                )
                
                self.logger.info(f"Model response received: {model_response.get('success', False)}")
                
                # Record end time
                elapsed_time = time.time() - start_time
                
                # Check if response was successful
                if not model_response.get("success", False):
                    error_msg = model_response.get("error", "Unknown error")
                    self.logger.error(f"Model response failed: {error_msg}")
                    return {
                        "success": False, 
                        "error": error_msg,
                        "source": "local"
                    }
                
                # Extract the text from the response
                response_text = model_response.get("text", "")
                self.logger.info(f"Response text length: {len(response_text)}")
                
                # If response is empty or just whitespace, consider it a failure
                if not response_text or not response_text.strip():
                    self.logger.warning("Empty response from model")
                    return {
                        "success": False, 
                        "error": "Empty response from model",
                        "source": "local"
                    }
                    
                self.logger.info("Returning successful response")
                return {
                    "text": response_text, 
                    "success": True, 
                    "source": "local",
                    "elapsed_time": elapsed_time
                }
                
        except Exception as e:
            self.logger.error(f"Error generating response from local model: {e}")
            return {"success": False, "error": str(e), "source": "local"}
            
    async def _get_external_response(self, prompt, context, intent):
        """Get a response from an external API.
        
        Args:
            prompt: User's prompt
            context: Additional context for the prompt
            intent: Detected user intent
            
        Returns:
            Response from the external API
        """
        # Check if API interface is available
        if not self.api_interface:
            self.logger.warning("No API interface available")
            return {"success": False, "error": "No API interface available"}
            
        # Get API priority
        api_priority = self.config.get("external_api_priority", ["openai", "google"])
        
        # Try APIs in priority order
        for api in api_priority:
            if api == "openai":
                try:
                    openai_response = await self._get_openai_response(prompt, context, intent)
                    if openai_response.get("success", False):
                        return openai_response
                except Exception as e:
                    self.logger.error(f"Error getting OpenAI response: {e}")
                    
            elif api == "google":
                try:
                    # Implement Google API integration if needed
                    pass
                except Exception as e:
                    self.logger.error(f"Error getting Google response: {e}")
                    
        # If all APIs fail, return error
        return {
            "text": "I'm sorry, I couldn't get a response from any of the available APIs. Please try again.",
            "success": False,
            "source": "external_api_error"
        }
            
    async def _get_openai_response(self, prompt, context, intent):
        """Get a response from the OpenAI API.
        
        Args:
            prompt: User's prompt
            context: Additional context for the prompt
            intent: Detected user intent
            
        Returns:
            Response from the OpenAI API
        """
        try:
            # Prepare messages for OpenAI format
            messages = [
                {"role": "system", "content": "You are Friday, a helpful AI assistant with a friendly and professional personality. Respond in a natural, conversational way."},
                {"role": "user", "content": prompt}
            ]
            
            # Add context if available
            if context:
                messages.insert(1, {"role": "system", "content": f"Additional context: {context}"})
                
            # Call OpenAI API
            response = await self.api_interface.call_openai_api(
                endpoint="chat/completions",
                data={
                    "model": "gpt-3.5-turbo",
                    "messages": messages,
                    "temperature": self.config.get("temperature", 0.7),
                    "max_tokens": self.config.get("max_tokens", 1024),
                    "top_p": self.config.get("top_p", 0.9)
                },
                reason="User query"
            )
            
            # Extract text from response
            if response and not response.get("error"):
                # Parse OpenAI response to get the text content
                text = self._extract_text_from_openai_response(response)
                return {"text": text, "success": True, "source": "openai"}
            else:
                return {"success": False, "error": response.get("error", "Unknown error"), "source": "openai"}
                
        except Exception as e:
            self.logger.error(f"Error getting OpenAI response: {e}")
            return {"success": False, "error": str(e), "source": "openai"}
            
    def _extract_text_from_openai_response(self, response):
        """Extract text from OpenAI API response.
        
        Args:
            response: OpenAI API response
            
        Returns:
            Extracted text
        """
        try:
            # Check if response has choices
            if "choices" in response and len(response["choices"]) > 0:
                # Get the first choice
                choice = response["choices"][0]
                
                # Check if choice has message and content
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
                    
            # Fallback to returning the whole response
            return str(response)
        except Exception as e:
            self.logger.error(f"Error extracting text from OpenAI response: {e}")
            return str(response)
            
    def _prepare_prompt(self, prompt, context=None, intent=None, template_name=None):
        """Prepare the prompt for the model.
        
        Args:
            prompt: User's prompt
            context: Additional context for the prompt
            intent: Detected user intent
            template_name: Name of template to use
            
        Returns:
            Prepared prompt
        """
        # Get the template
        if template_name and template_name in self.config.get("prompt_templates", {}):
            template = self.config["prompt_templates"][template_name]
        else:
            # Default to conversation template
            template = self.default_template
            
        # Get conversation history if available
        history_str = ""
        if self.conversation_history:
            # Format the conversation history
            for entry in self.conversation_history[-5:]:  # Last 5 turns
                history_str += f"User: {entry['user']}\nFriday: {entry['friday']}\n\n"
                
        # Format the template with available values
        return template.format(
            prompt=prompt,
            user_name=context.get("user_name", "User") if context else "User",
            conversation_history=history_str,
            context=str(context) if context else "",
            intent=str(intent) if intent else ""
        )
            
    def _should_use_external_api(self, local_response, prompt, intent):
        """Determine if we should use an external API instead of the local model.
        
        Args:
            local_response: Response from the local model
            prompt: User's prompt
            intent: Detected user intent
            
        Returns:
            True if we should use an external API, False otherwise
        """
        # Check if local response failed
        if not local_response.get("success", False):
            return True
            
        # Check if external APIs are enabled
        if not self.config.get("use_external_apis", False):
            return False
            
        # Check if the intent indicates a need for external resources
        if intent and intent.get("requires_external_resources", False):
            return True
            
        # Default to using local model
        return False
        
    async def search_web(self, query, results_count=5):
        """Search the web for information.
        
        Args:
            query: Search query
            results_count: Number of results to return
            
        Returns:
            Search results
        """
        if not self.api_interface:
            self.logger.warning("No API interface available for web search")
            return {"success": False, "error": "No API interface available for web search"}
            
        # Use the API interface to search the web
        try:
            search_result = await self.api_interface.search_web(
                query=query, 
                reason="Web search",
                results_count=results_count
            )
            
            return search_result
        except Exception as e:
            self.logger.error(f"Error searching the web: {e}")
            return {"success": False, "error": str(e)}