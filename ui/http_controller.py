# ui/http_controller.py
"""
Friday AI - HTTP Controller

This module handles HTTP communication between the UI and the Friday AI system.
"""

import json
import logging
import threading
import time
import os
from datetime import datetime
import asyncio
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

from network.internet_controller import InternetController

class HttpController:
    def __init__(self, config=None, port=5000):
        """Initialize the HTTP controller.
        
        Args:
            config: Configuration dictionary
            port: Port to listen on
        """
        # Initialize properties
        self.port = port
        self.server = None
        self.server_thread = None
        self.internet_controller = InternetController()
        self.network_module = None
        self.running = False
        self.logger = logging.getLogger("http_controller")
        
        # Speech components (will be set later if available)
        self.whisper_client = None
        self.piper_tts = None
        
        # Friday system reference (will be set later)
        self.friday_system = None
        
        # Command Deck reference (will be set later)
        self.command_deck = None
        
        # Registered routes for API endpoints
        self.registered_routes = {
            'GET': {},
            'POST': {}
        }
        
        # Set up the callback for domain approval
        self.internet_controller.set_confirmation_callback(self.request_domain_approval)
        
    async def start(self):
        """Start the HTTP controller."""
        # Initialize internet controller
        await self.internet_controller.initialize()
        
        # Start HTTP server if not already running
        if not self.running:
            self._start_http_server()
            self.running = True
            
        self.logger.info("HTTP controller started")
        
    def _start_http_server(self):
        """Start the HTTP server in a separate thread."""
        try:
            # Create server
            self.server = FridayHTTPServer(('0.0.0.0', self.port), 
                                           lambda *args: FridayRequestHandler(self, *args))
            
            # Start server in a separate thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            self.logger.info(f"HTTP server started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Error starting HTTP server: {e}")
            raise
        
    async def stop(self):
        """Stop the HTTP controller."""
        # Stop HTTP server if running
        if self.running:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                if self.server_thread:
                    self.server_thread.join(timeout=5)
                self.server = None
                self.server_thread = None
                
            self.running = False
            
        # Close internet controller
        await self.internet_controller.close()
        self.logger.info("HTTP controller stopped")
        
    def set_network_module(self, network_module):
        """Set the network module for this controller.
        
        Args:
            network_module: NetworkModule instance
        """
        self.network_module = network_module
        self.logger.info("Network module set for HTTP controller")
        
    def set_speech_components(self, whisper_client, piper_tts):
        """Set speech components for this controller.
        
        Args:
            whisper_client: WhisperClient instance
            piper_tts: PiperTTS instance
        """
        self.whisper_client = whisper_client
        self.piper_tts = piper_tts
        self.logger.info("Speech components set for HTTP controller")
        
    def set_friday_system(self, friday_system):
        """Set the Friday system for this controller.
        
        Args:
            friday_system: FridaySystem instance
        """
        self.friday_system = friday_system
        self.logger.info("Friday system set for HTTP controller")
    
    def set_command_deck(self, command_deck):
        """Set the Command Deck for this controller.
        
        Args:
            command_deck: CommandDeckDashboard instance
        """
        self.command_deck = command_deck
        self.logger.info("Command Deck set for HTTP controller")

    def register_route(self, method, path, handler):
        """Register a route handler.
        
        Args:
            method: HTTP method (GET, POST)
            path: URL path
            handler: Handler function
            
        Returns:
            Success flag
        """
        if method not in ['GET', 'POST']:
            self.logger.error(f"Unsupported HTTP method: {method}")
            return False
        
        self.registered_routes.setdefault(method, {})
        self.registered_routes[method][path] = handler
        self.logger.info(f"Registered {method} route: {path}")
        return True
        
    async def request_domain_approval(self, domain, reason):
        """Request domain approval from the user via UI.
        
        Args:
            domain: Domain to approve
            reason: Reason for the request
            
        Returns:
            Dict with approved status
        """
        try:
            # Send request to UI
            response = await self.send_to_ui("request-domain-approval", {
                "domain": domain,
                "reason": reason
            })
            
            return response
        except Exception as e:
            self.logger.error(f"Error requesting domain approval: {str(e)}")
            return {"approved": False}
            
    async def send_to_ui(self, action, data):
        """Send a message to the UI.
        
        Args:
            action: Action name
            data: Data to send
            
        Returns:
            Response from UI
        """
        # This would be implemented to communicate with the UI
        # For now, just simulate a response
        self.logger.info(f"Sending to UI: {action} - {data}")
        
        # For domain approval, prompt in console
        if action == "request-domain-approval":
            domain = data.get("domain", "unknown")
            reason = data.get("reason", "No reason provided")
            
            print(f"\nDomain approval request: {domain}")
            print(f"Reason: {reason}")
            user_input = input(f"Approve domain '{domain}'? (y/n, default: y): ")
            
            return {"approved": user_input.lower() != 'n'}
            
        return {"success": True}
            
    async def handle_request(self, method, endpoint, data):
        """Handle an HTTP request.
        
        Args:
            method: HTTP method
            endpoint: Endpoint path
            data: Request data
            
        Returns:
            Response data and status code
        """
        # Check if endpoint is registered in the routes
        if endpoint in self.registered_routes.get(method, {}):
            handler = self.registered_routes[method][endpoint]
            try:
                # Call the handler function
                result = handler(data) if method == 'POST' else handler()
                
                # If result is a coroutine (async), await it
                if asyncio.iscoroutine(result):
                    result = await result
                    
                return result, 200
            except Exception as e:
                self.logger.error(f"Error in handler for {endpoint}: {e}")
                return {"error": str(e)}, 500
        
        # Web request endpoint
        if endpoint == "/web_request":
            # Validate required fields
            required_fields = ["url", "method"]
            for field in required_fields:
                if field not in data:
                    return {"error": f"Missing required field: {field}"}, 400

            # Extract parameters
            url = data["url"]
            request_method = data.get("method", "GET")
            request_data = data.get("data")
            headers = data.get("headers")
            reason = data.get("reason")
            require_confirmation = data.get("require_confirmation", True)
            
            # Make the web request
            result = await self.internet_controller.request(
                url=url,
                method=request_method,
                data=request_data,
                headers=headers,
                reason=reason,
                require_confirmation=require_confirmation
            )
            
            return result, 200 if result["success"] else 400
        
        # Online status endpoint
        elif endpoint == "/set_online_status":
            # Validate required fields
            if "online" not in data:
                return {"error": "Missing required field: online"}, 400
            
            online = data["online"]
        
            # Update internet controller status
            if hasattr(self, 'network_module') and self.network_module:
                # Enable/disable internet access
                self.network_module.set_online_status(online)
                return {"success": True, "online": online}, 200
            else:
                return {"error": "Network module not initialized"}, 500
        
        # User message endpoint
        elif endpoint == "/message":
            # Process a user message
            text = data.get("text")
            if not text:
                return {"error": "Missing text in message"}, 400
                
            # Forward to Friday system if available
            if hasattr(self, 'friday_system') and self.friday_system:
                try:
                    response = await self.friday_system.process_request(text)
                    # Add timestamp if not present
                    if 'timestamp' not in response:
                        response['timestamp'] = datetime.now().isoformat()
                    return response, 200
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    return {"text": f"I encountered an error: {str(e)}", "error": True}, 200
            else:
                return {"text": "Friday system not connected to HTTP controller", "error": True}, 200
        
        # Speech recognition endpoints
        # Start speech recognition
        elif endpoint == "/speech/start":
            if self.whisper_client:
                try:
                    result = await self.whisper_client.start_recording()
                    return result, 200
                except Exception as e:
                    self.logger.error(f"Error starting speech recognition: {e}")
                    return {"error": f"Error starting speech recognition: {str(e)}", "success": False}, 500
            else:
                return {"error": "Speech recognition not available", "success": False}, 404
                
        # Stop speech recognition and transcribe
        elif endpoint == "/speech/stop":
            if self.whisper_client:
                try:
                    result = await self.whisper_client.stop_recording_and_transcribe()
                    
                    # If successful and piper_tts is available, forward to Friday
                    if result.get("success") and "text" in result and hasattr(self, 'friday_system') and self.friday_system:
                        text = result["text"]
                        friday_response = await self.friday_system.process_request(text)
                        
                        # Speak the response if TTS is available
                        if self.piper_tts and "text" in friday_response:
                            try:
                                await self.piper_tts.speak(friday_response["text"])
                            except Exception as e:
                                self.logger.error(f"Error speaking response: {e}")
                        
                        return {
                            "transcription": text,
                            "response": friday_response.get("text"),
                            "timestamp": datetime.now().isoformat(),
                            "success": True
                        }, 200
                        
                    return result, 200
                except Exception as e:
                    self.logger.error(f"Error with speech recognition: {e}")
                    return {"error": f"Error with speech recognition: {str(e)}", "success": False}, 500
            else:
                return {"error": "Speech recognition not available", "success": False}, 404
                
        # Text to speech
        elif endpoint == "/speech/speak":
            # Text to speech
            text = data.get("text")
            if not text:
                return {"error": "Missing text to speak"}, 400
    
            if self.piper_tts:
                try:
                    result = await self.piper_tts.speak(text)
                    return result, 200
                except Exception as e:
                    self.logger.error(f"Error speaking text: {e}")
                    return {
                        "success": False, 
                        "message": f"Error with text-to-speech: {str(e)}"
                    }, 500
            else:
                self.logger.info(f"TTS not available, but received request to speak: {text[:50]}...")
                return {
                    "success": True,
                    "message": "Speech simulated (TTS not available)"
                }, 200
        
        # Command Deck API endpoints
        elif endpoint == "/api/system_info":
            if self.command_deck:
                try:
                    return await handle_system_info(self.command_deck)
                except Exception as e:
                    self.logger.error(f"Error handling system info request: {e}")
                    return {"status": "error", "error": str(e)}, 500
            else:
                # Return basic system info if Command Deck is not available
                return {
                    "status": "success",
                    "data": {
                        "system": {
                            "running": True,
                            "online": hasattr(self, 'network_module') and 
                                    self.network_module is not None and 
                                    self.network_module.is_online,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                }, 200
        
        elif endpoint == "/api/dashboard":
            if self.command_deck:
                try:
                    return await handle_dashboard_data(self.command_deck)
                except Exception as e:
                    self.logger.error(f"Error handling dashboard data request: {e}")
                    return {"status": "error", "error": str(e)}, 500
            else:
                return {"status": "error", "error": "Command Deck not available"}, 404
        
        elif endpoint == "/api/dashboard/command":
            if self.command_deck:
                try:
                    command = data.get("command")
                    params = data.get("params", {})
                    
                    if not command:
                        return {"status": "error", "error": "No command specified"}, 400
                    
                    result = await self.command_deck.execute_command(command, params)
                    return {"status": "success" if result.get("success", False) else "error", "data": result}, 200
                except Exception as e:
                    self.logger.error(f"Error handling dashboard command: {e}")
                    return {"status": "error", "error": str(e)}, 500
            else:
                return {"status": "error", "error": "Command Deck not available"}, 404
                
        # Status endpoint - now handled in do_GET but kept for backward compatibility        
        elif endpoint == "/status":
            status = {
                "running": True,
                "online": hasattr(self, 'network_module') and 
                          self.network_module is not None and 
                          self.network_module.is_online,
                "speech_available": self.whisper_client is not None,
                "tts_available": self.piper_tts is not None,
                "command_deck_available": self.command_deck is not None,
                "processing": False,
                "timestamp": datetime.now().isoformat()
            }
            return status, 200
                
        # Handle other endpoints
        return {"error": "Unknown endpoint"}, 404


class FridayHTTPServer(HTTPServer):
    """Custom HTTP server for Friday AI."""
    allow_reuse_address = True
    

class FridayRequestHandler(BaseHTTPRequestHandler):
    """Custom request handler for Friday AI."""
    
    def __init__(self, controller, *args, **kwargs):
        """Initialize the request handler.
        
        Args:
            controller: HttpController instance
            *args: Arguments for BaseHTTPRequestHandler
            **kwargs: Keyword arguments for BaseHTTPRequestHandler
        """
        self.controller = controller
        super().__init__(*args, **kwargs)
        
    def _set_headers(self, status_code=200, content_type="application/json"):
        """Set response headers.
        
        Args:
            status_code: HTTP status code
            content_type: Content type
        """
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self._set_headers()
        
    def do_GET(self):
        """Handle GET requests."""
        # Parse URL
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Check if file exists in static folder
        if path != '/' and not path.startswith('/api/'):
            static_file = os.path.join('ui', 'static', path.lstrip('/'))
            if os.path.exists(static_file) and os.path.isfile(static_file):
                return self.serve_static_file(static_file)
        
        # Check if path is registered in routes
        if path in self.controller.registered_routes.get('GET', {}):
            handler = self.controller.registered_routes['GET'][path]
            try:
                # Parse query parameters
                query = urllib.parse.parse_qs(parsed_url.query)
                
                # Set up asyncio loop for async handlers
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Call handler function
                    response = handler(query)
                    
                    # If response is a coroutine (async), await it
                    if asyncio.iscoroutine(response):
                        response = loop.run_until_complete(response)
                    
                    # Send response
                    self._set_headers(200)
                    self.wfile.write(json.dumps(response).encode())
                finally:
                    loop.close()
                    
                return
            except Exception as e:
                self.controller.logger.error(f"Error in GET handler for {path}: {e}")
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return
            
        # Handle status endpoint
        if path == "/status":
            self._set_headers()
            status = {
                "running": True,
                "online": hasattr(self.controller, 'network_module') and 
                          self.controller.network_module is not None and 
                          self.controller.network_module.is_online,
                "speech_available": self.controller.whisper_client is not None,
                "tts_available": self.controller.piper_tts is not None,
                "command_deck_available": self.controller.command_deck is not None,
                "processing": False,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(status).encode())
        # Handle Command Deck endpoint
        elif (path == "/" or path == "/dashboard") and self.controller.command_deck is not None:
            # Serve the Command Deck page
            return self.serve_dashboard_page()
        # Handle main page
        elif path == "/":
            # Serve the main page
            return self.serve_main_page()
        # Handle API endpoints
        elif path.startswith('/api/'):
            # Use asyncio to handle async controller methods
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Handle request
                response, status_code = loop.run_until_complete(
                    self.controller.handle_request('GET', path, {})
                )
                
                # Send response
                self._set_headers(status_code)
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.controller.logger.error(f"Error handling GET request to {path}: {e}")
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            finally:
                loop.close()
        else:
            # Not found
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            
    def do_POST(self):
        """Handle POST requests."""
        # Get content length
        content_length = int(self.headers.get("Content-Length", 0))
        
        # Read request body
        if content_length > 0:
            request_body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(request_body)
            except json.JSONDecodeError:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                return
        else:
            data = {}
            
        # Parse URL
        parsed_url = urllib.parse.urlparse(self.path)
        endpoint = parsed_url.path
        
        # Log the incoming request
        self.controller.logger.info(f"Received POST request to {endpoint}")
        
        # Use asyncio to handle async controller methods
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Handle request
            response, status_code = loop.run_until_complete(
                self.controller.handle_request(self.command, endpoint, data)
            )
            
            # Send response
            self._set_headers(status_code)
            self.wfile.write(json.dumps(response).encode())
            
            # Log the response (basic info only)
            self.controller.logger.info(f"Responded to {endpoint} with status {status_code}")
        except Exception as e:
            self.controller.logger.error(f"Error handling request to {endpoint}: {e}")
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())
        finally:
            loop.close()
    
    def serve_static_file(self, file_path):
        """Serve a static file."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            content_type = 'text/plain'
            if file_path.endswith('.html'):
                content_type = 'text/html'
            elif file_path.endswith('.css'):
                content_type = 'text/css'
            elif file_path.endswith('.js'):
                content_type = 'application/javascript'
            elif file_path.endswith('.json'):
                content_type = 'application/json'
            elif file_path.endswith('.png'):
                content_type = 'image/png'
            elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.controller.logger.error(f"Error serving static file {file_path}: {e}")
            self.send_error(404, f"File not found: {file_path}")
    
    def serve_dashboard_page(self):
        """Serve the Command Deck dashboard page."""
        try:
            # Check for Command Deck HTML file
            dashboard_path = os.path.join('ui', 'command_deck.html')
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(dashboard_path), exist_ok=True)
            
            # If the Command Deck HTML doesn't exist, create it
            if not os.path.exists(dashboard_path):
                with open(dashboard_path, 'w', encoding='utf-8') as f:
                    f.write(get_default_dashboard_html())
            
            with open(dashboard_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.controller.logger.error(f"Error serving dashboard page: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def serve_main_page(self):
        """Serve the main page."""
        try:
            # Check for index.html
            index_path = os.path.join('ui', 'electron_app', 'index.html')
            
            if os.path.exists(index_path):
                with open(index_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            else:
                # Serve a default page if index.html doesn't exist
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Friday AI</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
                        h1 { color: #333; }
                        p { color: #666; }
                        .container { max-width: 800px; margin: 0 auto; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Friday AI</h1>
                        <p>Friday AI is running. Please use the client application to interact with the system.</p>
                        <p><a href="/dashboard">Open Command Deck</a></p>
                    </div>
                </body>
                </html>
                """)
        except Exception as e:
            self.controller.logger.error(f"Error serving main page: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def log_message(self, format, *args):
        """Override to use the logger instead of printing to stderr."""
        return

# Command Deck API handlers
async def handle_system_info(command_deck):
    """Handle GET /api/system_info requests"""
    try:
        # Get basic system info
        import platform
        import psutil
        
        # Get component status from dashboard
        component_status = command_deck.component_status
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Create response
        response = {
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_percent": memory.percent
            },
            "friday": {
                "status": "running",
                "component_status": component_status,
                "uptime": 0  # Will be calculated if available
            }
        }
        
        return {"status": "success", "data": response}
    except Exception as e:
        logging.error(f"Error handling system info request: {e}")
        return {"status": "error", "error": str(e)}

