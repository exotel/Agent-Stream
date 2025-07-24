#!/bin/bash

echo "🚀 Setting up Exotel Voice Streaming WebSocket Server..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start server: python3 simple_server.py"
echo "3. In another terminal, start ngrok: ngrok http 5000"
echo "4. Use the ngrok URL with Exotel"
echo ""
echo "📖 For detailed instructions, see README.md" 