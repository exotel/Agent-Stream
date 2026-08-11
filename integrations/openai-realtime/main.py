#!/usr/bin/env python3
"""
Voice AI Bot - Simple Entry Point
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from core.bot import main as bot_main

def main():
    """Main entry point"""
    print('🚀 Voice AI Bot')
    print('=' * 30)
    
    # Validate configuration
    try:
        Config.validate()
        print('✅ Configuration valid')
        print(f'🏢 Company: {Config.COMPANY_NAME}')
        print(f'🤖 Bot: {Config.SALES_BOT_NAME}')
        print(f'🌐 Server: {Config.SERVER_HOST}:{Config.SERVER_PORT}')
        print(f'📦 Chunk size: {Config.AUDIO_CHUNK_SIZE}ms')
    except ValueError as e:
        print(f'❌ Configuration error: {e}')
        print('💡 Edit .env file with your settings')
        sys.exit(1)
    
    # Start the bot
    try:
        print()
        print('🤖 Starting bot...')
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print()
        print('👋 Bot stopped')
    except Exception as e:
        print()
        print(f'❌ Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
