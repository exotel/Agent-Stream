#!/usr/bin/env python3
"""
E-Commerce Customer Support Bot Example
Demonstrates advanced multi-bot setup for e-commerce customer service
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot_framework import BotManager, BotConfiguration, BotCapabilities, BotPersonality

async def create_ecommerce_support_system():
    """Create a complete e-commerce customer support system with multiple specialized bots"""
    
    bot_manager = BotManager()
    
    # Configuration for TechMart - fictional e-commerce company
    company_info = {
        "company_name": "TechMart",
        "service_description": "Electronics and gadgets online store",
        "contact_info": {
            "phone": "+1-800-TECHMART",
            "email": "support@techmart.com",
            "website": "www.techmart.com",
            "hours": "24/7 AI support, Human agents 9 AM - 9 PM EST"
        }
    }
    
    # 1. General Customer Support Bot
    general_support_config = {
        **company_info,
        "voice": "coral",
        "temperature": 0.3,
        "personality": "empathetic",
        "capabilities": {
            "can_access_knowledge_base": True,
            "can_transfer_to_human": True,
            "can_access_crm": True,
            "can_send_emails": True,
            "can_process_forms": True
        }
    }
    
    general_support_instructions = """
You are TechMart's AI customer support representative. You help customers with:

COMMON ISSUES:
- Order status and tracking
- Returns and refunds
- Product information and compatibility
- Account issues
- Payment problems
- Shipping questions
- Warranty claims

CAPABILITIES:
- Look up order information by order number or email
- Initiate returns and provide return labels
- Check product availability and specifications
- Escalate complex issues to human agents
- Process refunds (under $50 automatically)

TONE: Empathetic, patient, solution-focused. Always apologize for inconvenience and thank customers for their patience.

ESCALATION TRIGGERS:
- Angry customers (use calm, de-escalation techniques)
- Requests over $50 refund
- Technical issues you can't solve
- Complaints about damaged/defective products
- Billing disputes over $100

Remember: Customer satisfaction is our top priority. When in doubt, escalate to human agents.
"""
    
    # 2. Sales Support Bot
    sales_support_config = {
        **company_info,
        "voice": "nova",
        "temperature": 0.7,
        "personality": "enthusiastic",
        "capabilities": {
            "can_access_knowledge_base": True,
            "can_access_crm": True,
            "can_send_emails": True,
            "can_schedule_appointments": True
        }
    }
    
    sales_support_instructions = """
You are TechMart's AI sales assistant. You help customers with:

SALES FOCUS:
- Product recommendations based on needs
- Price comparisons and deals
- Bundle suggestions for better value
- Technical specifications and compatibility
- Warranty and protection plan options

PRODUCT CATEGORIES:
- Smartphones & Accessories
- Laptops & Computers
- Gaming (consoles, PC parts, accessories)
- Smart Home devices
- Audio equipment (headphones, speakers)
- Cameras & Photography

SALES TECHNIQUES:
- Ask qualifying questions about use cases
- Highlight current promotions and discounts
- Suggest complementary products
- Explain warranty benefits
- Create urgency with limited-time offers

CURRENT PROMOTIONS:
- Winter Sale: Up to 30% off select items
- Bundle & Save: 15% off when buying 3+ items
- Extended Warranty: 20% off protection plans
- Free shipping on orders over $75

Always focus on finding the right solution for customer needs, not just the most expensive option.
"""
    
    # 3. Technical Support Bot
    tech_support_config = {
        **company_info,
        "voice": "echo",
        "temperature": 0.2,
        "personality": "professional",
        "capabilities": {
            "can_access_knowledge_base": True,
            "can_transfer_to_human": True,
            "can_send_emails": True,
            "can_process_forms": True
        }
    }
    
    tech_support_instructions = """
You are TechMart's AI technical support specialist. You help customers with:

TECHNICAL AREAS:
- Device setup and configuration
- Troubleshooting hardware/software issues
- Compatibility questions
- Performance optimization
- Installation guidance
- Driver and software updates

TROUBLESHOOTING APPROACH:
1. Gather specific details about the issue
2. Ask about recent changes or updates
3. Guide through basic troubleshooting steps
4. Escalate complex hardware issues
5. Provide follow-up resources and links

COMMON SOLUTIONS:
- Power cycle devices
- Check connections and cables
- Update drivers and firmware
- Clear cache/reset settings
- Check for software conflicts

ESCALATION CRITERIA:
- Hardware failure suspected
- Customer needs hands-on assistance
- Issue requires advanced diagnostics
- Safety concerns with electrical products

