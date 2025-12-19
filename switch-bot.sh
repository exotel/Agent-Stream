#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# Exotel Voice Bot - Bot Switcher Script
# ═══════════════════════════════════════════════════════════════════════════════
# Usage: ./switch-bot.sh [simple|s2s|gemini|gemini-live|elevenlabs|status|stop]
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to stop all bots
stop_all_bots() {
    echo -e "${YELLOW}🛑 Stopping all running bots...${NC}"
    pkill -f "simple-conversation-bot" 2>/dev/null || true
    pkill -f "speech-to-speech-bot" 2>/dev/null || true
    pkill -f "gemini-speech-to-speech-bot" 2>/dev/null || true
    pkill -f "gemini-live-bridge" 2>/dev/null || true
    pkill -f "elevenlabs-bridge" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✅ All bots stopped${NC}"
}

# Function to start a bot
start_bot() {
    local bot_name=$1
    local bot_script=$2
    local log_file=$3
    
    echo -e "${BLUE}🚀 Starting ${bot_name}...${NC}"
    npm run $bot_script > $log_file 2>&1 &
    local pid=$!
    sleep 3
    
    # Check if bot started successfully
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${bot_name} started successfully (PID: $pid)${NC}"
        echo -e "${CYAN}📋 Log file: $log_file${NC}"
        echo -e "${CYAN}📋 Monitor:  tail -f $log_file${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to start ${bot_name}${NC}"
        echo -e "${YELLOW}Check logs: cat $log_file${NC}"
        return 1
    fi
}

# Function to show current bot status
show_status() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Current Running Bot:${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    local found=false
    
    if pgrep -f "simple-conversation-bot" > /dev/null; then
        echo -e "${GREEN}✓ Simple Conversation Bot (GPT-4)${NC}"
        echo -e "  Monitor: ${YELLOW}tail -f server.log${NC}"
        found=true
    fi
    
    if pgrep -f "speech-to-speech-bot" > /dev/null; then
        echo -e "${GREEN}✓ Speech-to-Speech Bot (GPT-4 + Noise Cancellation)${NC}"
        echo -e "  Monitor: ${YELLOW}tail -f s2s-server.log${NC}"
        found=true
    fi
    
    if pgrep -f "gemini-speech-to-speech-bot" > /dev/null; then
        echo -e "${GREEN}✓ Gemini Bot (Gemini 2.0 Flash + OpenAI TTS)${NC}"
        echo -e "  Monitor: ${YELLOW}tail -f gemini-server.log${NC}"
        found=true
    fi
    
    if pgrep -f "gemini-live-bridge" > /dev/null; then
        echo -e "${GREEN}✓ Gemini Live Bridge (Native Audio)${NC}"
        echo -e "  Monitor: ${YELLOW}tail -f gemini-live-server.log${NC}"
        found=true
    fi
    
    if pgrep -f "elevenlabs-bridge" > /dev/null; then
        echo -e "${GREEN}✓ ElevenLabs Bridge Bot${NC}"
        echo -e "  Monitor: ${YELLOW}tail -f elevenlabs-server.log${NC}"
        found=true
    fi
    
    if [ "$found" = false ]; then
        echo -e "${RED}✗ No bot is running${NC}"
    fi
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to show help
show_help() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🤖 Exotel Voice Bot - Bot Switcher${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Usage: ./switch-bot.sh [command]"
    echo ""
    echo "Commands:"
    echo -e "  ${GREEN}simple${NC}       Switch to Simple Conversation Bot (GPT-4)"
    echo -e "  ${GREEN}s2s${NC}          Switch to Speech-to-Speech Bot (+ Noise Cancellation)"
    echo -e "  ${GREEN}gemini${NC}       Switch to Gemini Bot (Gemini + OpenAI TTS)"
    echo -e "  ${GREEN}gemini-live${NC}  Switch to Gemini Live Bridge (Native Audio) ⭐"
    echo -e "  ${GREEN}elevenlabs${NC}   Switch to ElevenLabs Bridge Bot ⭐"
    echo -e "  ${GREEN}status${NC}       Show currently running bot"
    echo -e "  ${GREEN}stop${NC}         Stop all bots"
    echo ""
    echo "Examples:"
    echo -e "  ${YELLOW}./switch-bot.sh simple${NC}   # Start simple bot"
    echo -e "  ${YELLOW}./switch-bot.sh gemini${NC}   # Switch to Gemini"
    echo -e "  ${YELLOW}./switch-bot.sh status${NC}   # Check status"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Main logic
case "$1" in
    simple)
        stop_all_bots
        start_bot "Simple Conversation Bot" "chat-bot" "server.log"
        show_status
        ;;
    s2s)
        stop_all_bots
        start_bot "Speech-to-Speech Bot" "s2s-bot" "s2s-server.log"
        show_status
        ;;
    gemini)
        stop_all_bots
        start_bot "Gemini Bot" "gemini-bot" "gemini-server.log"
        show_status
        ;;
    gemini-live)
        stop_all_bots
        start_bot "Gemini Live Bridge" "gemini-live" "gemini-live-server.log"
        show_status
        ;;
    elevenlabs)
        stop_all_bots
        start_bot "ElevenLabs Bridge" "elevenlabs-bot" "elevenlabs-server.log"
        show_status
        ;;
    status)
        show_status
        ;;
    stop)
        stop_all_bots
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        show_status
        exit 1
        ;;
esac

echo -e "${GREEN}Health Check:${NC} curl http://localhost:5001/health"
echo ""
