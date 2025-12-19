# AI Service Adapters

This directory contains adapters for various AI service providers.

## Structure

```
adapters/
├── stt/           # Speech-to-Text adapters
├── llm/           # Large Language Model adapters
└── tts/           # Text-to-Speech adapters
```

## Implemented Adapters

### Speech-to-Text (STT)
- ✅ `deepgramAdapter.js` - Deepgram STT
- 📝 `googleSTTAdapter.js` - Google Speech-to-Text (template)
- 📝 `azureSTTAdapter.js` - Azure Speech Services (template)
- 📝 `assemblyaiAdapter.js` - AssemblyAI (template)
- 📝 `whisperAdapter.js` - OpenAI Whisper (template)

### Large Language Models (LLM)
- ✅ `openaiAdapter.js` - OpenAI GPT
- 📝 `geminiAdapter.js` - Google Gemini (template)
- 📝 `azureOpenaiAdapter.js` - Azure OpenAI (template)
- 📝 `anthropicAdapter.js` - Anthropic Claude (template)
- 📝 `groqAdapter.js` - Groq (template)

### Text-to-Speech (TTS)
- ✅ `elevenlabsAdapter.js` - ElevenLabs TTS
- 📝 `googleTTSAdapter.js` - Google TTS (template)
- 📝 `azureTTSAdapter.js` - Azure TTS (template)
- 📝 `openaiTTSAdapter.js` - OpenAI TTS (template)
- 📝 `playhtAdapter.js` - Play.ht (template)

## Creating New Adapters

### STT Adapter Template

```javascript
/**
 * Your Provider STT Adapter
 * Install: npm install your-provider-sdk
 */

const Logger = require('../../../utils/logger');
const logger = new Logger('YOUR-PROVIDER');

let ProviderSDK;
try {
  ProviderSDK = require('your-provider-sdk');
} catch (error) {
  logger.warn('Provider SDK not installed. Install with: npm install your-provider-sdk');
}

class YourProviderAdapter {
  /**
   * Transcribe audio buffer
   * 
   * @param {Buffer} audioBuffer - PCM audio
   * @param {Object} config - Configuration
   * @returns {Promise<Object>} - {text, confidence, isFinal}
   */
  static async transcribe(audioBuffer, config) {
    if (!ProviderSDK) {
      throw new Error('Provider SDK not installed');
    }

    try {
      // Implement your transcription logic here
      const result = await ProviderSDK.transcribe(audioBuffer, config);
      
      return {
        text: result.transcript,
        confidence: result.confidence,
        isFinal: true
      };
    } catch (error) {
      logger.error('Transcription error:', error.message);
      throw error;
    }
  }

  /**
   * Create streaming session
   * 
   * @param {Object} config - Configuration
   * @param {Function} onTranscript - Callback for transcripts
   * @param {Function} onError - Error callback
   * @returns {Object} - {send, end} methods
   */
  static createStream(config, onTranscript, onError) {
    if (!ProviderSDK) {
      throw new Error('Provider SDK not installed');
    }

    try {
      // Create stream connection
      const stream = ProviderSDK.createStream(config);
      
      // Handle results
      stream.on('data', (result) => {
        onTranscript({
          text: result.text,
          isFinal: result.isFinal,
          confidence: result.confidence
        });
      });
      
      // Handle errors
      stream.on('error', (error) => {
        logger.error('Stream error:', error);
        onError(error);
      });
      
      return {
        send: (audioBuffer) => {
          stream.write(audioBuffer);
        },
        end: () => {
          stream.end();
        }
      };
    } catch (error) {
      logger.error('Stream creation error:', error.message);
      throw error;
    }
  }
}

module.exports = YourProviderAdapter;
```

### LLM Adapter Template

