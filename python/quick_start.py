#!/usr/bin/env python3
"""
🚀 Quick Start Demo - Enhanced AI Bot Framework
Create different types of bots in seconds!

This script demonstrates how to quickly create and deploy various types of AI bots
for sales, support, service collection, and more using the enhanced framework.
"""

import asyncio
import time
from bot_framework import BotManager

async def quick_start_demo():
    """Quick demonstration of creating different bot types"""
    
    print("🚀 ENHANCED AI BOT FRAMEWORK - QUICK START DEMO")
    print("=" * 60)
    print("Creating different types of bots to show the framework capabilities...")
    print()
    
    # Initialize bot manager
    bot_manager = BotManager()
    
    # Demo bots to create
    demo_bots = [
        {
            "type": "sales",
            "id": "demo-sales",
            "config": {
                "voice": "nova",
                "temperature": 0.8,
                "company_name": "Demo Corp",
                "personality": "enthusiastic"
            },
            "port": 6001,
            "description": "Enthusiastic sales bot for lead conversion"
        },
        {
            "type": "support", 
            "id": "demo-support",
            "config": {
                "voice": "coral",
                "temperature": 0.3,
                "company_name": "Demo Corp", 
                "personality": "empathetic"
            },
            "port": 6002,
            "description": "Empathetic support bot for customer assistance"
        },
        {
            "type": "service_collection",
            "id": "demo-collection",
            "config": {
                "voice": "echo",
                "temperature": 0.2,
                "company_name": "Demo Corp",
                "personality": "professional"
            },
            "port": 6003,
            "description": "Professional collection bot for payment reminders"
        },
        {
            "type": "appointment_booking",
            "id": "demo-booking", 
            "config": {
                "voice": "shimmer",
                "temperature": 0.4,
                "company_name": "Demo Clinic",
                "personality": "direct"
            },
            "port": 6004,
            "description": "Efficient booking bot for appointment scheduling"
        }
    ]
    
    created_bots = []
    
    # Create and start each demo bot
    for bot_info in demo_bots:
        try:
            print(f"🤖 Creating {bot_info['type']} bot: {bot_info['id']}")
            print(f"   {bot_info['description']}")
            
            # Create bot configuration
            config = bot_manager.create_bot(
                bot_type=bot_info["type"],
                bot_id=bot_info["id"],
                config_overrides=bot_info["config"],
                custom_instructions=f"You are a demo {bot_info['type']} bot showcasing the framework capabilities."
            )
            
            # Start the bot
            await bot_manager.start_bot(bot_info["id"], port=bot_info["port"])
            
            created_bots.append(bot_info)
            print(f"   ✅ Started on port {bot_info['port']}")
            
        except Exception as e:
            print(f"   ❌ Failed to create {bot_info['id']}: {e}")
        
        print()
    
    if not created_bots:
        print("❌ No bots were created successfully")
        return
    
    # Display summary
    print("=" * 60)
    print("🎉 DEMO BOTS CREATED SUCCESSFULLY!")
    print("=" * 60)
    
    for bot_info in created_bots:
        print(f"\n🤖 {bot_info['id'].upper().replace('-', ' ')}")
        print(f"   Type: {bot_info['type']}")
        print(f"   Voice: {bot_info['config']['voice']}")
        print(f"   Personality: {bot_info['config']['personality']}")
        print(f"   Port: {bot_info['port']}")
        print(f"   Description: {bot_info['description']}")
        
        # Show WebSocket endpoints with multi-sample rate support
        print("   Endpoints:")
        for rate in [8000, 16000, 24000]:
            print(f"     🎵 {rate}Hz: ws://localhost:{bot_info['port']}/?sample-rate={rate}")
    
    # Show testing instructions
    print("\n" + "=" * 60)
    print("🧪 TESTING YOUR BOTS")
    print("=" * 60)
    
    print("\nTest each bot with different scenarios:")
    
    test_scenarios = {
        "demo-sales": [
            "I'm interested in your products",
            "What's your pricing?", 
            "Can I schedule a demo?",
            "Tell me about your services"
        ],
        "demo-support": [
            "I need help with my account",
            "My order hasn't arrived",
            "How do I return an item?",
            "I can't log into my account"
        ],
        "demo-collection": [
            "I received a payment notice",
            "I want to set up a payment plan",
            "When is my payment due?",
            "I need to update my payment method"
        ],
        "demo-booking": [
            "I need to schedule an appointment",
            "What availability do you have?",
            "Can I change my existing appointment?",
            "I need to cancel my booking"
        ]
    }
    
    for bot_info in created_bots:
        bot_id = bot_info["id"]
        port = bot_info["port"]
        
        print(f"\n🎯 Test {bot_id.replace('-', ' ').title()}:")
        print(f"   python test_enhanced_bot.py --server ws://localhost:{port} --interactive")
        print("   Try these scenarios:")
        
        if bot_id in test_scenarios:
            for scenario in test_scenarios[bot_id]:
                print(f"     • '{scenario}'")
    
    # Show hot-reload demo
    print("\n" + "=" * 60)
    print("🔄 HOT-RELOAD DEMONSTRATION")
    print("=" * 60)
    
    if created_bots:
        demo_bot = created_bots[0]
        print(f"\nWatching for hot-reload demonstration on {demo_bot['id']}...")
        print("Original configuration:")
        print(f"  Voice: {demo_bot['config']['voice']}")
        print(f"  Temperature: {demo_bot['config']['temperature']}")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Demonstrate hot-reload
        print(f"\n🔧 Modifying {demo_bot['id']} configuration...")
        new_voice = "fable" if demo_bot['config']['voice'] != "fable" else "alloy"
        new_temp = 0.9 if demo_bot['config']['temperature'] < 0.9 else 0.5
        
        bot_manager.modify_bot(demo_bot['id'], {
            "voice": new_voice,
            "temperature": new_temp,
            "custom_instructions": "🔥 Hot-reloaded! I've been updated without restarting!"
        })
        
        print("✅ Configuration updated via hot-reload!")
        print(f"   New voice: {new_voice}")
        print(f"   New temperature: {new_temp}")
        print("   Added hot-reload message")
        
        print(f"\n🧪 Test the updated bot:")
        print(f"python test_enhanced_bot.py --server ws://localhost:{demo_bot['port']} --interactive")
        print("The bot should now mention being hot-reloaded!")
    
    # Show advanced features
    print("\n" + "=" * 60)
    print("🚀 ADVANCED FEATURES AVAILABLE")
    print("=" * 60)
    
    advanced_features = [
        "🎵 Multi-sample rate support (8kHz/16kHz/24kHz)",
        "📦 Variable chunk processing (20ms minimum)",
        "✨ Enhanced mark/clear event handling", 
        "🔄 Hot-reload without restart",
        "🤖 Multiple bot types and personalities",
        "📋 Template system for quick creation",
        "📊 Real-time bot monitoring",
        "🔌 Easy CRM/API integration",
        "🌐 Multi-language support ready",
        "🐳 Docker deployment ready"
    ]
    
    for feature in advanced_features:
        print(f"   {feature}")
    
    # Show next steps
    print("\n" + "=" * 60)
    print("📚 NEXT STEPS")
    print("=" * 60)
    
    next_steps = [
        "1. 🧪 Test each bot with the scenarios above",
        "2. 🔧 Try modifying bot configurations in real-time",
        "3. 📋 Explore bot templates with: python bot_framework.py list",
        "4. 🚀 Run full demos: python examples/restaurant_bot.py",
        "5. 📖 Read DEVELOPER_GUIDE.md for advanced usage",
        "6. 🎛️ Use the interactive launcher: python bot_launcher.py",
        "7. 🌐 Deploy to production with your Exotel integration"
    ]
    
    for step in next_steps:
        print(f"   {step}")
    
    # Keep bots running
    print("\n" + "=" * 60)
    print("🎯 DEMO BOTS RUNNING")
    print("Press Ctrl+C to stop all bots and exit")
    print("=" * 60)
    
    try:
        # Keep running until interrupted
        await asyncio.Future()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down demo bots...")
        
        # Stop all created bots
        for bot_info in created_bots:
            try:
                await bot_manager.stop_bot(bot_info["id"])
                print(f"   Stopped {bot_info['id']}")
            except Exception as e:
                print(f"   ❌ Error stopping {bot_info['id']}: {e}")
        
        bot_manager.shutdown()
        print("✅ All demo bots stopped successfully")
        print("👋 Thanks for trying the Enhanced AI Bot Framework!")

