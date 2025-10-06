"""
Core bot components for the Voice AI Bot System
"""

# Import only the main bot class to avoid circular imports
from .openai_realtime_sales_bot import OpenAIRealtimeSalesBot

__all__ = [
    'OpenAIRealtimeSalesBot'
] 