#!/usr/bin/env python3
"""
Customer Support Bot - Production Ready
======================================

A specialized customer support bot built on the OpenAI Realtime Bot framework.
This bot is optimized for customer service, issue resolution, and support ticket management.

Features:
- Issue diagnosis and troubleshooting
- Knowledge base integration
- Escalation management
- Customer satisfaction tracking
- Support ticket creation

Usage:
 python support_bot.py

Environment Variables:
 OPENAI_API_KEY=your_openai_api_key
 COMPANY_NAME="Your Company Name"
 ASSISTANT_NAME="Support Assistant Name"
 SUPPORT_CATEGORIES="Technical,Billing,Account,General"

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

class SupportBot(OpenAIRealtimeBot):
 """
 Specialized Customer Support Bot for issue resolution and customer service.

 This bot extends the base OpenAI Realtime Bot with support-specific
 functionality and troubleshooting flows.
 """

 def __init__(self):
 """Initialize the Support Bot with support-specific configuration."""
 super().__init__()

 # Support-specific configuration
 self.bot_type = "support"
 self.support_categories = os.getenv("SUPPORT_CATEGORIES", "Technical,Billing,Account,General").split(",")
 self.escalation_threshold = int(os.getenv("ESCALATION_THRESHOLD", "3")) # attempts before escalation

 # Track support sessions
 self.support_sessions = {}

 logger.info("Support Bot initialized")
 logger.info(f"Categories: {', '.join(self.support_categories)}")
 logger.info(f"Focus: Customer issue resolution")

 async def _connect_to_openai(self, stream_id: str):
 """Connect to OpenAI with support-specific configuration."""
 try:
 sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)

 # Get support-specific session configuration
 session_config = Config.get_session_config(
 sample_rate=sample_rate,
 voice=self.openai_voice,
 bot_type="support"
 )

 # Enhance instructions with support information
 enhanced_instructions = session_config["instructions"] + f"""

SUPPORT CATEGORIES:
{chr(10).join([f"{category.strip()}" for category in self.support_categories])}

SUPPORT PROCESS:
1. Greet customer warmly and show empathy
2. Listen actively to understand the issue
3. Ask clarifying questions to diagnose the problem
4. Provide step-by-step solutions
5. Verify the solution works
6. Document the resolution
7. Follow up to ensure satisfaction

TROUBLESHOOTING GUIDELINES:
- Start with simple solutions before complex ones
- Explain each step clearly and wait for confirmation
- Be patient and understanding
- Use non-technical language when possible
- Escalate when you've reached your limits
- Always end with "Is there anything else I can help you with?"

ESCALATION TRIGGERS:
- Customer requests to speak to a human
- Issue requires system access you don't have
- Customer is frustrated after {self.escalation_threshold} attempts
- Technical issue beyond your knowledge base

Remember: Every interaction is an opportunity to build customer loyalty."""

 session_config["instructions"] = enhanced_instructions

 # Initialize support session tracking
 self.support_sessions[stream_id] = {
 "issue_category": None,
 "issue_description": None,
 "attempts": 0,
 "resolution_status": "in_progress",
 "customer_satisfaction": None
 }

 # Connect using parent class method
 await super()._connect_to_openai_with_config(stream_id, session_config)

 logger.info(f"Support Bot connected to OpenAI: {stream_id}")

 except Exception as e:
 logger.error(f"Failed to connect Support Bot to OpenAI: {e}")

 async def _send_initial_greeting(self, stream_id: str):
 """Send support-specific initial greeting."""
 try:
 if stream_id not in self.openai_connections:
 return

 openai_ws = self.openai_connections[stream_id]["websocket"]

 greeting_message = {
 "type": "response.create",
 "response": {
 "modalities": ["audio", "text"],
 "instructions": f"""Give a warm, empathetic support greeting.