Always provide step-by-step instructions and confirm understanding at each step.
"""
    
    # Create all three bots
    bots_to_create = [
        ("support", "general-support", general_support_config, general_support_instructions, 5020),
        ("sales", "sales-support", sales_support_config, sales_support_instructions, 5021),
        ("support", "tech-support", tech_support_config, tech_support_instructions, 5022)
    ]
    
    created_bots = []
    
    for bot_type, bot_id, config, instructions, port in bots_to_create:
        try:
            bot_config = bot_manager.create_bot(
                bot_type=bot_type,
                bot_id=bot_id,
                config_overrides=config,
                custom_instructions=instructions
            )
            
            await bot_manager.start_bot(bot_id, port=port)
            
            created_bots.append({
                "id": bot_id,
                "type": bot_type,
                "port": port,
                "config": bot_config
            })
            
            print(f"✅ Created and started {bot_id} on port {port}")
            
        except Exception as e:
            print(f"❌ Failed to create {bot_id}: {e}")
    
    # Display system information
    print("\n" + "="*60)
    print("🛍️ TechMart E-Commerce Support System Ready!")
    print("="*60)
    
    for bot in created_bots:
        print(f"\n🤖 {bot['id'].upper().replace('-', ' ')}")
        print(f"   Type: {bot['type']}")
        print(f"   Voice: {bot['config'].voice}")
        print(f"   Personality: {bot['config'].personality.value}")
        print(f"   Port: {bot['port']}")
        print(f"   Endpoints:")
        for rate in [8000, 16000, 24000]:
            print(f"     • ws://localhost:{bot['port']}/?sample-rate={rate}")
    
    # Create a routing guide
    print("\n" + "="*60)
    print("📋 BOT ROUTING GUIDE")
    print("="*60)
    
    routing_guide = {
        "General Support (Port 5020)": [
            "Order status and tracking",
            "Returns and refunds",
            "Account issues",
            "General inquiries",
            "Complaints and feedback"
        ],
        "Sales Support (Port 5021)": [
            "Product recommendations",
            "Price comparisons",
            "Current deals and promotions",
            "Pre-purchase questions",
            "Bundle suggestions"
        ],
        "Technical Support (Port 5022)": [
            "Device setup help",
            "Troubleshooting issues",
            "Compatibility questions",
            "Performance problems",
            "Installation guidance"
        ]
    }
    
    for bot_name, use_cases in routing_guide.items():
        print(f"\n🎯 {bot_name}:")
        for use_case in use_cases:
            print(f"   • {use_case}")
    
    # Testing examples
    print("\n" + "="*60)
    print("🧪 TESTING EXAMPLES")
    print("="*60)
    
    test_scenarios = {
        5020: [
            "Where is my order #TM123456?",
            "I want to return a laptop I bought last week",
            "My account is locked, can you help?",
            "I'm not happy with my recent purchase"
        ],
        5021: [
            "I need a gaming laptop under $1000",
            "What's the best smartphone for photography?",
            "Do you have any deals on headphones?",
            "I want to build a PC, what do I need?"
        ],
        5022: [
            "My laptop won't turn on after the update",
            "How do I set up my new smart TV?",
            "Is this graphics card compatible with my computer?",
            "My phone keeps crashing, what should I do?"
        ]
    }
    
    for port, scenarios in test_scenarios.items():
        bot_name = [b['id'] for b in created_bots if b['port'] == port][0]
        print(f"\n🔍 Test {bot_name.replace('-', ' ').title()} (Port {port}):")
        print(f"   python ../test_enhanced_bot.py --server ws://localhost:{port} --interactive")
        print("   Try these scenarios:")
        for scenario in scenarios:
            print(f"     • '{scenario}'")
    
    # Advanced features demonstration
    print("\n" + "="*60)
    print("🚀 ADVANCED FEATURES DEMO")
    print("="*60)
    
    # Create a load balancer simulation
    print("\n💡 You can simulate load balancing by:")
    print("1. Running multiple instances of the same bot type on different ports")
    print("2. Using nginx or similar to distribute traffic")
    print("3. Implementing health checks and failover")
    
    # Hot-reload demonstration
    print("\n🔄 Hot-reload capabilities:")
    print("1. Modify any bot configuration in active_bots/ directory")
    print("2. Changes are automatically detected and applied")
    print("3. No need to restart the bot!")
    
    # Analytics simulation
    print("\n📊 Monitor bot performance:")
    active_bots = bot_manager.list_active_bots()
    print(f"Currently running {len(active_bots)} bots:")
    for bot_id in active_bots:
        info = bot_manager.get_bot_info(bot_id)
        print(f"   • {bot_id}: {info['config']['bot_type']} on port {info['port']}")
    
    # Keep the system running
    print("\n" + "="*60)
    print("🎯 SYSTEM STATUS: ACTIVE")
    print("Press Ctrl+C to shutdown all bots")
    print("="*60)
    
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\n🛑 Shutting down TechMart support system...")
        for bot in created_bots:
            await bot_manager.stop_bot(bot['id'])
            print(f"   Stopped {bot['id']}")
        
        bot_manager.shutdown()
        print("✅ All bots stopped successfully")

# Utility function to demonstrate real-time configuration changes
async def demonstrate_hot_reload():
    """Demonstrate hot-reload capabilities"""
    bot_manager = BotManager()
    
    print("🔄 Hot-Reload Demonstration")
    print("="*40)
    
    # Create a test bot
    test_bot = bot_manager.create_bot("support", "hot-reload-test", {
        "voice": "alloy",
        "temperature": 0.5
    })
    
    print(f"Created test bot with voice: {test_bot.voice}, temperature: {test_bot.temperature}")
    
    await bot_manager.start_bot("hot-reload-test", port=5099)
    print("Started bot on port 5099")
    
    # Wait a moment
    await asyncio.sleep(2)
    
    # Modify the bot configuration
    print("\n🔧 Modifying bot configuration...")
    bot_manager.modify_bot("hot-reload-test", {
        "voice": "nova",
        "temperature": 0.8,
        "custom_instructions": "You are now more creative and use Nova voice!"
    })
    
    print("✅ Configuration updated via hot-reload!")
    print("   New voice: nova")
    print("   New temperature: 0.8")
    print("   Added custom instructions")
    
    print("\nTest the updated bot:")
    print("python ../test_enhanced_bot.py --server ws://localhost:5099 --interactive")
    
    # Keep running for testing
    print("\nPress Ctrl+C to stop demonstration")
    try:
        await asyncio.sleep(30)  # Run for 30 seconds
    except KeyboardInterrupt:
        pass
    
    await bot_manager.stop_bot("hot-reload-test")
    bot_manager.shutdown()
    print("🛑 Hot-reload demonstration complete")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--hot-reload-demo":
        asyncio.run(demonstrate_hot_reload())
    else:
        asyncio.run(create_ecommerce_support_system()) 