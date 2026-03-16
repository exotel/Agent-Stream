#!/usr/bin/env python3
"""
Custom Bot - A fully configurable voice bot.

Personality, instructions, and behavior are driven entirely by the
BotConfiguration passed in — no hardcoded scripts like the SalesBot.

This class is instantiated by DynamicBot when bot_type == "custom".
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CustomBot:
    """
    A fully configurable bot whose behavior is defined at runtime
    via the BotConfiguration object, not hardcoded logic.
    """

    def __init__(self, bot_config):
        """
        Args:
            bot_config: A BotConfiguration dataclass instance from bot_framework.py
        """
        self.config = bot_config
        self.bot_name = getattr(bot_config, "bot_name", "AI Assistant")
        self.company_name = getattr(bot_config, "company_name", "")
        self.voice = getattr(bot_config, "voice", "coral")
        self.temperature = getattr(bot_config, "temperature", 0.7)

        # custom_instructions takes priority over base_instructions
        self.instructions = (
            getattr(bot_config, "custom_instructions", "")
            or getattr(bot_config, "base_instructions", "")
        )

        logger.info(f"🤖 CustomBot initialized: {self.bot_name}")

    def get_session_config(self) -> dict:
        """
        Returns the OpenAI Realtime API session.update payload.
        Fully driven by user-supplied BotConfiguration — no hardcoded scripts.
        """
        return {
            "type": "session.update",
            "session": {
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "voice": self.voice,
                "instructions": self._build_instructions(),
                "modalities": ["text", "audio"],
                "temperature": self.temperature,
            }
        }

    def _build_instructions(self) -> str:
        """
        Returns the system prompt for the bot.
        Uses custom_instructions if provided, otherwise falls back
        to base_instructions, and finally to a sensible default.
        """
        if self.instructions:
            return self.instructions

        # Generic voice-optimised fallback
        company_clause = f" for {self.company_name}" if self.company_name else ""
        return (
            f"You are {self.bot_name}, a helpful voice assistant{company_clause}. "
            "Keep responses concise and conversational — this is a phone call. "
            "Never use markdown, bullet points, or numbered lists. "
            "Speak naturally as if having a real conversation."
        )

    def get_bot_name(self) -> str:
        return self.bot_name

    def get_conversation_starter(self) -> Optional[str]:
        """Returns the first conversation starter if configured."""
        starters = getattr(self.config, "conversation_starters", [])
        return starters[0] if starters else None