Introduce yourself as {Config.ASSISTANT_NAME} from {Config.COMPANY_NAME} customer support.
Express that you're here to help and ask them to describe their issue.
Show genuine concern and readiness to assist.
Set a helpful, patient tone for the conversation."""
 }
 }

 await openai_ws.send(json.dumps(greeting_message))
 logger.info(f"Support greeting sent: {stream_id}")

 except Exception as e:
 logger.error(f"Failed to send support greeting: {e}")

 async def track_issue_resolution(self, stream_id: str, issue_data: dict):
 """
 Track issue resolution progress.

 This method can be extended to integrate with ticketing systems
 or knowledge management platforms.
 """
 try:
 if stream_id not in self.support_sessions:
 return

 session = self.support_sessions[stream_id]

 # Update session data
 for key, value in issue_data.items():
 if key in session:
 session[key] = value

 session["attempts"] += 1

 logger.info(f"Issue tracking updated for {stream_id}: {issue_data}")

 # Check if escalation is needed
 if session["attempts"] >= self.escalation_threshold:
 await self.trigger_escalation(stream_id, "max_attempts_reached")

 # Here you could integrate with ticketing systems
 # await self.update_support_ticket(stream_id, issue_data)

 except Exception as e:
 logger.error(f"Error tracking issue resolution: {e}")

 async def trigger_escalation(self, stream_id: str, reason: str):
 """
 Trigger escalation to human support.

 This method can be extended to integrate with escalation systems
 or support queue management.
 """
 try:
 logger.info(f"Escalation triggered for {stream_id}: {reason}")

 if stream_id in self.support_sessions:
 self.support_sessions[stream_id]["resolution_status"] = "escalated"

 # Here you could integrate with escalation systems
 # await self.create_escalation_ticket(stream_id, reason)

 # Notify the customer about escalation
 if stream_id in self.openai_connections:
 openai_ws = self.openai_connections[stream_id]["websocket"]

 escalation_message = {
 "type": "response.create",
 "response": {
 "modalities": ["audio", "text"],
 "instructions": """Inform the customer that you're connecting them with a human specialist who can better assist with their specific issue. Apologize for any inconvenience and assure them that help is on the way. Provide an estimated wait time if possible."""
 }
 }

 await openai_ws.send(json.dumps(escalation_message))
 logger.info(f"Escalation notification sent: {stream_id}")

 except Exception as e:
 logger.error(f"Error triggering escalation: {e}")

 async def collect_satisfaction_feedback(self, stream_id: str):
 """
 Collect customer satisfaction feedback.

 This method can be extended to integrate with feedback systems
 or customer satisfaction platforms.
 """
 try:
 if stream_id not in self.openai_connections:
 return

 openai_ws = self.openai_connections[stream_id]["websocket"]

 feedback_message = {
 "type": "response.create",
 "response": {
 "modalities": ["audio", "text"],
 "instructions": """Ask the customer to rate their support experience on a scale of 1-5 and if they have any additional feedback. Be genuine in wanting to improve the service."""
 }
 }

 await openai_ws.send(json.dumps(feedback_message))
 logger.info(f"Satisfaction feedback requested: {stream_id}")

 except Exception as e:
 logger.error(f"Error collecting satisfaction feedback: {e}")

 async def _cleanup_connection(self, stream_id: str):
 """Clean up support session data."""
 try:
 # Log final session data
 if stream_id in self.support_sessions:
 session = self.support_sessions[stream_id]
 logger.info(f"Support session completed: {stream_id}")
 logger.info(f" Category: {session.get('issue_category', 'Unknown')}")
 logger.info(f" Attempts: {session.get('attempts', 0)}")
 logger.info(f" Status: {session.get('resolution_status', 'Unknown')}")

 # Clean up session data
 del self.support_sessions[stream_id]

 # Call parent cleanup
 await super()._cleanup_connection(stream_id)

 except Exception as e:
 logger.error(f"Error during support cleanup: {e}")

def main():
 """Main entry point for the Support Bot."""
 try:
 # Validate support-specific environment
 required_vars = ["OPENAI_API_KEY", "COMPANY_NAME"]
 missing_vars = [var for var in required_vars if not os.getenv(var)]

 if missing_vars:
 logger.error(f"Missing required environment variables: {missing_vars}")
 logger.error("Please set the following:")
 for var in missing_vars:
 logger.error(f" export {var}='your_value'")
 return

 # Start the Support Bot
 logger.info("Starting Support Bot...")
 bot = SupportBot()
 asyncio.run(bot.start_server())

 except KeyboardInterrupt:
 logger.info("Support Bot stopped by user")
 except Exception as e:
 logger.error(f"Support Bot failed to start: {e}")
 raise

if __name__ == "__main__":
 main() 