#!/usr/bin/env python3
"""
Enhanced OpenAI Realtime Sales Bot Test Client
Tests multi-sample rate support, variable chunk sizes, and enhanced Exotel integration

Usage:
    python test_enhanced_bot.py --sample-rate 16000
    python test_enhanced_bot.py --sample-rate 24000
    python test_enhanced_bot.py --interactive
"""

import asyncio
import websockets
import json
import base64
import time
import argparse
import logging
import struct
import random
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedBotTester:
    """Test client for Enhanced OpenAI Realtime Sales Bot"""
    
    def __init__(self, server_url: str = "ws://localhost:5000", sample_rate: int = 8000):
        self.server_url = server_url
        self.sample_rate = sample_rate
        self.stream_id = f"test_stream_{int(time.time())}"
        
        # Enhance URL with sample rate parameter
        if "?" in server_url:
            self.test_url = f"{server_url}&sample-rate={sample_rate}"
        else:
            self.test_url = f"{server_url}?sample-rate={sample_rate}"
        
        logger.info(f"🧪 Enhanced Bot Tester initialized")
        logger.info(f"🎵 Target Sample Rate: {sample_rate}Hz")
        logger.info(f"🔗 Test URL: {self.test_url}")

    def generate_test_audio(self, duration_ms: int = 1000, frequency: int = 440) -> bytes:
        """Generate test audio at the configured sample rate"""
        samples = int(self.sample_rate * duration_ms / 1000)
        amplitude = 8000  # Moderate volume
        
        audio_data = []
        for i in range(samples):
            t = i / self.sample_rate
            sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
            sample = max(-32767, min(32767, sample))
            audio_data.append(sample)
        
        return struct.pack(f'<{len(audio_data)}h', *audio_data)

    def generate_variable_chunks(self, total_audio: bytes, min_chunk_ms: int = 20, max_chunk_ms: int = 200) -> list:
        """Generate variable-sized audio chunks to test enhanced chunk processing"""
        chunks = []
        bytes_per_ms = (self.sample_rate * 2) // 1000  # 16-bit PCM
        
        min_chunk_bytes = min_chunk_ms * bytes_per_ms
        max_chunk_bytes = max_chunk_ms * bytes_per_ms
        
        offset = 0
        while offset < len(total_audio):
            # Random chunk size between min and max
            chunk_size = random.randint(min_chunk_bytes, max_chunk_bytes)
            chunk_size = min(chunk_size, len(total_audio) - offset)
            
            chunk = total_audio[offset:offset + chunk_size]
            chunks.append(chunk)
            offset += chunk_size
            
        return chunks

    async def test_connection_and_sample_rate(self):
        """Test basic connection and sample rate detection"""
        logger.info("🔍 Testing enhanced connection and sample rate detection...")
        
        try:
            async with websockets.connect(self.test_url) as websocket:
                logger.info(f"✅ Connected to {self.test_url}")
                
                # Send connected event
                connected_msg = {
                    "event": "connected",
                    "protocol": "Call",
                    "version": "1.0.0"
                }
                await websocket.send(json.dumps(connected_msg))
                logger.info("📤 Sent connected event")
                
                # Send start event with media format
                start_msg = {
                    "event": "start",
                    "start": {
                        "streamSid": self.stream_id,
                        "accountSid": "TEST123",
                        "callSid": "TEST456"
                    },
                    "streamSid": self.stream_id,
                    "mediaFormat": {
                        "encoding": "mulaw",
                        "sampleRate": self.sample_rate,
                        "channels": 1
                    }
                }
                await websocket.send(json.dumps(start_msg))
                logger.info(f"📤 Sent start event with {self.sample_rate}Hz sample rate")
                
                # Wait for responses
                await asyncio.sleep(2)
                
                logger.info("✅ Basic connection test passed")
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
        
        return True

    async def test_variable_chunk_processing(self):
        """Test enhanced variable chunk size processing"""
        logger.info("🔄 Testing enhanced variable chunk processing...")
        
        try:
            async with websockets.connect(self.test_url) as websocket:
                # Initial setup
                await self._send_setup_messages(websocket)
                
                # Generate test audio and variable chunks
                test_audio = self.generate_test_audio(duration_ms=3000, frequency=523)  # C5 note
                variable_chunks = self.generate_variable_chunks(test_audio)
                
                logger.info(f"📦 Generated {len(variable_chunks)} variable-sized chunks")
                
                # Send variable chunks with different sizes
                for i, chunk in enumerate(variable_chunks):
                    chunk_b64 = base64.b64encode(chunk).decode()
                    
                    media_msg = {
                        "event": "media",
                        "streamSid": self.stream_id,
                        "media": {
                            "timestamp": str(int(time.time() * 1000)),
                            "payload": chunk_b64
                        }
                    }
                    
                    await websocket.send(json.dumps(media_msg))
                    
                    chunk_ms = (len(chunk) * 1000) // (self.sample_rate * 2)
                    logger.info(f"📤 Sent variable chunk {i+1}: {len(chunk)} bytes ({chunk_ms}ms)")
                    
                    # Small delay between chunks
                    await asyncio.sleep(0.1)
                
                # Wait for processing
                await asyncio.sleep(3)
                
                logger.info("✅ Variable chunk processing test completed")
                
        except Exception as e:
            logger.error(f"❌ Variable chunk test failed: {e}")
            return False
        
        return True

    async def test_enhanced_mark_clear_events(self):
        """Test enhanced mark and clear event handling"""
        logger.info("✨ Testing enhanced mark and clear event handling...")
        
        try:
            async with websockets.connect(self.test_url) as websocket:
                await self._send_setup_messages(websocket)
                
                # Send some audio first
                test_audio = self.generate_test_audio(duration_ms=2000, frequency=440)
                await self._send_audio_chunk(websocket, test_audio)
                
                # Test enhanced mark events
                enhanced_marks = [
                    "speech_boundary",
                    "audio_complete", 
                    "response_start"
                ]
                
                for mark_name in enhanced_marks:
                    mark_msg = {
                        "event": "mark",
                        "streamSid": self.stream_id,
                        "mark": {
                            "name": mark_name,
                            "timestamp": str(int(time.time() * 1000))
                        }
                    }
                    
                    await websocket.send(json.dumps(mark_msg))
                    logger.info(f"📍 Sent enhanced mark event: {mark_name}")
                    await asyncio.sleep(0.5)
                
                # Test enhanced clear event
                clear_msg = {
                    "event": "clear",
                    "streamSid": self.stream_id
                }
                
                await websocket.send(json.dumps(clear_msg))
                logger.info("🧹 Sent enhanced clear event")
                
                await asyncio.sleep(2)
                logger.info("✅ Enhanced mark/clear events test completed")
                
        except Exception as e:
            logger.error(f"❌ Enhanced events test failed: {e}")
            return False
        
        return True

    async def test_sample_rate_comparison(self):
        """Test multiple sample rates to compare performance"""
        logger.info("🎵 Testing multi-sample rate comparison...")
        
        test_rates = [8000, 16000, 24000]
        results = {}
        
        for rate in test_rates:
            if rate not in [8000, 16000, 24000]:
                continue
                
            logger.info(f"🔄 Testing {rate}Hz...")
            
            # Create URL with specific sample rate
            test_url = f"ws://localhost:5000?sample-rate={rate}"
            
            try:
                start_time = time.time()
                
                async with websockets.connect(test_url) as websocket:
                    temp_stream_id = f"rate_test_{rate}_{int(time.time())}"
                    
                    # Setup
                    await self._send_setup_messages(websocket, temp_stream_id)
                    
                    # Generate and send audio
                    test_audio = self.generate_test_audio_for_rate(rate, duration_ms=1000)
                    await self._send_audio_chunk(websocket, test_audio, temp_stream_id)
                    
                    # Wait for processing
                    await asyncio.sleep(1)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                results[rate] = {
                    "success": True,
                    "processing_time": processing_time,
                    "audio_size": len(test_audio)
                }
                
                logger.info(f"✅ {rate}Hz test completed in {processing_time:.2f}s")
                
            except Exception as e:
                results[rate] = {
                    "success": False,
                    "error": str(e)
                }
                logger.error(f"❌ {rate}Hz test failed: {e}")
        
        # Print comparison results
        logger.info("📊 Sample Rate Comparison Results:")
        for rate, result in results.items():
            if result["success"]:
                logger.info(f"   {rate}Hz: ✅ {result['processing_time']:.2f}s, {result['audio_size']} bytes")
            else:
                logger.error(f"   {rate}Hz: ❌ {result['error']}")
        
        return results

    def generate_test_audio_for_rate(self, sample_rate: int, duration_ms: int = 1000) -> bytes:
        """Generate test audio for specific sample rate"""
        samples = int(sample_rate * duration_ms / 1000)
        amplitude = 8000
        frequency = 440  # A4 note
        
        audio_data = []
        for i in range(samples):
            t = i / sample_rate
            sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
            sample = max(-32767, min(32767, sample))
            audio_data.append(sample)
        
        return struct.pack(f'<{len(audio_data)}h', *audio_data)

    async def _send_setup_messages(self, websocket, stream_id: str = None):
        """Send initial setup messages"""
        if stream_id is None:
            stream_id = self.stream_id
            
        # Connected
        connected_msg = {
            "event": "connected",
            "protocol": "Call",
            "version": "1.0.0"
        }
        await websocket.send(json.dumps(connected_msg))
        
        # Start
        start_msg = {
            "event": "start",
            "start": {
                "streamSid": stream_id,
                "accountSid": "TEST123",
                "callSid": "TEST456"
            },
            "streamSid": stream_id,
            "mediaFormat": {
                "encoding": "mulaw",
                "sampleRate": self.sample_rate,
                "channels": 1
            }
        }
        await websocket.send(json.dumps(start_msg))
        
        # Small delay for setup
        await asyncio.sleep(0.5)

    async def _send_audio_chunk(self, websocket, audio_data: bytes, stream_id: str = None):
        """Send audio chunk"""
        if stream_id is None:
            stream_id = self.stream_id
            
        audio_b64 = base64.b64encode(audio_data).decode()
        
        media_msg = {
            "event": "media",
            "streamSid": stream_id,
            "media": {
                "timestamp": str(int(time.time() * 1000)),
                "payload": audio_b64
            }
        }
        
        await websocket.send(json.dumps(media_msg))

    async def interactive_test_session(self):
        """Interactive test session with user input"""
        logger.info("🎮 Starting interactive test session...")
        logger.info("Commands: connect, audio, mark, clear, variable, rates, quit")
        
        async with websockets.connect(self.test_url) as websocket:
            await self._send_setup_messages(websocket)
            
            while True:
                command = input("\n> Enter command (help for options): ").strip().lower()
                
                if command == "help":
                    print("""
Available commands:
  connect  - Test connection and sample rate detection
  audio    - Send test audio chunk
  mark     - Send enhanced mark event
  clear    - Send enhanced clear event  
  variable - Send variable-sized chunks
  rates    - Compare different sample rates
  quit     - Exit interactive session
                    """)
                
                elif command == "connect":
                    await self.test_connection_and_sample_rate()
                    
                elif command == "audio":
                    test_audio = self.generate_test_audio(duration_ms=2000, frequency=523)
                    await self._send_audio_chunk(websocket, test_audio)
                    logger.info("📤 Sent test audio chunk")
                    
                elif command == "mark":
                    mark_name = input("Enter mark name (speech_boundary/audio_complete/response_start): ").strip()
                    if not mark_name:
                        mark_name = "speech_boundary"
                    
                    mark_msg = {
                        "event": "mark",
                        "streamSid": self.stream_id,
                        "mark": {
                            "name": mark_name,
                            "timestamp": str(int(time.time() * 1000))
                        }
                    }
                    await websocket.send(json.dumps(mark_msg))
                    logger.info(f"📍 Sent mark event: {mark_name}")
                    
                elif command == "clear":
                    clear_msg = {
                        "event": "clear",
                        "streamSid": self.stream_id
                    }
                    await websocket.send(json.dumps(clear_msg))
                    logger.info("🧹 Sent clear event")
                    
                elif command == "variable":
                    await self.test_variable_chunk_processing()
                    
                elif command == "rates":
                    await self.test_sample_rate_comparison()
                    
                elif command == "quit":
                    logger.info("👋 Exiting interactive session")
                    break
                    
                else:
                    logger.warning(f"❓ Unknown command: {command}")