```javascript
/**
 * Your Provider LLM Adapter
 * Install: npm install your-llm-sdk
 */

const Logger = require('../../../utils/logger');
const logger = new Logger('YOUR-LLM');

let LLMSDK;
try {
  LLMSDK = require('your-llm-sdk');
} catch (error) {
  logger.warn('LLM SDK not installed. Install with: npm install your-llm-sdk');
}

class YourLLMAdapter {
  /**
   * Generate response
   * 
   * @param {Object} config - Configuration with messages
   * @returns {Promise<string>} - Generated response
   */
  static async generate(config) {
    if (!LLMSDK) {
      throw new Error('LLM SDK not installed');
    }

    try {
      const client = new LLMSDK(config.apiKey);
      
      const response = await client.generate({
        model: config.model,
        messages: config.messages,
        temperature: config.temperature,
        max_tokens: config.maxTokens
      });
      
      return response.content;
    } catch (error) {
      logger.error('Generation error:', error.message);
      throw error;
    }
  }

  /**
   * Stream response
   * 
   * @param {Object} config - Configuration
   * @yields {string} - Response chunks
   */
  static async *stream(config) {
    if (!LLMSDK) {
      throw new Error('LLM SDK not installed');
    }

    try {
      const client = new LLMSDK(config.apiKey);
      
      const stream = await client.generateStream({
        model: config.model,
        messages: config.messages,
        temperature: config.temperature,
        max_tokens: config.maxTokens
      });
      
      for await (const chunk of stream) {
        if (chunk.content) {
          yield chunk.content;
        }
      }
    } catch (error) {
      logger.error('Stream error:', error.message);
      throw error;
    }
  }
}

module.exports = YourLLMAdapter;
```

### TTS Adapter Template

```javascript
/**
 * Your Provider TTS Adapter
 * Install: npm install your-tts-sdk
 */

const Logger = require('../../../utils/logger');
const logger = new Logger('YOUR-TTS');

let TTSSDK;
try {
  TTSSDK = require('your-tts-sdk');
} catch (error) {
  logger.warn('TTS SDK not installed. Install with: npm install your-tts-sdk');
}

class YourTTSAdapter {
  /**
   * Synthesize text to speech
   * 
   * @param {string} text - Text to synthesize
   * @param {Object} config - Configuration
   * @returns {Promise<Buffer>} - PCM audio buffer
   */
  static async synthesize(text, config) {
    if (!TTSSDK) {
      throw new Error('TTS SDK not installed');
    }

    try {
      const client = new TTSSDK(config.apiKey);
      
      const audio = await client.synthesize({
        text: text,
        voice: config.voiceId,
        // ... other config
      });
      
      // Convert to PCM buffer if needed
      return Buffer.from(audio);
    } catch (error) {
      logger.error('Synthesis error:', error.message);
      throw error;
    }
  }

  /**
   * Stream synthesis
   * 
   * @param {string} text - Text to synthesize
   * @param {Object} config - Configuration
   * @yields {Buffer} - Audio chunks
   */
  static async *stream(text, config) {
    if (!TTSSDK) {
      throw new Error('TTS SDK not installed');
    }

    try {
      const client = new TTSSDK(config.apiKey);
      
      const stream = await client.synthesizeStream({
        text: text,
        voice: config.voiceId
      });
      
      for await (const chunk of stream) {
        yield chunk;
      }
    } catch (error) {
      logger.error('Stream error:', error.message);
      throw error;
    }
  }

  /**
   * Get available voices (optional)
   * 
   * @param {Object} config - Configuration
   * @returns {Promise<Array>} - Available voices
   */
  static async getVoices(config) {
    if (!TTSSDK) {
      return [];
    }

    try {
      const client = new TTSSDK(config.apiKey);
      const voices = await client.getVoices();
      
      return voices.map(v => ({
        id: v.id,
        name: v.name,
        description: v.description
      }));
    } catch (error) {
      logger.error('Get voices error:', error.message);
      return [];
    }
  }
}

module.exports = YourTTSAdapter;
```

## Testing Adapters

```javascript
// Test STT
const STTService = require('../../services/sttService');
const stt = new STTService('your-provider');
const result = await stt.transcribe(audioBuffer);
console.log(result);

// Test LLM
const LLMService = require('../../services/llmService');
const llm = new LLMService('your-provider');
const response = await llm.generateResponse('Hello!');
console.log(response);

// Test TTS
const TTSService = require('../../services/ttsService');
const tts = new TTSService('your-provider');
const audio = await tts.synthesize('Hello world');
console.log(audio.length, 'bytes');
```

## Integration Steps

1. **Create adapter** in appropriate directory
2. **Add to config** in `config/ai-services.config.js`
3. **Register in service** (sttService.js, llmService.js, or ttsService.js)
4. **Test** with your bot
5. **Document** any special requirements

## Best Practices

- ✅ Handle SDK missing gracefully
- ✅ Use try-catch for errors
- ✅ Log appropriately
- ✅ Return consistent formats
- ✅ Support streaming when possible
- ✅ Document dependencies

## Need Help?

Check `examples/ai-voice-bot.js` for complete usage examples.