async def simple_sales_bot_demo():
    """Create just a simple sales bot for quick testing"""
    print("🤖 Creating a simple sales bot for quick testing...")
    
    bot_manager = BotManager()
    
    # Create a simple sales bot
    sales_bot = bot_manager.create_bot(
        bot_type="sales",
        bot_id="quick-sales-bot",
        config_overrides={
            "voice": "nova",
            "temperature": 0.8,
            "company_name": "Quick Demo Corp",
            "personality": "enthusiastic"
        },
        custom_instructions="You're a friendly sales rep showcasing our AI bot framework!"
    )
    
    # Start on port 5555 for easy remembering
    await bot_manager.start_bot("quick-sales-bot", port=5555)
    
    print("✅ Quick sales bot created and running!")
    print("📞 Test it now:")
    print("   python test_enhanced_bot.py --server ws://localhost:5555 --interactive")
    print("\n🎯 Try saying:")
    print("   • 'Tell me about your AI bot framework'")
    print("   • 'What can this bot do?'")
    print("   • 'I want to see a demo'")
    
    print("\nPress Ctrl+C to stop...")
    
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        await bot_manager.stop_bot("quick-sales-bot")
        bot_manager.shutdown()
        print("\n✅ Quick demo bot stopped")

if __name__ == "__main__":
    import sys
    
    print("🚀 Enhanced AI Bot Framework - Quick Start")
    print("Choose your demo:")
    print("1. Full demo (4 different bot types)")
    print("2. Simple sales bot demo") 
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    try:
        if choice == "1":
            asyncio.run(quick_start_demo())
        elif choice == "2": 
            asyncio.run(simple_sales_bot_demo())
        else:
            print("👋 Goodbye!")
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("   • Set OPENAI_API_KEY environment variable")
        print("   • Installed requirements: pip install -r requirements.txt")
        print("   • Run from the python/ directory") 