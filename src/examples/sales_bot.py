#!/usr/bin/env python3
"""
Sales Bot Example - Production Ready
===================================

A specialized sales bot built on the OpenAI Realtime Bot framework.
This bot is optimized for sales conversations, lead qualification,
and customer engagement.

Features:
- Natural sales conversation flow
- Lead qualification capabilities
- Objection handling
- Product knowledge integration
- CRM integration ready

Usage:
 python sales_bot.py

Environment Variables:
 OPENAI_API_KEY=your_openai_api_key
 COMPANY_NAME="Your Company Name"
 ASSISTANT_NAME="Sales Assistant Name"
 PRODUCTS="Product1,Product2,Product3"

Author: Agent Stream Team
Version: 2.0.0
"""

import os
import sys
import asyncio
import logging
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.realtime_bot import OpenAIRealtimeBot
from config.settings import Config

# Configure logging
logging.basicConfig(
 level=logging.INFO,
 format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SalesBot(OpenAIRealtimeBot):
 """
 Specialized Sales Bot for customer acquisition and lead qualification.

 This bot extends the base OpenAI Realtime Bot with sales-specific
 functionality and conversation flows.
 """

 def __init__(self):
 """Initialize the Sales Bot with sales-specific configuration."""
 super().__init__()

 # Sales-specific configuration
 self.bot_type = "sales"
 self.products = os.getenv("PRODUCTS", "AI Solutions,Voice Bots,Customer Service").split(",")
 self.qualification_criteria = {
 "budget": None,
 "authority": None,
 "need": None,
 "timeline": None
 }

 logger.info("Sales Bot initialized")
 logger.info(f"Products: {', '.join(self.products)}")
 logger.info(f"Focus: Lead generation and qualification")

 async def _connect_to_openai(self, stream_id: str):
 """Connect to OpenAI with sales-specific configuration."""
 try:
 sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)

 # Get sales-specific session configuration
 session_config = Config.get_session_config(
 sample_rate=sample_rate,
 voice=self.openai_voice,
 bot_type="sales"
 )

 # Enhance instructions with product information
 enhanced_instructions = session_config["instructions"] + f"""

PRODUCT PORTFOLIO:
{chr(10).join([f"{product.strip()}" for product in self.products])}

SALES PROCESS:
1. Build rapport and establish trust
2. Identify pain points and challenges
3. Qualify budget, authority, need, and timeline (BANT)
4. Present relevant solutions
5. Handle objections professionally
6. Guide to next steps (demo, trial, meeting)

CONVERSATION GUIDELINES:
- Ask open-ended questions to understand needs
- Listen for buying signals and pain indicators
- Use consultative selling approach
- Focus on value, not just features
- Create urgency when appropriate
- Always end with a clear next step

Remember: You're a trusted advisor, not just a salesperson."""

 session_config["instructions"] = enhanced_instructions

 # Connect using parent class method
 await super()._connect_to_openai_with_config(stream_id, session_config)

 logger.info(f"Sales Bot connected to OpenAI: {stream_id}")

 except Exception as e:
 logger.error(f"Failed to connect Sales Bot to OpenAI: {e}")

 async def _send_initial_greeting(self, stream_id: str):
 """Send sales-specific initial greeting."""
 try:
 if stream_id not in self.openai_connections:
 return

 openai_ws = self.openai_connections[stream_id]["websocket"]

 greeting_message = {
 "type": "response.create",
 "response": {
 "modalities": ["audio", "text"],
 "instructions": f"""Give a warm, professional sales greeting. 

Introduce yourself as {Config.ASSISTANT_NAME} from {Config.COMPANY_NAME}. 
Ask how you can help them today and show genuine interest in their business needs.
Keep it natural and conversational - avoid sounding scripted.
Set a positive, helpful tone for the conversation."""
 }
 }

 await openai_ws.send(json.dumps(greeting_message))
 logger.info(f"Sales greeting sent: {stream_id}")

 except Exception as e:
 logger.error(f"Failed to send sales greeting: {e}")

 async def handle_qualification_data(self, stream_id: str, qualification_info: dict):
 """
 Handle qualification data extraction from conversation.

 This method can be extended to integrate with CRM systems
 or lead management platforms.
 """
 try:
 # Update qualification criteria
 for key, value in qualification_info.items():
 if key in self.qualification_criteria:
 self.qualification_criteria[key] = value

 logger.info(f"Qualification updated for {stream_id}: {qualification_info}")

 # Here you could integrate with CRM systems
 # await self.update_crm_lead(stream_id, qualification_info)

 except Exception as e:
 logger.error(f"Error handling qualification data: {e}")

 async def schedule_follow_up(self, stream_id: str, follow_up_type: str, contact_info: dict):
 """
 Schedule follow-up activities.

 This method can be extended to integrate with calendar systems
 or task management platforms.
 """
 try:
 logger.info(f"Scheduling {follow_up_type} for {stream_id}")
 logger.info(f"Contact: {contact_info}")

 # Here you could integrate with calendar/scheduling systems
 # await self.create_calendar_event(follow_up_type, contact_info)

 except Exception as e:
 logger.error(f"Error scheduling follow-up: {e}")

def main():
 """Main entry point for the Sales Bot."""
 try:
 # Validate sales-specific environment
 required_vars = ["OPENAI_API_KEY", "COMPANY_NAME"]
 missing_vars = [var for var in required_vars if not os.getenv(var)]

 if missing_vars:
 logger.error(f"Missing required environment variables: {missing_vars}")
 logger.error("Please set the following:")
 for var in missing_vars:
 logger.error(f" export {var}='your_value'")
 return

 # Start the Sales Bot
 logger.info("Starting Sales Bot...")
 bot = SalesBot()
 asyncio.run(bot.start_server())

 except KeyboardInterrupt:
 logger.info("Sales Bot stopped by user")
 except Exception as e:
 logger.error(f"Sales Bot failed to start: {e}")
 raise

if __name__ == "__main__":
 main() 