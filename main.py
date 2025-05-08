"""
Friday AI - Main Entry Point
Initializes and coordinates the core components of the Friday AI system.
"""

import os
import sys
import asyncio
import argparse
import json
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/friday.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Import core components
from core.model_manager import ModelManager
from core.memory_system import MemorySystem
from core.request_router import RequestRouter
from core.security_monitor import SecurityMonitor
from core.llm_interface import LLMInterface

# Import network components
from network.network_integration import NetworkModule
from ui.http_controller import HttpController

# Import Command Deck components if available
try:
    from command_deck.dashboard_interface import CommandDeckDashboard
    from command_deck.system_metrics import SystemMetricsMonitor
    from command_deck.memory_access_logs import MemoryAccessMonitor
    from command_deck.error_tracker import ErrorTracker
    command_deck_available = True
    logging.info("Command Deck modules available")
except ImportError as e:
    command_deck_available = False
    logging.warning(f"Command Deck modules not available: {e}. Command Deck functionality will be disabled.")

# Import or create the Friday Integrations class
try:
    from friday_integrations import FridayIntegrations
except ImportError:
    logging.warning("FridayIntegrations not found. Creating default implementation.")
    
    class FridayIntegrations:
        """Default implementation of FridayIntegrations when the module is not available."""
        def __init__(self, friday_system):
            self.friday_system = friday_system
            self.system_info_provider = None
            self.web_search_manager = None
            self.model_context_provider = None
            self.api_endpoints = None
            logging.info("Created default FridayIntegrations implementation")
            
        async def initialize(self):
            """Initialize integrations with minimum functionality."""
            # Create config paths
            os.makedirs("configs", exist_ok=True)
            
            # Create system_info_config.json if it doesn't exist
            system_info_config_path = "configs/system_info_config.json"
            if not os.path.exists(system_info_config_path):
                with open(system_info_config_path, 'w') as f:
                    json.dump({
                        "update_interval": 5,
                        "monitor_processes": True,
                        "monitor_startup_items": True,
                        "monitor_sensors": True,
                        "monitor_network": True,
                        "weather_api_key": None,
                        "weather_location": None,
                        "display_in_ui": True,
                        "display_update_interval": 5000,
                        "include_in_model_context": True
                    }, f, indent=2)
                    
            # Create web_search_config.json if it doesn't exist
            web_search_config_path = "configs/web_search_config.json"
            if not os.path.exists(web_search_config_path):
                with open(web_search_config_path, 'w') as f:
                    json.dump({
                        "search_engines": {
                            "default": "duckduckgo",
                            "duckduckgo": {
                                "enabled": True,
                                "base_url": "https://html.duckduckgo.com/html/?q=",
                                "requires_api_key": False
                            }
                        },
                        "max_results": 5,
                        "safe_search": True,
                        "log_searches": True,
                        "cache_enabled": True,
                        "cache_ttl": 3600,
                        "max_snippets_per_query": 3,
                        "max_snippet_length": 200,
                        "include_in_model_context": True,
                        "auto_search_for_queries": False
                    }, f, indent=2)
            
            logging.info("Created default configuration files for integrations")
            logging.info("To enable full integrations, please install the friday_integrations.py module")
            
            return self

