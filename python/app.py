import asyncio
import websockets
import json
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/voice_streaming.log')
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

async def handle_websocket(websocket, path):
    """Handle WebSocket connection with path support."""
    connection_id = f"conn_{int(datetime.now().timestamp() * 1000)}"
    logger.info(f"New WebSocket connection established: {connection_id} on path: {path}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Received event from {connection_id}: {data['event']}")
                
                # Log call details if it's a connected event
                if data['event'] == 'connected':
                    logger.info(f"Call details for {connection_id}: {json.dumps(data, indent=2)}")
                    with open('logs/calls.log', 'a') as f:
                        f.write(json.dumps({
                            'timestamp': datetime.now().isoformat(),
                            'connection_id': connection_id,
                            'call_data': data
                        }) + '\n')
                
                # Echo back media packets in bidirectional mode
                elif data['event'] == 'media':
                    logger.info(f"Media packet received from {connection_id}: size={len(data['media']['payload'])}")
                    await websocket.send(json.dumps({
                        'event': 'media',
                        'stream_sid': data.get('stream_sid'),
                        'media': data['media']
                    }))
                    logger.info(f"Media packet echoed back to {connection_id}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {connection_id}: {e}")
            except Exception as e:
                logger.error(f"Error processing message from {connection_id}: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed normally: {connection_id}")
    except Exception as e:
        logger.error(f"Error in connection {connection_id}: {str(e)}")
    finally:
        logger.info(f"Connection closed: {connection_id}")

async def main():
    port = 5000
    server = await websockets.serve(
        handle_websocket,
        "0.0.0.0",
        port,
        ping_interval=30,  # Send ping every 30 seconds
        ping_timeout=10    # Wait 10 seconds for pong response
    )
    logger.info(f"WebSocket server running at ws://0.0.0.0:{port}")
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
