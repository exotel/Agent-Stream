/**
 * AI Services Configuration
 * 
 * Standard configuration for connecting LLMs, STT, TTS, and Dialog services
 * Switch providers by changing config - no code changes needed!
 */

require('dotenv').config();

module.exports = {
  // ═══════════════════════════════════════════════════════════
  // Speech-to-Text (STT) Configuration
  // ═══════════════════════════════════════════════════════════
  stt: {
    provider: process.env.AI_STT_PROVIDER || process.env.STT_PROVIDER || 'whisper', // deepgram, google, azure, assemblyai, whisper
    
    // Deepgram (Recommended - Fast, accurate)
    deepgram: {
      apiKey: process.env.DEEPGRAM_API_KEY,
      model: 'nova-2',
      language: 'en-US',
      encoding: 'linear16',
      sampleRate: 8000,
      interimResults: true
    },
    
    // Google Speech-to-Text
    google: {
      credentials: process.env.GOOGLE_APPLICATION_CREDENTIALS,
      languageCode: 'en-US',
      encoding: 'LINEAR16',
      sampleRateHertz: 8000,
      model: 'phone_call'
    },
    
    // Azure Speech Services
    azure: {
      subscriptionKey: process.env.AZURE_SPEECH_KEY,
      region: process.env.AZURE_SPEECH_REGION,
      language: 'en-US',
      format: 'raw-16khz-16bit-mono-pcm'
    },
    
    // AssemblyAI
    assemblyai: {
      apiKey: process.env.ASSEMBLYAI_API_KEY,
      sampleRate: 8000,
      languageCode: 'en'
    },
    
    // OpenAI Whisper
    whisper: {
      apiKey: process.env.OPENAI_API_KEY,
      model: 'whisper-1',
      language: 'en'
    }
  },

  // ═══════════════════════════════════════════════════════════
  // Large Language Model (LLM) Configuration
  // ═══════════════════════════════════════════════════════════
  llm: {
    provider: process.env.LLM_PROVIDER || 'openai', // openai, gemini, azure, anthropic, groq
    
    // OpenAI (GPT-4, GPT-3.5)
    openai: {
      apiKey: process.env.OPENAI_API_KEY,
      model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview',
      temperature: 0.7,
      maxTokens: 150,
      systemPrompt: process.env.SYSTEM_PROMPT || 'You are a helpful voice assistant. Keep responses concise and natural for voice conversation.'
    },
    
    // Google Gemini
    gemini: {
      apiKey: process.env.GEMINI_API_KEY,
      model: process.env.GEMINI_MODEL || 'gemini-pro',
      temperature: 0.7,
      maxTokens: 150,
      systemPrompt: process.env.SYSTEM_PROMPT || 'You are a helpful voice assistant. Keep responses concise and natural for voice conversation.'
    },
    
    // Azure OpenAI
    azureOpenai: {
      apiKey: process.env.AZURE_OPENAI_KEY,
      endpoint: process.env.AZURE_OPENAI_ENDPOINT,
      deploymentName: process.env.AZURE_OPENAI_DEPLOYMENT,
      apiVersion: '2024-02-15-preview',
      temperature: 0.7,
      maxTokens: 150,
      systemPrompt: process.env.SYSTEM_PROMPT || 'You are a helpful voice assistant. Keep responses concise and natural for voice conversation.'
    },
    
    // Anthropic Claude
    anthropic: {
      apiKey: process.env.ANTHROPIC_API_KEY,
      model: process.env.ANTHROPIC_MODEL || 'claude-3-sonnet-20240229',
      maxTokens: 150,
      temperature: 0.7,
      systemPrompt: process.env.SYSTEM_PROMPT || 'You are a helpful voice assistant. Keep responses concise and natural for voice conversation.'
    },
    
    // Groq (Fast inference)
    groq: {
      apiKey: process.env.GROQ_API_KEY,
      model: process.env.GROQ_MODEL || 'mixtral-8x7b-32768',
      temperature: 0.7,
      maxTokens: 150,
      systemPrompt: process.env.SYSTEM_PROMPT || 'You are a helpful voice assistant. Keep responses concise and natural for voice conversation.'
    }
  },

  // ═══════════════════════════════════════════════════════════
  // Text-to-Speech (TTS) Configuration
  // ═══════════════════════════════════════════════════════════
  tts: {
    provider: process.env.AI_TTS_PROVIDER || process.env.TTS_PROVIDER || 'openai', // elevenlabs, google, azure, openai, playht
    
    // ElevenLabs (Recommended - Best quality)
    elevenlabs: {
      apiKey: process.env.ELEVENLABS_API_KEY,
      voiceId: process.env.ELEVENLABS_VOICE_ID || 'EXAVITQu4vr4xnSDxMaL', // Default: Bella
      model: 'eleven_turbo_v2',
      stability: 0.5,
      similarityBoost: 0.75,
      outputFormat: 'pcm_16000' // Will be resampled to match call
    },
    
    // Google Text-to-Speech
    google: {
      credentials: process.env.GOOGLE_APPLICATION_CREDENTIALS,
      languageCode: 'en-US',
      voiceName: 'en-US-Neural2-F',
      audioEncoding: 'LINEAR16',
      sampleRateHertz: 16000
    },
    
    // Azure Text-to-Speech
    azure: {
      subscriptionKey: process.env.AZURE_SPEECH_KEY,
      region: process.env.AZURE_SPEECH_REGION,
      voiceName: 'en-US-JennyNeural',
      outputFormat: 'raw-16khz-16bit-mono-pcm'
    },
    
    // OpenAI TTS
    openai: {
      apiKey: process.env.OPENAI_API_KEY,
      model: 'tts-1', // or tts-1-hd
      voice: 'alloy', // alloy, echo, fable, onyx, nova, shimmer
      speed: 1.0
    },
    
    // Play.ht
    playht: {
      apiKey: process.env.PLAYHT_API_KEY,
      userId: process.env.PLAYHT_USER_ID,
      voice: process.env.PLAYHT_VOICE || 'en-US-JennyNeural',
      quality: 'premium',
      outputFormat: 'raw',
      sampleRate: 16000
    }
  },

  // ═══════════════════════════════════════════════════════════
  // Dialog Management (Optional)
  // ═══════════════════════════════════════════════════════════
  dialog: {
    provider: process.env.DIALOG_PROVIDER || 'none', // dialogflow, none
    
    // Google Dialogflow
    dialogflow: {
      projectId: process.env.DIALOGFLOW_PROJECT_ID,
      credentials: process.env.GOOGLE_APPLICATION_CREDENTIALS,
      languageCode: 'en-US',
      sessionPath: null // Will be set per call
    }
  },

  // ═══════════════════════════════════════════════════════════
  // Voice AI Frameworks
  // ═══════════════════════════════════════════════════════════
  framework: {
    provider: process.env.VOICE_FRAMEWORK || 'custom', // pipecat, custom
    
    // Pipecat Configuration
    pipecat: {
      enabled: process.env.PIPECAT_ENABLED === 'true',
      // Pipecat will use STT, LLM, TTS configs above
      turnDetection: {
        silenceDuration: 1.0, // seconds
        silenceThreshold: 0.01
      }
    }
  },

  // ═══════════════════════════════════════════════════════════
  // General Configuration
  // ═══════════════════════════════════════════════════════════
  general: {
    // Conversation settings
    maxConversationTurns: parseInt(process.env.MAX_CONVERSATION_TURNS) || 50,
    conversationTimeout: parseInt(process.env.CONVERSATION_TIMEOUT) || 300000, // 5 minutes
    
    // Response settings
    maxResponseLength: parseInt(process.env.MAX_RESPONSE_LENGTH) || 200,
    streamResponses: process.env.STREAM_RESPONSES === 'true',
    
    // Audio processing
    audioBufferSize: 3200, // 100ms at 8kHz
    silenceThreshold: 0.01,
    silenceDuration: 1000, // ms
    
    // Performance
    enableCaching: process.env.ENABLE_CACHING === 'true',
    cacheTimeout: 3600000, // 1 hour
    
    // Fallback responses
    fallbackMessage: process.env.FALLBACK_MESSAGE || "I'm sorry, I didn't understand that. Could you please repeat?",
    errorMessage: process.env.ERROR_MESSAGE || "I'm experiencing technical difficulties. Please try again.",
    
    // Logging
    logConversations: process.env.LOG_CONVERSATIONS === 'true',
    logAudio: process.env.LOG_AUDIO === 'false'
  }
};

