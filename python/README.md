# Exotel Voice Streaming WebSocket Server

A simple WebSocket server for testing Exotel's voice streaming functionality. This server can handle both unidirectional and bidirectional audio streaming with real-time logging.

## Features

- ✅ WebSocket server for Exotel voice streaming
- ✅ Support for bidirectional audio (echo functionality)
- ✅ Real-time logging of all events
- ✅ Easy local testing with ngrok
- ✅ Simple setup with minimal dependencies
- ✅ Clear and Mark event handling
- ✅ Audio quality monitoring

## Quick Start

### Prerequisites

- Python 3.8+
- ngrok account (free tier works)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd voice-streaming/python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start the WebSocket Server

```bash
python3 simple_server.py
```

The server will start on `ws://localhost:5000`

### 3. Expose with ngrok

In another terminal:

```bash
# Install ngrok (if not already installed)
# Visit: https://ngrok.com/download

# Add your auth token
ngrok config add-authtoken YOUR_NGROK_TOKEN

# Start tunnel
ngrok http 5000
```

You'll get a URL like: `https://abc123.ngrok-free.app`

### 4. Use with Exotel

Use the ngrok URL as your WebSocket endpoint in Exotel:
- WebSocket URL: `wss://abc123.ngrok-free.app`

## Configuration

### Environment Variables

No sensitive information required! The basic server works out of the box.

Optional (for advanced features):
```bash
# For Google Speech-to-Text (unidirectional mode only)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
```

### Server Options

The simple server runs with these defaults:
- Host: `0.0.0.0` (accessible from outside)
- Port: `5000`
- Mode: Bidirectional (echo)

## File Structure

```
voice-streaming/python/
├── simple_server.py      # Basic WebSocket server (recommended)
├── app.py               # Full-featured server with logging
├── requirements.txt     # Python dependencies
├── logs/               # Log files (auto-created)
└── README.md           # This file
```

## Usage Examples

### Basic Echo Server (Recommended)

```python
# simple_server.py - Just echo back audio
import asyncio
import websockets
import json

async def echo(websocket):
    async for message in websocket:
        data = json.loads(message)
        if data['event'] == 'media':
            await websocket.send(message)  # Echo back
```

### Advanced Server with Logging

Use `app.py` for:
- Detailed logging
- Audio quality metrics
- Event handling (clear, mark)
- Error monitoring

## Testing

### 1. Test WebSocket Connection

```bash
# Install websocket client
pip install websockets

# Test connection
python3 -c "
import asyncio
import websockets
import json

async def test():
    uri = 'ws://localhost:5000'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({'event': 'connected'}))
        response = await ws.recv()
        print(f'Server response: {response}')

asyncio.run(test())
"
```

### 2. Check Logs

```bash
# View real-time logs
tail -f logs/voice_streaming.log
```

## Deployment Options

### Local Development
- Use `simple_server.py` with ngrok
- Perfect for testing and development

### Production
- Use `app.py` with proper logging
- Deploy on cloud (AWS, GCP, Azure)
- Use proper domain instead of ngrok

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   lsof -i :5000
   kill -9 <PID>
   ```

2. **ngrok tunnel limit**
   ```bash
   pkill ngrok
   ngrok http 5000
   ```

3. **WebSocket connection failed**
   - Check if server is running: `lsof -i :5000`
   - Verify ngrok tunnel: `curl https://your-ngrok-url.ngrok-free.app`
   - Check Exotel logs for connection errors

### Logs Location

- Main logs: `logs/voice_streaming.log`
- Error logs: `logs/errors/error.log`
- Event logs: `logs/events/events.log`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Exotel
5. Submit a pull request

## License

MIT License - feel free to use and modify as needed.

## Support

- Check logs for detailed error information
- Ensure WebSocket URL is accessible from Exotel servers
- Verify ngrok tunnel is active and not rate-limited

---

**Note**: This is a sample implementation for testing. For production use, implement proper authentication, error handling, and monitoring.



