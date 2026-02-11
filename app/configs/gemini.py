# Configuration for Gemini model (generic sales expert voice bot)
"""
# Optional: add thinking config in generationConfig for deeper reasoning
{
    "thinkingConfig": {
        "includeThoughts": True,
        "thinkingBudget": 300
    }
}
"""
import os

# Tunable via env for latency: lower = faster turn commit (risk: cutting off user). Defaults tuned for lower round-trip.
_GEMINI_SILENCE_MS = int(os.getenv("GEMINI_SILENCE_DURATION_MS", "280"))
_GEMINI_PREFIX_MS = int(os.getenv("GEMINI_PREFIX_PADDING_MS", "60"))
_GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048"))

end_conversation_description = """
Call this function when the user explicitly indicates they want to end the conversation or says goodbye.
This should be called when the user says phrases like:
- "goodbye", "bye", "thanks bye", "ok bye"
- "धन्यवाद", "अलविदा", "बाय", "ठीक है बाय"
- "I have to go", "I need to go", "talk later"
- "बस इतना ही", "मुझे जाना है", "फिर बात करेंगे"
- Or any other clear indication that they want to end the call

Args:
    reason (str): Brief reason why the conversation is ending (e.g., "user said goodbye", "user needs to go")
Returns:
    dict: Confirmation that the call will end gracefully
        - status (str): "success"
        - message (str): Confirmation message
"""

GEMINI_CONFIG = {
    "setup": {
        # Live API (v1beta) model id format: models/{model}
        # Ref: https://ai.google.dev/gemini-api/docs/live-guide
        "model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "temperature": 0.4,
            "topP": 0.9,
            "maxOutputTokens": _GEMINI_MAX_TOKENS,
            # Native audio models do NOT support explicit languageCode; they choose language automatically.
            # Restrict language via system instruction if needed.
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Sulafat"
                    }
                }
            },
        },
        "realtimeInputConfig": {
            "automaticActivityDetection": {
                "disabled": False,
                "startOfSpeechSensitivity": "START_SENSITIVITY_LOW",
                "endOfSpeechSensitivity": "END_SENSITIVITY_HIGH",
                "silenceDurationMs": _GEMINI_SILENCE_MS,
                "prefixPaddingMs": _GEMINI_PREFIX_MS
            },
            "activityHandling": "START_OF_ACTIVITY_INTERRUPTS",
            "turnCoverage": "TURN_INCLUDES_ONLY_ACTIVITY"
        },
        "systemInstruction": {
            "parts": []
        },
        "tools": [{
            "functionDeclarations": [
                {
                    "name": "end_conversation",
                    "description": end_conversation_description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Brief reason why the conversation is ending"
                            }
                        },
                        "required": ["reason"]
                    }
                }
            ]
        }]
    }
}

# Note: Gemini Live API Native Audio defaults:
# Input: 16000Hz PCM (enforced in code)
# Output: 24000Hz PCM (default for flash-native-audio model)


def end_conversation(reason: str = "user requested") -> dict:
    """Signal to end the conversation gracefully."""
    return {
        "status": "success",
        "message": "Call will end gracefully",
        "reason": reason
    }


TOOL_REGISTRY = {
    "end_conversation": end_conversation,
}