class FridaySystem:
    def __init__(self, config_path: str = None):
        """Initialize the Friday AI system.
        
        Args:
            config_path: Path to main configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        logging.info("Starting Friday AI system...")
        
        # Initialize core components
        self.security_monitor = self._init_security_monitor()
        self.memory_system = self._init_memory_system()
        self.model_manager = self._init_model_manager()
        
        # Initialize HTTP controller
        self.http_controller = self._init_http_controller()
        self.http_controller.set_friday_system(self)

        # Network module will be initialized in initialize_friday()
        self.network_module = None
        
        # Initialize LLM interface
        self.llm_interface = self._init_llm_interface()
        
        # Initialize request router
        self.request_router = self._init_request_router()
        
        # Speech components will be initialized in initialize_friday()
        self.whisper_client = None
        self.piper_tts = None
        
        # Command Deck will be initialized in initialize_friday() if available
        self.command_deck = None
        
        logging.info("Friday AI system initialization complete")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load system configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "system": {
                "name": "Friday",
                "version": "0.1.0",
                "development_mode": True
            },
            "paths": {
                "models": "models",
                "data": "data",
                "logs": "logs",
                "configs": "configs"
            },
            "components": {
                "model_manager": {
                    "config_path": "configs/model_config.json",
                    "enabled": True
                },
                "memory_system": {
                    "config_path": "configs/memory_config.json",
                    "enabled": True
                },
                "security_monitor": {
                    "config_path": "configs/security_config.json",
                    "enabled": True
                },
                "llm_interface": {
                    "config_path": "configs/llm_config.json",
                    "enabled": True
                },
                "network": {
                    "config_path": "configs/network_config.json",
                    "enabled": True,
                    "online_by_default": False
                },
                "http_controller": {
                    "port": 5000,
                    "enabled": True
                },
                "command_deck": {
                    "config_path": "configs/command_deck_config.json",
                    "enabled": True
                },
                "speech": {
                    "enabled": False,
                    "whisper_model": "small",
                    "piper_voice": "en_US-lessac-medium"
                }
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with default config
                # Deep merge would be better but keeping it simple for now
                for section in loaded_config:
                    if section in default_config:
                        if isinstance(default_config[section], dict) and isinstance(loaded_config[section], dict):
                            default_config[section].update(loaded_config[section])
                        else:
                            default_config[section] = loaded_config[section]
                    else:
                        default_config[section] = loaded_config[section]
            except Exception as e:
                logging.error(f"Error loading config: {e}. Using defaults.")
                
        # Ensure necessary directories exist
        for dir_key, dir_path in default_config["paths"].items():
            os.makedirs(dir_path, exist_ok=True)
            
        # Ensure config directory exists
        os.makedirs("configs", exist_ok=True)
        
        return default_config
    
    def _init_security_monitor(self) -> SecurityMonitor:
        """Initialize the security monitoring system.
        
        Returns:
            SecurityMonitor instance
        """
        if not self.config["components"]["security_monitor"]["enabled"]:
            logging.info("Security monitor disabled in configuration")
            return None
            
        try:
            config_path = self.config["components"]["security_monitor"]["config_path"]
            # Ensure the file exists before passing it to SecurityMonitor
            if not os.path.exists(config_path):
                with open(config_path, 'w') as f:
                    json.dump({
                        "logging": {
                            "level": "INFO",
                            "file_path": "logs/security.log",
                            "max_size_mb": 10,
                            "backup_count": 5
                        },
                        "monitoring": {
                            "check_interval_seconds": 60,
                            "thresholds": {
                                "cpu_warning": 80.0,
                                "cpu_critical": 95.0,
                                "memory_warning": 80.0,
                                "memory_critical": 95.0,
                                "disk_warning": 85.0,
                                "disk_critical": 95.0
                            }
                        },
                        "security": {
                            "log_api_access": True,
                            "log_internet_access": True,
                            "require_confirmation_for_system_commands": True
                        }
                    }, f, indent=2)
            return SecurityMonitor(config_path)
        except Exception as e:
            logging.error(f"Error initializing security monitor: {e}")
            return None
    
    def _init_memory_system(self) -> MemorySystem:
        """Initialize the memory system.
        
        Returns:
            MemorySystem instance
        """
        if not self.config["components"]["memory_system"]["enabled"]:
            logging.info("Memory system disabled in configuration")
            return None
            
        try:
            config_path = self.config["components"]["memory_system"]["config_path"]
            # Ensure the file exists before passing it to MemorySystem
            if not os.path.exists(config_path):
                with open(config_path, 'w') as f:
                    json.dump({
                        "short_term": {
                            "host": "localhost",
                            "port": 6379,
                            "db": 0,
                            "ttl": 3600
                        },
                        "mid_term": {
                            "db_path": "data/memory/mid_term.db",
                            "retention_days": 30
                        },
                        "long_term": {
                            "db_path": "data/memory/long_term",
                            "similarity_threshold": 0.75
                        }
                    }, f, indent=2)
            return MemorySystem(config_path)
        except Exception as e:
            logging.error(f"Error initializing memory system: {e}")
            return None
    
    def _init_model_manager(self) -> ModelManager:
        """Initialize the model manager.
        
        Returns:
            ModelManager instance
        """
        if not self.config["components"]["model_manager"]["enabled"]:
            logging.info("Model manager disabled in configuration")
            return None
            
        try:
            config_path = self.config["components"]["model_manager"]["config_path"]
            # Ensure the file exists before passing it to ModelManager
            if not os.path.exists(config_path):
                with open(config_path, 'w') as f:
                    json.dump({
                        "model_directory": "models",
                        "auto_load_model": False,
                        "default_model": "mixtral-8x7b-instruct-v0.1-4bit",
                        "models": {
                            "mixtral-8x7b-instruct-v0.1-4bit": {
                                "type": "mixtral",
                                "path": "mixtral-8x7b-instruct-v0.1-4bit",
                                "quantization": "4bit",
                                "max_context_length": 8192,
                                "requires_gpu": True
                            }
                        }
                    }, f, indent=2)
            return ModelManager(config_path)
        except Exception as e:
            logging.error(f"Error initializing model manager: {e}")
            return None
            
    def _init_llm_interface(self) -> LLMInterface:
        """Initialize the LLM interface.
        
        Returns:
            LLMInterface instance
        """
        if not self.config["components"]["llm_interface"]["enabled"]:
            logging.info("LLM interface disabled in configuration")
            return None
            
        try:
            config_path = self.config["components"]["llm_interface"]["config_path"]
            # Create an empty LLM config if it doesn't exist
            if not os.path.exists(config_path):
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump({
                        "temperature": 0.7,
                        "max_tokens": 1024,
                        "top_p": 0.9,
                        "use_external_apis": False,
                        "external_api_priority": ["local", "openai", "google"]
                    }, f, indent=2)
                    
            return LLMInterface(
                model_manager=self.model_manager,
                memory_system=self.memory_system,
                config_path=config_path
            )
        except Exception as e:
            logging.error(f"Error initializing LLM interface: {e}")
            return None
            
    def _init_http_controller(self) -> HttpController:
        """Initialize the HTTP controller for UI communication.
        
        Returns:
            HttpController instance
        """
        if not self.config["components"]["http_controller"]["enabled"]:
            logging.info("HTTP controller disabled in configuration")
            return None
            
        try:
            port = self.config["components"]["http_controller"]["port"]
            controller = HttpController(port=port)
            return controller
        except Exception as e:
            logging.error(f"Error initializing HTTP controller: {e}")
            return None
    
    def _init_request_router(self) -> RequestRouter:
        """Initialize the request router.
        
        Returns:
            RequestRouter instance
        """
        try:
            return RequestRouter(
                memory_system=self.memory_system,
                model_manager=self.model_manager,
                llm_interface=self.llm_interface
            )
        except Exception as e:
            logging.error(f"Error initializing request router: {e}")
            # Create a simple fallback request router
            class SimpleRequestRouter:
                async def route_request(self, user_input):
                    return {
                        "text": "I don't have a model loaded yet, so I'm using a simple response instead. My name is Friday, an AI assistant. How can I help you today?"
                    }
            return SimpleRequestRouter()
    
    async def _init_command_deck(self):
        """Initialize the Command Deck dashboard if available.
        
        Returns:
            CommandDeckDashboard instance or None
        """
        # Skip if Command Deck is disabled in configuration
        if not self.config["components"].get("command_deck", {}).get("enabled", False):
            logging.info("Command Deck disabled in configuration")
            return None
        
        # Skip if Command Deck modules are not available
        if not command_deck_available:
            logging.warning("Command Deck enabled in configuration but modules not available")
            return None
        
        try:
            # Create Command Deck directory if it doesn't exist
            os.makedirs("command_deck", exist_ok=True)
            
            # Ensure config file exists
            config_path = self.config["components"]["command_deck"]["config_path"]
            if not os.path.exists(config_path):
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump({
                        "refresh_rate": 5,
                        "error_log_limit": 100,
                        "default_panels": [
                            "system_metrics", 
                            "memory_access", 
                            "error_tracker"
                        ],
                        "ui_theme": "dark",
                        "enable_remote_access": False,
                        "logging": {
                            "level": "INFO",
                            "file": "logs/command_deck.log"
                        },
                        "memory_monitor": {
                            "log_limit": 200,
                            "include_details": True
                        },
                        "system_metrics": {
                            "history_limit": 100,
                            "update_interval": 5,
                            "warning_thresholds": {
                                "cpu": 75,
                                "memory": 80,
                                "disk": 85
                            },
                            "critical_thresholds": {
                                "cpu": 90,
                                "memory": 90,
                                "disk": 95
                            }
                        },
                        "error_tracker": {
                            "log_limit": 1000,
                            "update_interval": 10,
                            "monitored_logs": [
                                "friday_system.log",
                                "core.log",
                                "memory.log",
                                "llm.log",
                                "intent.log",
                                "internet_access.log",
                                "security.log",
                                "personality.log",
                                "api_usage.log"
                            ]
                        }
                    }, f, indent=2)
            
            # Create the Command Deck dashboard
            dashboard = CommandDeckDashboard(http_controller=self.http_controller)
            
            # Initialize components
            metrics_monitor = SystemMetricsMonitor(dashboard)
            error_tracker = ErrorTracker(dashboard)
            memory_monitor = MemoryAccessMonitor(dashboard, self.memory_system)
            self.http_controller.set_command_deck(dashboard)

            # Register system components with dashboard
            dashboard.register_component("friday_system", self)
            dashboard.register_component("memory_system", self.memory_system)
            dashboard.register_component("llm_interface", self.llm_interface)
            dashboard.register_component("model_manager", self.model_manager)
            dashboard.register_component("security_monitor", self.security_monitor)
            if self.network_module:
                dashboard.register_component("network_module", self.network_module)
            
            # Start component monitoring
            asyncio.create_task(metrics_monitor.start_monitoring())
            asyncio.create_task(error_tracker.start_monitoring())
            asyncio.create_task(memory_monitor.start_monitoring())
            
            # Start dashboard update loop
            asyncio.create_task(dashboard.start_dashboard())
            
            logging.info("Command Deck initialized successfully")
            return dashboard
            
        except Exception as e:
            logging.error(f"Error initializing Command Deck: {e}")
            return None
        
    async def initialize_friday(self):
        """Perform async initialization steps that need to happen after the initial setup.
        
        Returns:
            Self, for chaining
        """
        logging.info("Performing async initialization...")
        
        # Start background monitoring if available
        if self.security_monitor:
            self.security_monitor.start_monitoring()
            logging.info("System monitoring started")
            
        # Start HTTP controller if available
        if self.http_controller:
            try:
                await self.http_controller.start()
                logging.info("HTTP controller started")
            except Exception as e:
                logging.error(f"Error starting HTTP controller: {e}")
            
        # Initialize network module if enabled and HTTP controller is available
        if self.config["components"]["network"]["enabled"] and self.http_controller:
            try:
                # Create and initialize network module
                self.network_module = NetworkModule(self.http_controller)
                await self.network_module.initialize()
                
                # Set online status based on configuration
                online_by_default = self.config["components"]["network"]["online_by_default"]
                self.network_module.set_online_status(online_by_default)
                logging.info(f"Network module initialized with online status: {online_by_default}")
                
                # Connect network module to LLM interface if available
                if self.llm_interface:
                    try:
                        # Pass the API interface to the LLM interface
                        api_interface = self.network_module.get_api_interface()
                        await self.llm_interface.setup_network(api_interface)
                        logging.info("Network module connected to LLM interface")
                    except Exception as e:
                        logging.error(f"Error connecting network module to LLM interface: {e}")
                    
                # Test connectivity
                try:
                    connectivity = await self.network_module.test_connectivity()
                    logging.info(f"Internet connectivity test: {connectivity['online']}")
                except Exception as e:
                    logging.error(f"Error testing connectivity: {e}")
            except Exception as e:
                logging.error(f"Error initializing network module: {e}")
                self.network_module = None
        elif self.config["components"]["network"]["enabled"] and not self.http_controller:
            logging.warning("Network module enabled but HTTP controller is not available. Skipping network module initialization.")
            
        # Initialize speech components if enabled
        await self._init_speech_components()
        
        # Initialize Command Deck if available
        self.command_deck = await self._init_command_deck()
                
        logging.info("Async initialization complete")
        return self
    
    async def _init_speech_components(self):
        """Initialize speech recognition and synthesis components."""
        if not self.config["components"].get("speech", {}).get("enabled", False):
            logging.info("Speech components disabled in configuration")
            return
            
        try:
            # Import speech components here to avoid errors if not available
            from speech.whisper_client import WhisperClient
            from speech.piper_tts import PiperTTS
            
            # Get model configuration
            whisper_model = self.config["components"]["speech"].get("whisper_model", "small")
            piper_voice = self.config["components"]["speech"].get("piper_voice", "en_US-lessac-medium")
            
            # Initialize speech recognition
            self.whisper_client = WhisperClient(model=whisper_model)
            logging.info(f"Speech recognition initialized with model: {whisper_model}")
            
            # Initialize text-to-speech
            self.piper_tts = PiperTTS(voice=piper_voice)
            logging.info(f"Text-to-speech initialized with voice: {piper_voice}")
            
            # Connect speech components to HTTP controller if available
            if self.http_controller and hasattr(self.http_controller, 'set_speech_components'):
                self.http_controller.set_speech_components(
                    self.whisper_client, 
                    self.piper_tts
                )
                logging.info("Speech components connected to HTTP controller")
        except ImportError:
            logging.warning("Speech components not available. Make sure Whisper and Piper TTS are installed.")
        except Exception as e:
            logging.error(f"Error initializing speech components: {e}")
    
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process a user request.
        
        Args:
            user_input: User's input text
            
        Returns:
            Response dictionary
        """
        try:
            # Route the request
            response = await self.request_router.route_request(user_input)
            return response
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return {
                "text": "I'm sorry, I encountered an error processing your request. Please try again."
            }
    
    async def shutdown(self) -> None:
        """Gracefully shut down the Friday system."""
        logging.info("Shutting down Friday AI system...")
        
        # Stop security monitoring
        if self.security_monitor:
            try:
                self.security_monitor.stop_monitoring()
                logging.info("Security monitoring stopped")
            except Exception as e:
                logging.error(f"Error stopping security monitor: {e}")
            
        # Shutdown network module if available
        if self.network_module:
            try:
                await self.network_module.shutdown()
                logging.info("Network module shut down")
            except Exception as e:
                logging.error(f"Error shutting down network module: {e}")
            
        # Shutdown HTTP controller if available
        if self.http_controller:
            try:
                await self.http_controller.stop()
                logging.info("HTTP controller shut down")
            except Exception as e:
                logging.error(f"Error shutting down HTTP controller: {e}")
            
        logging.info("Shutdown complete")

