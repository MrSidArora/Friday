import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebSocket Test")

async def test_connection():
    try:
        logger.info("Connecting to WebSocket server...")
        async with websockets.connect("ws://localhost:8765") as websocket:
            logger.info("Connected to WebSocket server")
            
            # Send a test message
            test_message = {
                "type": "user_message",
                "text": "Hello from test script"
            }
            logger.info(f"Sending message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            logger.info("Waiting for response...")
            response = await websocket.recv()
            logger.info(f"Received response: {response}")
            
            # Send a status check
            status_check = {
                "type": "status_check"
            }
            logger.info(f"Sending status check: {status_check}")
            await websocket.send(json.dumps(status_check))
            
            # Wait for response
            logger.info("Waiting for status response...")
            status_response = await websocket.recv()
            logger.info(f"Received status response: {status_response}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_connection())