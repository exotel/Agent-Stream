#!/usr/bin/env python3
"""
Test script to verify WebSocket connection to the voice streaming server.
"""

import asyncio
import websockets
import json
import sys

async def test_connection(uri="ws://localhost:5000"):
    """Test WebSocket connection with sample Exotel events."""
    
    try:
        print(f"🔗 Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Test 1: Send connected event
            connected_event = {
                "event": "connected",
                "protocol": "Call",
                "version": "1.0.0"
            }
            
            print("📤 Sending 'connected' event...")
            await websocket.send(json.dumps(connected_event))
            
            # Test 2: Send start event
            start_event = {
                "event": "start",
                "stream_sid": "test_stream_123",
                "media_format": {
                    "encoding": "linear16",
                    "sample_rate": 8000,
                    "channels": 1
                }
            }
            
            print("📤 Sending 'start' event...")
            await websocket.send(json.dumps(start_event))
            
            # Test 3: Send sample media event
            media_event = {
                "event": "media",
                "stream_sid": "test_stream_123",
                "media": {
                    "timestamp": "12345",
                    "payload": "dGVzdCBhdWRpbyBkYXRh"  # base64 encoded "test audio data"
                }
            }
            
            print("📤 Sending sample 'media' event...")
            await websocket.send(json.dumps(media_event))
            
            # Test 4: Wait for echo (if bidirectional)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"📥 Received response: {response}")
                print("✅ Echo functionality working!")
            except asyncio.TimeoutError:
                print("⚠️  No echo received (may be unidirectional mode)")
            
            # Test 5: Send stop event
            stop_event = {
                "event": "stop",
                "stream_sid": "test_stream_123"
            }
            
            print("📤 Sending 'stop' event...")
            await websocket.send(json.dumps(stop_event))
            
            print("🎉 All tests completed successfully!")
            
    except ConnectionRefusedError:
        print("❌ Connection refused. Make sure the server is running on the specified port.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

async def main():
    """Main test function."""
    
    # Default to localhost
    uri = "ws://localhost:5000"
    
    # Check if custom URI provided
    if len(sys.argv) > 1:
        uri = sys.argv[1]
        if not uri.startswith("ws://") and not uri.startswith("wss://"):
            uri = f"ws://{uri}"
    
    print("🧪 Testing Exotel Voice Streaming WebSocket Server")
    print("=" * 50)
    
    success = await test_connection(uri)
    
    if success:
        print("\n✅ Connection test passed!")
        print("🚀 Your server is ready for Exotel integration!")
    else:
        print("\n❌ Connection test failed!")
        print("🔧 Please check:")
        print("   1. Server is running: python3 simple_server.py")
        print("   2. Port is not blocked by firewall")
        print("   3. URI is correct")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}") 