# Command-line interface for testing
async def main():
    parser = argparse.ArgumentParser(description="Friday AI System")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--interactive", action="store_true", help="Start in interactive mode")
    parser.add_argument("--server", action="store_true", help="Start in server mode (default)")
    parser.add_argument("--command-deck", action="store_true", help="Launch Command Deck dashboard")
    args = parser.parse_args()
    
    # Initialize the Friday system
    friday = FridaySystem(args.config)
    
    # Run async initialization
    await friday.initialize_friday()

    # Initialize integrations
    try:
        friday_integrations = FridayIntegrations(friday)
        await friday_integrations.initialize()
        logging.info("Friday integrations initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing Friday integrations: {e}")
    
    # Interactive mode for testing
    if args.interactive:
        print("\nFriday AI Interactive Mode")
        print("Type 'exit' or 'quit' to end the session\n")
        
        while True:
            try:
                user_input = input("You: ")
                
                if user_input.lower() in ["exit", "quit"]:
                    break
                    
                # Process the request
                response = await friday.process_request(user_input)
                
                # Display the response
                print(f"Friday: {response.get('text', 'No response')}")
            except Exception as e:
                logging.error(f"Error in interactive mode: {e}")
                print(f"Friday: I encountered an error processing your request. Please try again.")
    
    # Server mode - keep running until interrupted
    elif args.server or (not args.interactive and not args.command_deck):  # Default to server mode
        print("\nFriday AI Server Mode")
        print("HTTP server running on port 5000")
        print("Press Ctrl+C to shutdown\n")
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutdown requested via Ctrl+C")
    
    # Command Deck mode
    elif args.command_deck:
        print("\nFriday AI Command Deck Mode")
        print("Command Deck dashboard available at http://localhost:5000")
        print("Press Ctrl+C to shutdown\n")
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutdown requested via Ctrl+C")
    
    # Gracefully shut down
    await friday.shutdown()

if __name__ == "__main__":
    asyncio.run(main())