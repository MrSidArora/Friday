import asyncio
import json
import websockets
import logging
from datetime import datetime
import threading
import socket

# Add these lines after importing logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger("Friday UI Controller")

# Import necessary Friday components
# Note: These will be adjusted based on your actual imports
try:
    from core.llm_interface import LLMInterface
    from core.memory_system import MemorySystem
    from core.intent_model import IntentModel
    from speech.whisper_client import WhisperClient
    from speech.piper_tts import PiperTTS
except ImportError:
    logging.warning("Running in development mode without core Friday components")
    LLMInterface = None
    MemorySystem = None
    IntentModel = None
    WhisperClient = None
    PiperTTS = None

class UIController:
    def __init__(self, port=8765, dev_mode=False):
        self.port = port
        self.dev_mode = dev_mode
        self.clients = set()
        self.running = False
        self.server = None

        # Initialize Friday components if not in dev mode
        if not dev_mode and all([LLMInterface, MemorySystem, IntentModel]):
            self.memory_system = MemorySystem()
            self.llm_interface = LLMInterface()
            self.intent_model = IntentModel(self.memory_system, self.llm_interface)
            self.speech_recognition = WhisperClient() if WhisperClient else None
            self.text_to_speech = PiperTTS() if PiperTTS else None
        else:
            self.memory_system = None
            self.llm_interface = None
            self.intent_model = None
            self.speech_recognition = None
            self.text_to_speech = None
            logging.info("Running in development mode with mock Friday components")

    async def handler(self, websocket, path):
        """Handle WebSocket connections from the UI"""
        client_id = id(websocket)
        logger.info(f"Client connected: {client_id}")
        self.clients.add(websocket)
        try:
            async for message in websocket:
                logger.info(f"Received message from client {client_id}: {message[:100]}...")
                try:
                    data = json.loads(message)
                    await self.process_message(websocket, data)
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse message: {message}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "error": "Invalid JSON format"
                    }))
        except websockets.exceptions.ConnectionClosed:
            logging.info("Client disconnected")
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client {client_id} removed from active clients")

    async def process_message(self, websocket, data):
        """Process messages from the UI"""
        msg_type = data.get("type", "")
        logger.info(f"Processing message of type: {msg_type}")
        
        if msg_type == "user_message":
            # Process user message
            logger.info(f"User message: {data.get('text', '')[:100]}...")
            await self.handle_user_message(websocket, data)
        elif msg_type == "status_check":
            # Send status update
            logger.info("Status check request received")
            await self.send_status(websocket)
        elif msg_type == "speech_input":
            # Handle speech input
            logger.info("Speech input request received")
            await self.handle_speech_input(websocket, data)
        else:
            # Unknown message type
            logger.warning(f"Unknown message type: {msg_type}")
            await websocket.send(json.dumps({
                "type": "error",
                "error": f"Unknown message type: {msg_type}"
            }))

    async def handle_user_message(self, websocket, data):
        """Process a user message and generate a response"""
        text = data.get("text", "")
        
        if not text:
            await websocket.send(json.dumps({
                "type": "error",
                "error": "Empty message"
            }))
            return
            
        # Send processing status
        await websocket.send(json.dumps({
            "type": "status_update",
            "processing": True
        }))
        
        try:
            # Process with Friday components if available, otherwise mock
            if self.dev_mode or not all([self.memory_system, self.llm_interface, self.intent_model]):
                # Mock response in development mode
                response_text = f"Echo (dev mode): {text}"
                # Simulate processing delay
                await asyncio.sleep(1)
            else:
                # Real processing with Friday components
                # Store user message in memory
                await self.memory_system.store_interaction({
                    "role": "user",
                    "content": text,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Analyze intent
                intent_analysis = await self.intent_model.analyze_intent(text, None)
                
                # Get response from LLM
                llm_response = await self.llm_interface.ask(text, intent=intent_analysis)
                
                # Store Friday's response in memory
                await self.memory_system.store_interaction({
                    "role": "friday",
                    "content": llm_response["text"],
                    "timestamp": datetime.now().isoformat()
                })
                
                response_text = llm_response["text"]
                
                # Generate speech if TTS is available
                if self.text_to_speech:
                    # Run TTS in background to avoid blocking
                    threading.Thread(
                        target=self.text_to_speech.speak,
                        args=(response_text,),
                        daemon=True
                    ).start()
            
            # Send response back to client
            await websocket.send(json.dumps({
                "type": "friday_response",
                "text": response_text,
                "timestamp": datetime.now().isoformat()
            }))
            
            # Update status (not processing anymore)
            await websocket.send(json.dumps({
                "type": "status_update",
                "processing": False
            }))
            
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            await websocket.send(json.dumps({
                "type": "error",
                "error": f"Error: {str(e)}"
            }))
            
            # Update status
            await websocket.send(json.dumps({
                "type": "status_update",
                "processing": False
            }))

    async def handle_speech_input(self, websocket, data):
        """Process speech input"""
        # This will be implemented when Whisper integration is ready
        await websocket.send(json.dumps({
            "type": "error",
            "error": "Speech input not yet implemented"
        }))

    async def send_status(self, websocket):
        """Send Friday's status to the client"""
        # Check if core components are available
        online = not self.dev_mode and all([self.memory_system, self.llm_interface, self.intent_model])
        
        await websocket.send(json.dumps({
            "type": "status_update",
            "online": online,
            "processing": False
        }))

    def find_available_port(self, start_port=8765, max_attempts=10):
        """Find an available port starting from start_port"""
        for port_offset in range(max_attempts):
            port = start_port + port_offset
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('localhost', port))
                sock.close()
                return port
            except OSError:
                continue
        
        # If we get here, we couldn't find an available port
        raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

    async def start_server(self):
        """Start the WebSocket server"""
        if self.running:
            return
            
        # Find an available port
        try:
            self.port = self.find_available_port(self.port)
            logging.info(f"Using port {self.port} for UI Controller WebSocket server")
        except RuntimeError as e:
            logging.error(f"Failed to find available port: {str(e)}")
            return
            
        self.running = True
        self.server = await websockets.serve(self.handler, "localhost", self.port)
        logging.info(f"UI Controller WebSocket server started on port {self.port}")
        
        # Keep the server running
        await self.server.wait_closed()
    
    def start(self):
        """Start the server in a non-blocking way"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.start_server())
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop the WebSocket server"""
        if not self.running:
            return
            
        self.running = False
        if self.server:
            self.server.close()
        logging.info("UI Controller WebSocket server stopped")

# Helper function to run the controller
def run_ui_controller(port=8765, dev_mode=False):
    controller = UIController(port=port, dev_mode=dev_mode)
    controller.start()
    return controller

# For running directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_ui_controller(dev_mode=True)