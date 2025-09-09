#!/usr/bin/env python3
"""
Restaurant Reservation Bot Example
Shows how to create a specialized bot for restaurant reservations using the framework
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot_framework import BotManager, BotConfiguration, BotCapabilities

async def create_restaurant_bot():
    """Create and configure a restaurant reservation bot"""
    
    bot_manager = BotManager()
    
    # Create restaurant-specific configuration
    restaurant_config = {
        "voice": "fable",              # Warm, welcoming voice
        "temperature": 0.6,            # Conversational but consistent
        "personality": "friendly",      # Warm hospitality
        
        # Restaurant details
        "company_name": "Bella Vista Restaurant",
        "service_description": "Fine dining with Italian cuisine and scenic city views",
        "contact_info": {
            "phone": "+1-555-BELLA-1",
            "email": "reservations@bellavista.com",
            "address": "123 Downtown Ave, City Center"
        },
        
        # Enhanced capabilities for restaurant needs
        "capabilities": {
            "can_schedule_appointments": True,
            "can_send_emails": True,
            "can_process_forms": True,
            "can_access_crm": True
        }
    }
    
    # Detailed instructions for restaurant reservation handling
    custom_instructions = """
You are the AI reservation assistant for Bella Vista Restaurant, an upscale Italian restaurant with scenic city views.

RESTAURANT DETAILS:
- Cuisine: Authentic Italian fine dining
- Ambiance: Romantic, upscale, city views
- Capacity: 80 seats, private dining room available
- Hours: Tuesday-Sunday 5:00 PM - 10:00 PM (Closed Mondays)
- Dress code: Smart casual to formal
- Average meal duration: 90-120 minutes

RESERVATION PROCESS:
1. Greet warmly and ask how you can help
2. For reservations, collect:
   - Preferred date and time
   - Number of guests (max 8 for regular tables, 16 for private room)
   - Name for reservation
   - Phone number
   - Special occasions (anniversary, birthday, etc.)
   - Dietary restrictions or allergies
   - Seating preferences (window view, quiet corner, etc.)

3. Check availability and offer alternatives if needed
4. Confirm all details and provide confirmation number
5. Mention our sommelier's wine pairing recommendations
6. Ask about valet parking (complimentary for reservations of 4+)

SPECIAL OFFERS:
- Happy Hour: Tuesday-Thursday 5-6 PM (20% off appetizers and wine)
- Wine Wednesday: 30% off bottles under $100
- Chef's Table: Available Friday-Saturday (7-course tasting menu)

POLICIES:
- Reservations recommended, walk-ins welcome subject to availability
- Cancellation policy: 24 hours notice required
- Large parties (8+) require private dining room and deposit
- Children welcome but no children's menu (can modify regular dishes)

Always be welcoming, knowledgeable about our offerings, and help create memorable dining experiences.
"""
    
    # Create the restaurant bot
    restaurant_bot = bot_manager.create_bot(
        bot_type="appointment_booking",  # Base type for reservations
        bot_id="bella-vista-reservations",
        config_overrides=restaurant_config,
        custom_instructions=custom_instructions
    )
    
    print("🍽️ Bella Vista Restaurant Reservation Bot Created!")
    print(f"Bot ID: {restaurant_bot.bot_id}")
    print(f"Voice: {restaurant_bot.voice}")
    print(f"Personality: {restaurant_bot.personality.value}")
    
    # Start the bot
    port = 5010
    await bot_manager.start_bot("bella-vista-reservations", port=port)
    
    print(f"\n🚀 Restaurant bot running on port {port}")
    print("📞 WebSocket endpoints:")
    print(f"   • ws://localhost:{port}/?sample-rate=8000")
    print(f"   • ws://localhost:{port}/?sample-rate=16000") 
    print(f"   • ws://localhost:{port}/?sample-rate=24000")
    
    print("\n🧪 Test the bot:")
    print(f"python ../test_enhanced_bot.py --server ws://localhost:{port} --interactive")
    
    print("\n📋 Try these conversation starters:")
    print("- 'I'd like to make a reservation for Saturday night'")
    print("- 'Do you have availability for 4 people tomorrow?'")
    print("- 'I want to book your chef's table experience'")
    print("- 'Can I reserve the private dining room for an anniversary?'")
    
    # Keep running
    print("\nPress Ctrl+C to stop the bot")
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\n🛑 Stopping restaurant bot...")
        await bot_manager.stop_bot("bella-vista-reservations")
        bot_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(create_restaurant_bot()) 