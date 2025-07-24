import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def echo(websocket):
    logger.info("Client connected!")
    try:
        async for message in websocket:
            data = json.loads(message)
            logger.info(f"Received: {data['event']}")
            
            # Echo back media packets
            if data['event'] == 'media':
                await websocket.send(message)  # Just echo back the exact same message
                
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        logger.info("Client disconnected")

async def main():
    async with websockets.serve(echo, "0.0.0.0", 5000):
        logger.info("WebSocket server running on ws://0.0.0.0:5000")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main()) 