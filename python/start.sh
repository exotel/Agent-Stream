#!/bin/bash

echo "🚀 Starting Exotel Voice Streaming WebSocket Server..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

# Start the server
echo "🎧 Starting WebSocket server on port 5000..."
python3 simple_server.py 