async def run_comprehensive_tests(sample_rate: int):
    """Run comprehensive test suite"""
    tester = EnhancedBotTester(sample_rate=sample_rate)
    
    logger.info(f"🚀 Starting comprehensive enhanced bot tests @ {sample_rate}Hz")
    
    tests = [
        ("Connection & Sample Rate Detection", tester.test_connection_and_sample_rate),
        ("Variable Chunk Processing", tester.test_variable_chunk_processing), 
        ("Enhanced Mark/Clear Events", tester.test_enhanced_mark_clear_events),
        ("Multi-Sample Rate Comparison", tester.test_sample_rate_comparison)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            if result:
                logger.info(f"✅ {test_name} - PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} - FAILED")
        except Exception as e:
            logger.error(f"💥 {test_name} - ERROR: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")

def main():
    parser = argparse.ArgumentParser(description="Enhanced OpenAI Realtime Sales Bot Tester")
    parser.add_argument("--sample-rate", type=int, choices=[8000, 16000, 24000], 
                       default=8000, help="Sample rate to test (default: 8000)")
    parser.add_argument("--server", type=str, default="ws://localhost:5000",
                       help="Server URL (default: ws://localhost:5000)")
    parser.add_argument("--interactive", action="store_true",
                       help="Run interactive test session")
    parser.add_argument("--comprehensive", action="store_true", 
                       help="Run comprehensive test suite")
    
    args = parser.parse_args()
    
    # Import math here to avoid issues
    import math
    globals()['math'] = math
    
    if args.interactive:
        tester = EnhancedBotTester(server_url=args.server, sample_rate=args.sample_rate)
        asyncio.run(tester.interactive_test_session())
    elif args.comprehensive:
        asyncio.run(run_comprehensive_tests(args.sample_rate))
    else:
        # Quick test
        tester = EnhancedBotTester(server_url=args.server, sample_rate=args.sample_rate)
        asyncio.run(tester.test_connection_and_sample_rate())

if __name__ == "__main__":
    main() 