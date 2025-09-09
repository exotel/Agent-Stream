#!/bin/bash
# Enhanced OpenAI Realtime Sales Bot Startup Script
# Supports multi-sample rate (8kHz, 16kHz, 24kHz) and variable chunk processing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Enhanced OpenAI Realtime Sales Bot${NC}"
echo -e "${BLUE}Multi-sample rate support: 8kHz, 16kHz, 24kHz${NC}"
echo -e "${BLUE}Enhanced Exotel integration with variable chunk sizes${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚙️ Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}⬆️ Upgrading pip...${NC}"
pip install --upgrade pip

# Install/upgrade requirements
echo -e "${BLUE}📚 Installing enhanced dependencies...${NC}"
pip install -r requirements.txt

# Check for required environment variables
echo -e "${BLUE}🔐 Checking environment configuration...${NC}"

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY environment variable is not set${NC}"
    echo -e "${YELLOW}💡 Please set your OpenAI API key:${NC}"
    echo "export OPENAI_API_KEY='your-api-key-here'"
    echo ""
    echo -e "${YELLOW}Or create a .env file with:${NC}"
    echo "OPENAI_API_KEY=your-api-key-here"
    exit 1
fi

# Load .env file if it exists
if [ -f ".env" ]; then
    echo -e "${GREEN}📄 Loading .env file...${NC}"
    export $(cat .env | xargs)
fi

# Set default environment variables if not set
export SERVER_HOST=${SERVER_HOST:-"0.0.0.0"}
export SERVER_PORT=${SERVER_PORT:-"5000"}
export OPENAI_MODEL=${OPENAI_MODEL:-"gpt-4o-realtime-preview-2024-12-17"}
export OPENAI_VOICE=${OPENAI_VOICE:-"coral"}

# Enhanced audio configuration
export SAMPLE_RATE=${SAMPLE_RATE:-"8000"}
export MIN_CHUNK_SIZE_MS=${MIN_CHUNK_SIZE_MS:-"20"}
export BUFFER_SIZE_MS=${BUFFER_SIZE_MS:-"160"}
export DYNAMIC_CHUNK_SIZING=${DYNAMIC_CHUNK_SIZING:-"true"}
export AUDIO_ENHANCEMENT_ENABLED=${AUDIO_ENHANCEMENT_ENABLED:-"true"}

# Enhanced features
export EXOTEL_MARK_CLEAR_ENHANCED=${EXOTEL_MARK_CLEAR_ENHANCED:-"true"}
export EXOTEL_VARIABLE_CHUNK_SUPPORT=${EXOTEL_VARIABLE_CHUNK_SUPPORT:-"true"}

echo -e "${GREEN}✅ Environment configured${NC}"
echo -e "🎵 Sample Rate: ${SAMPLE_RATE}Hz"
echo -e "📦 Chunk Size: ${BUFFER_SIZE_MS}ms (min: ${MIN_CHUNK_SIZE_MS}ms)"
echo -e "🤖 OpenAI Model: ${OPENAI_MODEL}"
echo -e "🎭 Voice: ${OPENAI_VOICE}"
echo -e "🌐 Server: ${SERVER_HOST}:${SERVER_PORT}"
echo ""

# Check for existing server
if lsof -i :$SERVER_PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Port $SERVER_PORT is already in use${NC}"
    echo -e "${YELLOW}🔄 Stopping existing server...${NC}"
    pkill -f "openai_realtime_sales_bot.py" || true
    sleep 2
fi

# Start the enhanced server
echo -e "${GREEN}🚀 Starting Enhanced OpenAI Realtime Sales Bot...${NC}"
echo -e "${GREEN}📞 WebSocket endpoints:${NC}"
echo -e "   • ws://${SERVER_HOST}:${SERVER_PORT}/ (default 8kHz)"
echo -e "   • ws://${SERVER_HOST}:${SERVER_PORT}/?sample-rate=8000"
echo -e "   • ws://${SERVER_HOST}:${SERVER_PORT}/?sample-rate=16000"
echo -e "   • ws://${SERVER_HOST}:${SERVER_PORT}/?sample-rate=24000"
echo ""

# Function to handle cleanup
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down enhanced bot...${NC}"
    pkill -f "openai_realtime_sales_bot.py" || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start the server with enhanced features
python3 openai_realtime_sales_bot.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Check if server started successfully
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start server${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Enhanced Sales Bot running!${NC}"
echo -e "${BLUE}🎯 Multi-sample rate support active${NC}"
echo -e "${BLUE}📦 Variable chunk processing enabled${NC}"
echo -e "${BLUE}✨ Enhanced mark/clear events ready${NC}"
echo ""

# Show test commands
echo -e "${YELLOW}🧪 Test the enhanced features:${NC}"
echo "# Basic test (8kHz):"
echo "python3 test_enhanced_bot.py"
echo ""
echo "# Test 16kHz support:"
echo "python3 test_enhanced_bot.py --sample-rate 16000"
echo ""
echo "# Test 24kHz support:"
echo "python3 test_enhanced_bot.py --sample-rate 24000"
echo ""
echo "# Interactive testing:"
echo "python3 test_enhanced_bot.py --interactive"
echo ""
echo "# Comprehensive test suite:"
echo "python3 test_enhanced_bot.py --comprehensive"
echo ""

echo -e "${GREEN}🎯 Ready for enhanced Exotel connections!${NC}"
echo -e "${BLUE}Press Ctrl+C to stop the server${NC}"

# Wait for the server process
wait $SERVER_PID 