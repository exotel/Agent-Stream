const WebSocket = require('ws');

const DEFAULT_CONFIG = {
  setup: {
    model: 'models/gemini-2.5-flash-native-audio-preview-12-2025',
    generationConfig: {
      responseModalities: ['AUDIO'],
      temperature: 0.4,
      topP: 0.9,
      maxOutputTokens: 2048,
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: { voiceName: 'Sulafat' },
        },
      },
    },
    realtimeInputConfig: {
      automaticActivityDetection: {
        disabled: false,
        startOfSpeechSensitivity: 'START_SENSITIVITY_LOW',
        endOfSpeechSensitivity: 'END_SENSITIVITY_HIGH',
        silenceDurationMs: 280,
        prefixPaddingMs: 60,
      },
      activityHandling: 'START_OF_ACTIVITY_INTERRUPTS',
      turnCoverage: 'TURN_INCLUDES_ONLY_ACTIVITY',
    },
    systemInstruction: { parts: [{ text: 'You are a helpful voice assistant. Keep responses concise (1-2 sentences).' }] },
    sessionResumption: {},
  },
};

const GREETING = 'Hello! How can I help you today?';

function connectGemini(apiKey, callbacks) {
  const url = `${process.env.GEMINI_LIVE_WS_URL || 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent'}?key=${apiKey}`;
  const ws = new WebSocket(url);

  ws.on('open', () => {
    callbacks.onOpen?.();
    ws.send(JSON.stringify(DEFAULT_CONFIG));
  });

  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      if (msg.setupComplete) {
        callbacks.onSetupComplete?.();
        ws.send(JSON.stringify({
          clientContent: {
            turns: [{ role: 'user', parts: [{ text: GREETING }] }],
            turnComplete: true,
          },
        }));
        return;
      }
      const serverContent = msg.serverContent;
      if (!serverContent) return;
      if (serverContent.interrupted) {
        callbacks.onInterrupted?.();
        return;
      }
      const modelTurn = serverContent.modelTurn;
      if (modelTurn?.parts) {
        for (const part of modelTurn.parts) {
          if (part.inlineData?.data) {
            callbacks.onAudio?.(part.inlineData.data);
          }
        }
      }
    } catch (e) {
      callbacks.onError?.(e);
    }
  });

  ws.on('error', (err) => callbacks.onError?.(err));
  ws.on('close', () => callbacks.onClose?.());

  return {
    sendAudio(base64Pcm16k) {
      if (ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({
        realtimeInput: {
          audio: {
            mimeType: 'audio/pcm;rate=16000',
            data: base64Pcm16k,
          },
        },
      }));
    },
    close() {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    },
  };
}

module.exports = { connectGemini };
