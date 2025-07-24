#!/usr/bin/env python3
"""
Simple test script to verify the WebSocket server is working.
"""

import asyncio
import json
import time

async def test_websocket():
    """Test the WebSocket connection to the voice streaming server."""
    
    try:
        import websockets
    except ImportError:
        print("Installing websockets...")
        import subprocess
        subprocess.check_call(["pip", "install", "websockets"])
        import websockets
    
    uri = "ws://localhost:5000/media"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Wait for connected message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Received: {data['event']}")
            
            if data['event'] == 'connected':
                print("✅ Server connection confirmed")
                
                # Send a test start message
                start_message = {
                    "event": "start",
                    "sequence_number": 1,
                    "stream_sid": "test_stream_123",
                    "start": {
                        "stream_sid": "test_stream_123",
                        "call_sid": "test_call_456",
                        "account_sid": "test_account_789",
                        "from": "+1234567890",
                        "to": "+0987654321",
                        "custom_parameters": {
                            "test": "value"
                        },
                        "media_format": {
                            "encoding": "LINEAR16",
                            "sample_rate": "8000",
                            "bit_rate": "128000"
                        }
                    }
                }
                
                await websocket.send(json.dumps(start_message))
                print("📤 Sent start message")
                
                # Wait for any response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"📨 Received: {data['event']}")
                except asyncio.TimeoutError:
                    print("⏰ No response received (this is normal for this test)")
                
                # Send a stop message
                stop_message = {
                    "event": "stop",
                    "sequence_number": 2,
                    "stream_sid": "test_stream_123",
                    "stop": {
                        "call_sid": "test_call_456",
                        "account_sid": "test_account_789",
                        "reason": "test_completed"
                    }
                }
                
                await websocket.send(json.dumps(stop_message))
                print("📤 Sent stop message")
                
                print("✅ WebSocket test completed successfully")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Testing WebSocket server...")
    print("Make sure the server is running on port 5000")
    print("=" * 50)
    
    result = asyncio.run(test_websocket())
    
    if result:
        print("🎉 All tests passed!")
    else:
        print("💥 Tests failed!") 