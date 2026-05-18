import asyncio
import websockets
import json

async def test_ws():
    uri = "wss://exotel-bridge-s66pqrbxkq-uc.a.run.app/media"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connection successful!")
            
            # Send a mock 'connected' event like Exotel would
            connect_msg = {
                "event": "connected",
                "protocol": "Call",
                "version": "1.0.0"
            }
            await websocket.send(json.dumps(connect_msg))
            print("Sent 'connected' event.")
            
            # Wait for a brief moment to see if it stays open
            try:
                # We expect it to stay open waiting for 'start' event
                # We'll send a 'start' event next
                start_msg = {
                    "event": "start",
                    "stream_sid": "test_stream_123",
                    "start": {
                        "call_sid": "test_call_123",
                        "account_sid": "test_account_123",
                        "media_format": {
                            "encoding": "audio/x-l16",
                            "sample_rate": 8000,
                            "channels": 1
                        }
                    }
                }
                await websocket.send(json.dumps(start_msg))
                print("Sent 'start' event.")
                
                print("WebSocket is operational. Closing connection.")
            except Exception as e:
                print(f"Error during message exchange: {e}")
                
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())