async def handle_dashboard_data(command_deck):
    """Handle GET /api/dashboard requests"""
    try:
        # Force dashboard update
        await command_deck.update_dashboard()
        
        # Create response with panel data
        response = {
            "timestamp": command_deck.last_update.isoformat() if hasattr(command_deck, 'last_update') else datetime.now().isoformat(),
            "panels": {}
        }
        
        for panel in command_deck.active_panels:
            if panel["visible"]:
                try:
                    panel_data = await panel["render"]()
                    response["panels"][panel["id"]] = panel_data
                except Exception as e:
                    logging.error(f"Error rendering panel {panel['id']}: {e}")
                    response["panels"][panel["id"]] = {
                        "error": str(e),
                        "status": "error"
                    }
        
        return {"status": "success", "data": response}
    except Exception as e:
        logging.error(f"Error handling dashboard data request: {e}")
        return {"status": "error", "error": str(e)}

def get_default_dashboard_html():
    """Return default HTML for the Command Deck dashboard."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Friday AI - Command Deck</title>
    <style>
        :root {
            --bg-color: #121212;
            --panel-bg: #1e1e1e;
            --text-color: #e0e0e0;
            --accent-color: #3498db;
            --success-color: #2ecc71;
            --warning-color: #f39c12;
            --error-color: #e74c3c;
            --critical-color: #c0392b;
            --muted-color: #7f8c8d;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        
        header {
            background-color: var(--panel-bg);
            padding: 1rem;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        h1, h2, h3 {
            margin: 0;
            font-weight: 500;
        }
        
        .content {
            padding: 1rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1rem;
        }
        
        .panel {
            background-color: var(--panel-bg);
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            padding: 1rem;
            position: relative;
            overflow: hidden;
        }
        
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            border-bottom: 1px solid #333;
            padding-bottom: 0.5rem;
        }
        
        .panel-controls {
            display: flex;
            gap: 0.5rem;
        }
        
        .panel-content {
            overflow: auto;
            max-height: 400px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-running {
            background-color: var(--success-color);
        }
        
        .status-warning {
            background-color: var(--warning-color);
        }
        
        .status-error {
            background-color: var(--error-color);
        }
        
        .status-critical {
            background-color: var(--critical-color);
        }
        
        .status-unknown {
            background-color: var(--muted-color);
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }
        
        .metric-card {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
            padding: 1rem;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 500;
            margin: 0.5rem 0;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: var(--muted-color);
        }
        
        .log-entry {
            padding: 0.5rem;
            border-bottom: 1px solid #333;
        }
        
        .log-entry:last-child {
            border-bottom: none;
        }
        
        .log-time {
            font-size: 0.8rem;
            color: var(--muted-color);
        }
        
        .log-message {
            margin-top: 0.25rem;
        }
        
        .log-warning {
            border-left: 3px solid var(--warning-color);
            padding-left: 0.5rem;
        }
        
        .log-error {
            border-left: 3px solid var(--error-color);
            padding-left: 0.5rem;
        }
        
        .log-critical {
            border-left: 3px solid var(--critical-color);
            padding-left: 0.5rem;
            background-color: rgba(192, 57, 43, 0.1);
        }
        
        button {
            background-color: var(--accent-color);
            color: white;
            border: none;
            border-radius: 3px;
            padding: 0.5rem 1rem;
            cursor: pointer;
            font-size: 0.9rem;
        }
        
        button:hover {
            background-color: #2980b9;
        }
        
        button.danger {
            background-color: var(--error-color);
        }
        
        button.danger:hover {
            background-color: #c0392b;
        }
        
        .chart-container {
            width: 100%;
            height: 200px;
            margin-top: 1rem;
        }
        
        .refresh-info {
            font-size: 0.8rem;
            color: var(--muted-color);
            margin-top: 1rem;
            text-align: center;
        }
        
        .error-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .memory-stats {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
        }
        
        .memory-tier {
            flex: 1;
            text-align: center;
            padding: 0.5rem;
            border-radius: 5px;
            background-color: rgba(255, 255, 255, 0.05);
            margin: 0 0.25rem;
        }
        
.memory-tier-label {
            font-size: 0.8rem;
            color: var(--muted-color);
        }
        
        .memory-tier-value {
            font-size: 1.2rem;
            margin: 0.25rem 0;
        }
        
        .tooltip {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        
        .tooltip .tooltip-text {
            visibility: hidden;
            width: 200px;
            background-color: #555;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 5px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .tooltip:hover .tooltip-text {
            visibility: visible;
            opacity: 1;
        }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>Friday AI - Command Deck</h1>
            <div id="system-status">
                <span id="status-indicator" class="status-indicator status-unknown"></span>
                <span id="status-text">Connecting...</span>
            </div>
        </div>
        <div>
            <button id="refresh-btn">Refresh</button>
            <button id="diagnostics-btn">Run Diagnostics</button>
        </div>
    </header>
    
    <div class="content">
        <!-- System Metrics Panel -->
        <div class="panel" id="system-metrics-panel">
            <div class="panel-header">
                <h2>System Resources</h2>
                <div class="panel-controls">
                    <span id="system-metrics-status" class="status-indicator status-unknown"></span>
                    <button id="toggle-metrics-btn" class="small">Collapse</button>
                </div>
            </div>
            <div class="panel-content">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-value" id="cpu-usage">0%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Memory Usage</div>
                        <div class="metric-value" id="memory-usage">0%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Disk Usage</div>
                        <div class="metric-value" id="disk-usage">0%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Friday Process</div>
                        <div class="metric-value" id="process-memory">0 MB</div>
                    </div>
                </div>
                
                <div class="chart-container" id="cpu-chart">
                    <!-- CPU Chart will be inserted here -->
                </div>
                
                <div class="chart-container" id="memory-chart">
                    <!-- Memory Chart will be inserted here -->
                </div>
            </div>
        </div>
        
        <!-- Memory Access Panel -->
        <div class="panel" id="memory-access-panel">
            <div class="panel-header">
                <h2>Memory Access</h2>
                <div class="panel-controls">
                    <span id="memory-access-status" class="status-indicator status-unknown"></span>
                    <button id="toggle-memory-btn" class="small">Collapse</button>
                </div>
            </div>
            <div class="panel-content">
                <div class="memory-stats">
                    <div class="memory-tier">
                        <div class="memory-tier-label">Short-term</div>
                        <div class="memory-tier-value" id="short-term-count">-</div>
                    </div>
                    <div class="memory-tier">
                        <div class="memory-tier-label">Mid-term</div>
                        <div class="memory-tier-value" id="mid-term-count">-</div>
                    </div>
                    <div class="memory-tier">
                        <div class="memory-tier-label">Long-term</div>
                        <div class="memory-tier-value" id="long-term-count">-</div>
                    </div>
                </div>
                
                <h3>Recent Memory Operations</h3>
                <div id="memory-access-logs" class="error-list">
                    <!-- Memory logs will be inserted here -->
                </div>
                
                <h3>Memory Errors</h3>
                <div id="memory-error-logs" class="error-list">
                    <!-- Memory error logs will be inserted here -->
                </div>
            </div>
        </div>
        
        <!-- Error Tracking Panel -->
        <div class="panel" id="error-tracking-panel">
            <div class="panel-header">
                <h2>Error Tracking</h2>
                <div class="panel-controls">
                    <span id="error-tracking-status" class="status-indicator status-unknown"></span>
                    <button id="toggle-errors-btn" class="small">Collapse</button>
                </div>
            </div>
            <div class="panel-content">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Critical Errors</div>
                        <div class="metric-value" id="critical-count">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Errors</div>
                        <div class="metric-value" id="error-count">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Warnings</div>
                        <div class="metric-value" id="warning-count">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Log Files</div>
                        <div class="metric-value" id="log-file-count">0</div>
                    </div>
                </div>
                
                <h3>Recent Errors</h3>
                <div id="error-logs" class="error-list">
                    <!-- Error logs will be inserted here -->
                </div>
                
                <div class="refresh-info">
                    <button id="clear-errors-btn" class="danger">Clear Errors</button>
                </div>
            </div>
        </div>
        
        <!-- Component Status Panel -->
        <div class="panel" id="component-status-panel">
            <div class="panel-header">
                <h2>Component Status</h2>
                <div class="panel-controls">
                    <button id="toggle-components-btn" class="small">Collapse</button>
                </div>
            </div>
            <div class="panel-content">
                <div id="component-list">
                    <!-- Component status will be inserted here -->
                </div>
                
                <div class="refresh-info">
                    Last updated: <span id="last-update-time">Never</span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- JavaScript -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Dashboard configuration
        const config = {
            refreshInterval: 5000, // ms
            apiEndpoint: '/api',
            charts: {},
            lastUpdate: null,
            componentStatus: {}
        };
        
        // Initialize the dashboard
        document.addEventListener('DOMContentLoaded', () => {
            // Initial data fetch
            fetchDashboardData();
            
            // Set up refresh interval
            setInterval(fetchDashboardData, config.refreshInterval);
            
            // Set up button handlers
            document.getElementById('refresh-btn').addEventListener('click', fetchDashboardData);
            document.getElementById('diagnostics-btn').addEventListener('click', runDiagnostics);
            document.getElementById('clear-errors-btn').addEventListener('click', clearErrors);
            
            // Toggle panel visibility
            document.getElementById('toggle-metrics-btn').addEventListener('click', function() {
                togglePanel('system-metrics-panel', this);
            });
            
            document.getElementById('toggle-memory-btn').addEventListener('click', function() {
                togglePanel('memory-access-panel', this);
            });
            
            document.getElementById('toggle-errors-btn').addEventListener('click', function() {
                togglePanel('error-tracking-panel', this);
            });
            
            document.getElementById('toggle-components-btn').addEventListener('click', function() {
                togglePanel('component-status-panel', this);
            });
            
            // Initialize charts
            initializeCharts();
        });
        
        // Fetch dashboard data from API
        async function fetchDashboardData() {
            try {
                // Update system info
                const systemInfoResponse = await fetch(`${config.apiEndpoint}/system_info`);
                if (systemInfoResponse.ok) {
                    const systemInfo = await systemInfoResponse.json();
                    updateSystemInfo(systemInfo.data);
                }
                
                // Update dashboard panels
                const dashboardResponse = await fetch(`${config.apiEndpoint}/dashboard`);
                if (dashboardResponse.ok) {
                    const dashboardData = await dashboardResponse.json();
                    updateDashboardPanels(dashboardData.data);
                }
                
                // Update last fetch time
                config.lastUpdate = new Date();
                document.getElementById('last-update-time').innerText = config.lastUpdate.toLocaleTimeString();
            } catch (error) {
                console.error('Error fetching dashboard data:', error);
                updateSystemStatus('error', 'Connection error');
            }
        }
        
        // Update system status info
        function updateSystemInfo(data) {
            if (!data) return;
            
            // Update system status indicator
            updateSystemStatus(data.friday.status, 'System running');
            
            // Update component status
            config.componentStatus = data.friday.component_status;
            updateComponentList();
        }
        
        // Update all dashboard panels
        function updateDashboardPanels(data) {
            if (!data || !data.panels) return;
            
            // Update system metrics panel
            if (data.panels.system_metrics) {
                updateSystemMetricsPanel(data.panels.system_metrics);
            }
            
            // Update memory access panel
            if (data.panels.memory_access) {
                updateMemoryAccessPanel(data.panels.memory_access);
            }
            
            // Update error tracking panel
            if (data.panels.error_tracker) {
                updateErrorTrackingPanel(data.panels.error_tracker);
            }
        }
        
        // Update system status indicator
        function updateSystemStatus(status, message) {
            const indicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('status-text');
            
            // Remove all status classes
            indicator.className = 'status-indicator';
            
            // Add appropriate class
            switch (status) {
                case 'running':
                    indicator.classList.add('status-running');
                    break;
                case 'warning':
                    indicator.classList.add('status-warning');
                    break;
                case 'error':
                    indicator.classList.add('status-error');
                    break;
                case 'critical':
                    indicator.classList.add('status-critical');
                    break;
                default:
                    indicator.classList.add('status-unknown');
            }
            
            // Update status text
            statusText.innerText = message || status;
        }
        
        // Update component status list
        function updateComponentList() {
            const componentList = document.getElementById('component-list');
            componentList.innerHTML = '';
            
            for (const [componentId, status] of Object.entries(config.componentStatus)) {
                const componentItem = document.createElement('div');
                componentItem.className = 'log-entry';
                
                // Add status indicator class based on status
                if (status.status === 'error' || status.status === 'critical') {
                    componentItem.classList.add('log-error');
                } else if (status.status === 'warning' || status.status === 'stalled') {
                    componentItem.classList.add('log-warning');
                }
                
                // Create component content
                const statusIndicator = document.createElement('span');
                statusIndicator.className = `status-indicator status-${status.status || 'unknown'}`;
                
                const componentName = document.createElement('strong');
                componentName.innerText = componentId;
                
                const componentStatus = document.createElement('span');
                componentStatus.innerText = `: ${status.status || 'unknown'}`;
                
                componentItem.appendChild(statusIndicator);
                componentItem.appendChild(componentName);
                componentItem.appendChild(componentStatus);
                
                // Add error message if present
                if (status.error) {
                    const errorMessage = document.createElement('div');
                    errorMessage.className = 'log-message';
                    errorMessage.innerText = status.error;
                    componentItem.appendChild(errorMessage);
                }
                
                // Add control buttons
                const controlsDiv = document.createElement('div');
                controlsDiv.style.marginTop = '0.5rem';
                
                const restartBtn = document.createElement('button');
                restartBtn.innerText = 'Restart';
                restartBtn.style.fontSize = '0.8rem';
                restartBtn.style.padding = '0.25rem 0.5rem';
                restartBtn.addEventListener('click', () => restartComponent(componentId));
                
                const diagnosticsBtn = document.createElement('button');
                diagnosticsBtn.innerText = 'Diagnostics';
                diagnosticsBtn.style.fontSize = '0.8rem';
                diagnosticsBtn.style.padding = '0.25rem 0.5rem';
                diagnosticsBtn.style.marginLeft = '0.5rem';
                diagnosticsBtn.addEventListener('click', () => runComponentDiagnostics(componentId));
                
                controlsDiv.appendChild(restartBtn);
                controlsDiv.appendChild(diagnosticsBtn);
                componentItem.appendChild(controlsDiv);
                
                componentList.appendChild(componentItem);
            }
        }
        
        // Update system metrics panel
        function updateSystemMetricsPanel(data) {
            if (!data) return;
            
            // Update status indicator
            updatePanelStatus('system-metrics-status', data.status || 'unknown');
            
            // Update metric values
            if (data.metrics && data.metrics.current) {
                const current = data.metrics.current;
                
                // Update CPU usage
                if (current.cpu) {
                    document.getElementById('cpu-usage').innerText = `${Math.round(current.cpu.total_percent)}%`;
                }
                
                // Update memory usage
                if (current.memory) {
                    document.getElementById('memory-usage').innerText = `${Math.round(current.memory.total_percent)}%`;
                    document.getElementById('process-memory').innerText = `${Math.round(current.memory.process_mb)} MB`;
                }
                
                // Update disk usage
                if (current.disk) {
                    document.getElementById('disk-usage').innerText = `${Math.round(current.disk.percent)}%`;
                }
            }
            
            // Update charts
            if (data.metrics && data.metrics.history) {
                updateMetricsCharts(data.metrics.history);
            }
        }
        
        // Update memory access panel
        function updateMemoryAccessPanel(data) {
            if (!data) return;
            
            // Update status indicator
            updatePanelStatus('memory-access-status', data.status || 'unknown');
            
            // Update memory tier counts
            if (data.stats) {
                document.getElementById('short-term-count').innerText = data.stats.short_term_count || '-';
                document.getElementById('mid-term-count').innerText = data.stats.mid_term_count || '-';
                document.getElementById('long-term-count').innerText = data.stats.long_term_count || '-';
            }
            
            // Update access logs
            const logsContainer = document.getElementById('memory-access-logs');
            logsContainer.innerHTML = '';
            
            if (data.recent_access_logs && data.recent_access_logs.length > 0) {
                data.recent_access_logs.forEach(log => {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'log-entry';
                    
                    if (!log.success) {
                        logEntry.classList.add('log-error');
                    }
                    
                    // Format timestamp
                    const timestamp = new Date(log.timestamp);
                    const timeElement = document.createElement('div');
                    timeElement.className = 'log-time';
                    timeElement.innerText = `${timestamp.toLocaleTimeString()} - ${log.operation} on ${log.memory_tier} by ${log.agent}`;
                    
                    // Message
                    const messageElement = document.createElement('div');
                    messageElement.className = 'log-message';
                    
                    if (log.success) {
                        messageElement.innerText = `Key: ${log.key}`;
                    } else {
                        messageElement.innerText = `Error: ${log.error || 'Unknown error'} (Key: ${log.key})`;
                    }
                    
                    logEntry.appendChild(timeElement);
                    logEntry.appendChild(messageElement);
                    logsContainer.appendChild(logEntry);
                });
            } else {
                logsContainer.innerHTML = '<div class="log-entry">No recent memory operations</div>';
            }
            
            // Update error logs
            const errorLogsContainer = document.getElementById('memory-error-logs');
            errorLogsContainer.innerHTML = '';
            
            if (data.recent_error_logs && data.recent_error_logs.length > 0) {
                data.recent_error_logs.forEach(log => {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'log-entry log-error';
                    
                    // Format timestamp
                    const timestamp = new Date(log.timestamp);
                    const timeElement = document.createElement('div');
                    timeElement.className = 'log-time';
                    timeElement.innerText = `${timestamp.toLocaleTimeString()} - ${log.operation} on ${log.memory_tier}`;
                    
                    // Message
                    const messageElement = document.createElement('div');
                    messageElement.className = 'log-message';
                    messageElement.innerText = log.error || 'Unknown error';
                    
                    logEntry.appendChild(timeElement);
                    logEntry.appendChild(messageElement);
                    errorLogsContainer.appendChild(logEntry);
                });
            } else {
                errorLogsContainer.innerHTML = '<div class="log-entry">No memory errors</div>';
            }
        }
        
        // Update error tracking panel
        function updateErrorTrackingPanel(data) {
            if (!data) return;
            
            // Update status indicator
            updatePanelStatus('error-tracking-status', data.status || 'unknown');
            
            // Update error counts
            if (data.error_counts) {
                document.getElementById('critical-count').innerText = data.error_counts.critical || 0;
                document.getElementById('error-count').innerText = data.error_counts.error || 0;
                document.getElementById('warning-count').innerText = data.error_counts.warning || 0;
            }
            
            // Update log file count
            if (data.monitored_logs) {
                document.getElementById('log-file-count').innerText = data.monitored_logs.length || 0;
            }
            
            // Update error logs
            const errorLogsContainer = document.getElementById('error-logs');
            errorLogsContainer.innerHTML = '';
            
            if (data.recent_errors && data.recent_errors.length > 0) {
                data.recent_errors.forEach(error => {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'log-entry';
                    
                    // Add severity class
                    if (error.severity === 'critical') {
                        logEntry.classList.add('log-critical');
                    } else if (error.severity === 'error') {
                        logEntry.classList.add('log-error');
                    } else if (error.severity === 'warning') {
                        logEntry.classList.add('log-warning');
                    }
                    
                    // Format timestamp
                    const timestamp = new Date(error.timestamp);
                    const timeElement = document.createElement('div');
                    timeElement.className = 'log-time';
                    timeElement.innerText = `${timestamp.toLocaleTimeString()} - ${error.component} (${error.log_file})`;
                    
                    // Message
                    const messageElement = document.createElement('div');
                    messageElement.className = 'log-message';
                    messageElement.innerText = error.message || 'Unknown error';
                    
                    logEntry.appendChild(timeElement);
                    logEntry.appendChild(messageElement);
                    errorLogsContainer.appendChild(logEntry);
                });
            } else {
                errorLogsContainer.innerHTML = '<div class="log-entry">No recent errors</div>';
            }
        }
        
        // Update panel status indicator
        function updatePanelStatus(elementId, status) {
            const indicator = document.getElementById(elementId);
            if (!indicator) return;
            
            // Remove all status classes
            indicator.className = 'status-indicator';
            
            // Add appropriate class
            switch (status) {
                case 'running':
                    indicator.classList.add('status-running');
                    break;
                case 'warning':
                    indicator.classList.add('status-warning');
                    break;
                case 'error':
                    indicator.classList.add('status-error');
                    break;
                case 'critical':
                    indicator.classList.add('status-critical');
                    break;
                default:
                    indicator.classList.add('status-unknown');
            }
        }
        
        // Initialize charts
        function initializeCharts() {
            // CPU usage chart
            const cpuCtx = document.createElement('canvas');
            document.getElementById('cpu-chart').appendChild(cpuCtx);
            
            config.charts.cpu = new Chart(cpuCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU Usage (%)',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                color: '#e0e0e0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        x: {
                            ticks: {
                                color: '#e0e0e0',
                                maxRotation: 0
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#e0e0e0'
                            }
                        }
                    }
                }
            });
            
            // Memory usage chart
            const memCtx = document.createElement('canvas');
            document.getElementById('memory-chart').appendChild(memCtx);
            
            config.charts.memory = new Chart(memCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Memory Usage (%)',
                        data: [],
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true
                    }, {
                        label: 'Process Memory (MB)',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                color: '#e0e0e0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y1: {
                            beginAtZero: true,
                            position: 'right',
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#e0e0e0'
                            }
                        },
                        x: {
                            ticks: {
                                color: '#e0e0e0',
                                maxRotation: 0
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#e0e0e0'
                            }
                        }
                    }
                }
            });
        }
        
        // Update charts with new data
        function updateMetricsCharts(history) {
            // Update CPU chart
            if (history.cpu && history.cpu.length > 0) {
                const cpuData = history.cpu.map(item => item.total_percent);
                const timestamps = history.cpu.map(item => {
                    const date = new Date(item.timestamp);
                    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                });
                
                config.charts.cpu.data.labels = timestamps;
                config.charts.cpu.data.datasets[0].data = cpuData;
                config.charts.cpu.update();
            }
            
            // Update Memory chart
            if (history.memory && history.memory.length > 0) {
                const memData = history.memory.map(item => item.total_percent);
                const processData = history.memory.map(item => item.process_mb);
                const timestamps = history.memory.map(item => {
                    const date = new Date(item.timestamp);
                    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                });
                
                config.charts.memory.data.labels = timestamps;
                config.charts.memory.data.datasets[0].data = memData;
                config.charts.memory.data.datasets[1].data = processData;
                config.charts.memory.update();
            }
        }
        
        // Toggle panel visibility
        function togglePanel(panelId, buttonElement) {
            const panel = document.getElementById(panelId);
            const content = panel.querySelector('.panel-content');
            
            if (content.style.display === 'none') {
                content.style.display = 'block';
                buttonElement.innerText = 'Collapse';
            } else {
                content.style.display = 'none';
                buttonElement.innerText = 'Expand';
            }
        }
        
        // Run system diagnostics
        async function runDiagnostics() {
            try {
                const response = await fetch(`${config.apiEndpoint}/dashboard/command`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        command: 'run_diagnostics'
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`Diagnostics complete. Status: ${result.data.status}\n\nIssues: ${result.data.issues ? result.data.issues.join('\n') : 'None'}\n\nWarnings: ${result.data.warnings ? result.data.warnings.join('\n') : 'None'}`);
                    
                    // Refresh dashboard data
                    fetchDashboardData();
                } else {
                    alert('Error running diagnostics');
                }
            } catch (error) {
                console.error('Error running diagnostics:', error);
                alert('Error running diagnostics: ' + error.message);
            }
        }
        
        // Run component-specific diagnostics
        async function runComponentDiagnostics(componentId) {
            try {
                const response = await fetch(`${config.apiEndpoint}/dashboard/command`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        command: 'run_diagnostics',
                        params: {
                            component_id: componentId
                        }
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`Diagnostics for ${componentId} complete. Status: ${result.data.status}\n\nIssues: ${result.data.issues ? result.data.issues.join('\n') : 'None'}\n\nWarnings: ${result.data.warnings ? result.data.warnings.join('\n') : 'None'}`);
                    
                    // Refresh dashboard data
                    fetchDashboardData();
                } else {
                    alert('Error running component diagnostics');
                }
            } catch (error) {
                console.error('Error running component diagnostics:', error);
                alert('Error running component diagnostics: ' + error.message);
            }
        }
        
        // Restart a component
        async function restartComponent(componentId) {
            if (!confirm(`Are you sure you want to restart the ${componentId} component?`)) {
                return;
            }
            
            try {
                const response = await fetch(`${config.apiEndpoint}/dashboard/command`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        command: 'restart_component',
                        params: {
                            component_id: componentId
                        }
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`Component ${componentId} restart: ${result.data.success ? 'Success' : 'Failed'}\n${result.data.message || ''}`);
                    
                    // Refresh dashboard data
                    fetchDashboardData();
                } else {
                    alert('Error restarting component');
                }
            } catch (error) {
                console.error('Error restarting component:', error);
                alert('Error restarting component: ' + error.message);
            }
        }
        
        // Clear error logs
        async function clearErrors() {
            if (!confirm('Are you sure you want to clear all error logs?')) {
                return;
            }
            
            try {
                const response = await fetch(`${config.apiEndpoint}/dashboard/command`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        command: 'clear_errors'
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert('Error logs cleared successfully');
                    
                    // Refresh dashboard data
                    fetchDashboardData();
                } else {
                    alert('Error clearing error logs');
                }
            } catch (error) {
                console.error('Error clearing error logs:', error);
                alert('Error clearing error logs: ' + error.message);
            }
        }
    </script>
</body>
</html>
"""