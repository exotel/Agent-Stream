/**
 * ElevenLabs Conversational AI Bridge Bot
 *
 * Bridges Exotel WebSocket with ElevenLabs Conversational AI Agent
 * Transforms events between the two different protocols
 *
 * Audio Format Handling (per Exotel docs):
 * - Exotel sends: raw/slin 16-bit PCM 8kHz mono (little-endian), base64 encoded
 * - ElevenLabs expects: pcm_16000 (16-bit PCM 16kHz)
 * - Bridge resamples: 8kHz ↔ 16kHz both directions
 *
 * Reference: https://elevenlabs.io/docs/conversational-ai/api-reference/websocket
 */

const ExotelWSSServer = require('../src/core/server');
const Logger = require('../src/core/utils/logger');
const AudioResampler = require('../src/core/utils/audioResampler');
const { SessionState, AudioUtils, BargeInHandler, EXOTEL_CONSTANTS } = require('../src/core/utils/botUtils');
const WebSocket = require('ws');

const logger = new Logger('ELEVENLABS-BRIDGE');

// Audio format constants
const AUDIO_FORMAT = {
  EXOTEL_SAMPLE_RATE: 8000,       // Exotel uses 8kHz
  ELEVENLABS_SAMPLE_RATE: 16000,  // ElevenLabs uses 16kHz
  ELEVENLABS_FORMAT: 'pcm_16000'  // 16-bit PCM 16kHz for ElevenLabs
};

class ElevenLabsConversationalBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();
    this.apiKey = process.env.ELEVENLABS_API_KEY;
    this.agentId = process.env.ELEVENLABS_AGENT_ID;

    if (!this.apiKey) {
      logger.error('═══════════════════════════════════════════════════════');
      logger.error('❌ ELEVENLABS_API_KEY not configured!');
      logger.error('');
      logger.error('Add to your .env file:');
      logger.error('  ELEVENLABS_API_KEY=your_api_key_here');
      logger.error('');
      logger.error('Get your API key from: https://elevenlabs.io/app/settings/api-keys');
      logger.error('═══════════════════════════════════════════════════════');
      process.exit(1);
    }

    if (!this.agentId) {
      logger.error('═══════════════════════════════════════════════════════');
      logger.error('❌ ELEVENLABS_AGENT_ID not configured!');
      logger.error('');
      logger.error('Add to your .env file:');
      logger.error('  ELEVENLABS_AGENT_ID=your_agent_id_here');
      logger.error('');
      logger.error('Create an agent at: https://elevenlabs.io/app/conversational-ai');
      logger.error('Then copy the Agent ID from the agent settings');
      logger.error('═══════════════════════════════════════════════════════');
      process.exit(1);
    }

    logger.info(`✓ API Key configured (${this.apiKey.substring(0, 8)}...)`);
    logger.info(`✓ Agent ID: ${this.agentId}`);
  }

  /**
   * Initialize session for a new call
   */
  initializeSession(streamId) {
    const sampleRate = this.connections.get(streamId)?.sampleRate || 8000;

    return {
      streamId,
      sampleRate,
      elevenLabsWs: null,
      connected: false,
      conversationId: null,
      lastActivity: Date.now(),
      // State tracking for interruption handling
      agentSpeaking: false,        // Is agent currently outputting audio?
      interrupted: false,          // Was the agent interrupted?
      audioChunks: 0,              // Count of audio chunks sent to ElevenLabs
      responseChunks: 0,           // Count of response chunks sent to Exotel
      // Audio buffer - reduced to 640 bytes (20ms) for lower latency
      // Trade-off: More network packets but faster response
      audioBuffer: Buffer.alloc(0),
      MIN_CHUNK_SIZE: 640,         // 20ms at 8kHz, 16-bit (2 frames of 320 bytes)
      // Custom parameters from Exotel (passed to ElevenLabs)
      customParams: {}
    };
  }

  /**
   * Connect to ElevenLabs Conversational AI
   */
  connectToElevenLabs(session) {
    return new Promise((resolve, reject) => {
      // ElevenLabs WebSocket endpoint
      const wsUrl = `wss://api.elevenlabs.io/v1/convai/conversation?agent_id=${this.agentId}`;

      logger.info(`🔌 Connecting to ElevenLabs Agent: ${this.agentId}`);
      logger.info(`   Exotel format: 16-bit PCM ${AUDIO_FORMAT.EXOTEL_SAMPLE_RATE}Hz`);
      logger.info(`   ElevenLabs format: ${AUDIO_FORMAT.ELEVENLABS_FORMAT}`);
      logger.info(`   Bridge will resample: ${AUDIO_FORMAT.EXOTEL_SAMPLE_RATE}Hz ↔ ${AUDIO_FORMAT.ELEVENLABS_SAMPLE_RATE}Hz`);

      const ws = new WebSocket(wsUrl, {
        headers: {
          'xi-api-key': this.apiKey
        }
      });

      ws.on('open', () => {
        logger.info('✅ Connected to ElevenLabs Conversational AI');
        session.connected = true;

        // Build initialization message with custom parameters
        const initMessage = {
          type: 'conversation_initiation_client_data',
          conversation_config_override: {
            agent: {
              language: 'en'
            },
            tts: {
              // Request PCM 16kHz output - we'll resample to 8kHz for Exotel
              output_format: AUDIO_FORMAT.ELEVENLABS_FORMAT
            }
          }
        };

        // Pass custom parameters from Exotel to ElevenLabs as dynamic variables
        // These can be used in the agent's prompt with {{variable_name}} syntax
        if (session.customParams && Object.keys(session.customParams).length > 0) {
          initMessage.dynamic_variables = session.customParams;
          logger.info(`📦 Passing custom params to ElevenLabs: ${JSON.stringify(session.customParams)}`);
        }

        ws.send(JSON.stringify(initMessage));
        logger.debug('→ Sent conversation initialization');
        logger.debug(`   Output format: ${AUDIO_FORMAT.ELEVENLABS_FORMAT}`);

        resolve();
      });

      ws.on('message', (data) => {
        this.handleElevenLabsMessage(session, data);
      });

      ws.on('error', (error) => {
        logger.error('❌ ElevenLabs WebSocket error:', error.message);
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
          logger.error('   Check your ELEVENLABS_API_KEY is valid');
        }
        if (error.message.includes('404') || error.message.includes('agent')) {
          logger.error('   Check your ELEVENLABS_AGENT_ID exists');
        }
        reject(error);
      });

      ws.on('close', (code, reason) => {
        logger.info(`🔌 ElevenLabs WebSocket closed (code: ${code})`);
        if (reason) {
          logger.debug(`   Reason: ${reason}`);
        }
        session.connected = false;
      });

      session.elevenLabsWs = ws;
    });
  }

  /**
   * BRIDGE: Transform Exotel event to ElevenLabs format
   */
  exotelToElevenLabs(exotelEvent) {
    // Transform Exotel media event to ElevenLabs user_audio_chunk
    if (exotelEvent.event === 'media' && exotelEvent.media) {
      return {
        user_audio_chunk: exotelEvent.media.payload
      };
    }

    return null;
  }

  /**
   * BRIDGE: Transform ElevenLabs event to Exotel format
   */
  elevenLabsToExotel(elevenLabsEvent) {
    const event = JSON.parse(elevenLabsEvent.toString());

    // Transform ElevenLabs audio to Exotel media
    if (event.type === 'audio' && event.audio_event) {
      return {
        event: 'media',
        media: {
          payload: event.audio_event.audio_base_64
        }
      };
    }

    return null;
  }

  /**
   * Handle messages from ElevenLabs
   */
  handleElevenLabsMessage(session, data) {
    try {
      const event = JSON.parse(data.toString());

      logger.debug(`← ElevenLabs event: ${event.type}`);

      switch (event.type) {
        case 'conversation_initiation_metadata':
          // Store conversation metadata
          const metadata = event.conversation_initiation_metadata_event;
          session.conversationId = metadata.conversation_id;
          logger.info(`📋 Conversation ID: ${session.conversationId}`);
          logger.info(`🎤 Input format: ${metadata.user_input_audio_format}`);
          logger.info(`🔊 Output format: ${metadata.agent_output_audio_format}`);
          break;

        case 'user_transcript':
          // User speech was transcribed
          const userText = event.user_transcription_event.user_transcript;
          // Track when user finished speaking for latency measurement
          session.userSpeechEndTime = Date.now();
          logger.info(`👤 User: "${userText}"`);
          break;

        case 'agent_response':
          // Agent's text response - agent is about to speak
          session.agentSpeaking = true;
          session.interrupted = false;
          const agentText = event.agent_response_event.agent_response;

          // Calculate latency from user speech end to agent response
          if (session.userSpeechEndTime) {
            const latency = Date.now() - session.userSpeechEndTime;
            logger.info(`⏱️  Response latency: ${latency}ms`);
          }
          session.agentResponseTime = Date.now();

          logger.info(`🤖 Agent: "${agentText}"`);
          break;

        case 'audio':
          // Agent's audio response - send to Exotel
          // Don't send if we've been interrupted
          if (!session.interrupted) {
            this.forwardAudioToExotel(session, event);
          } else {
            logger.debug('⏸️  Skipping audio (interrupted)');
          }
          break;

        case 'agent_response_correction':
          // Agent response was corrected (interrupted mid-sentence)
          logger.info('📝 Agent response corrected');
          break;

        case 'interruption':
          // User interrupted agent - THIS IS CRITICAL FOR BARGE-IN
          logger.info('⚠️  USER INTERRUPTED! Clearing Exotel audio buffer');
          session.interrupted = true;
          session.agentSpeaking = false;

          // Clear our internal audio buffer
          session.audioBuffer = Buffer.alloc(0);

          // Send CLEAR to Exotel to stop playing pending audio
          this.sendClearToExotel(session);
          break;

        case 'user_started_speaking':
          // User started speaking (may lead to interruption)
          logger.debug('🎤 User started speaking');
          break;

        case 'agent_audio_done':
          // Agent finished sending audio
          session.agentSpeaking = false;
          logger.debug('🔊 Agent audio complete');

          // Flush any remaining buffered audio
          this.flushAudioBuffer(session);

          // Send mark to Exotel to track when audio finishes playing
          this.sendMarkToExotel(session, 'agent_response_complete');
          break;

        case 'ping':
          // Respond to ping with pong
          this.sendPong(session, event.ping_event.event_id);
          break;

        case 'error':
          // Handle errors from ElevenLabs
          const errorMsg = event.error?.message || event.message || 'Unknown error';
          const errorCode = event.error?.code || event.code || 'UNKNOWN';
          logger.error(`❌ ElevenLabs error: [${errorCode}] ${errorMsg}`);
          break;

        case 'client_tool_call':
          // ElevenLabs agent is requesting a tool/function call
          // This is for advanced integrations (e.g., booking, lookups)
          logger.info(`🔧 Tool call requested: ${event.client_tool_call?.tool_name || 'unknown'}`);
          // TODO: Implement tool handling if needed
          // For now, send empty result to continue conversation
          this.sendToolResult(session, event.client_tool_call?.tool_call_id, {});
          break;

        case 'internal_vad_score':
        case 'internal_turn_probability':
        case 'internal_tentative_agent_response':
          // Internal debug events - ignore silently
          break;

        default:
          logger.debug(`Unhandled ElevenLabs event: ${event.type}`);
      }
    } catch (error) {
      logger.error('Error handling ElevenLabs message:', error.message);
    }
  }

  /**
   * Send tool result back to ElevenLabs (for function calling)
   */
  sendToolResult(session, toolCallId, result) {
    if (!session.elevenLabsWs || !session.connected) return;

    const message = {
      type: 'client_tool_result',
      tool_call_id: toolCallId,
      result: JSON.stringify(result),
      is_error: false
    };

    session.elevenLabsWs.send(JSON.stringify(message));
    logger.debug(`→ Sent tool result for ${toolCallId}`);
  }

  /**
   * Send CLEAR event to Exotel to stop audio playback
   * This enables barge-in (user can interrupt the agent)
   */
  sendClearToExotel(session) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender) {
      logger.warn('No sender available for clear event');
      return;
    }

    try {
      sender.sendClear();
      logger.info('🧹 Sent CLEAR to Exotel - audio buffer cleared');
    } catch (error) {
      logger.error('Error sending clear to Exotel:', error.message);
    }
  }

  /**
   * Send MARK event to Exotel to track audio playback
   * Exotel will send back a mark event when the audio is played
   */
  sendMarkToExotel(session, markName) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender) {
      logger.warn('No sender available for mark event');
      return;
    }

    try {
      sender.sendMark(markName);
      logger.debug(`📍 Sent MARK to Exotel: ${markName}`);
    } catch (error) {
      logger.error('Error sending mark to Exotel:', error.message);
    }
  }

  /**
   * Forward audio from ElevenLabs to Exotel
   * Resamples from 16kHz (ElevenLabs) to 8kHz (Exotel)
   * Buffers audio to meet Exotel's minimum chunk size requirement
   */
  forwardAudioToExotel(session, audioEvent) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender) {
      logger.warn('No sender available for audio forwarding');
      return;
    }

    try {
      // Check if interrupted before processing
      if (session.interrupted) {
        // Clear any buffered audio
        session.audioBuffer = Buffer.alloc(0);
        logger.debug('⏸️  Skipping audio forward (interrupted)');
        return;
      }

      // Get base64 audio from ElevenLabs (16-bit PCM 16kHz)
      const audioBase64 = audioEvent.audio_event.audio_base_64;

      // Convert base64 to buffer
      const elevenLabsBuffer = Buffer.from(audioBase64, 'base64');

      // Resample from 16kHz to 8kHz for Exotel
      const resampledBuffer = AudioResampler.resample(
        elevenLabsBuffer,
        AUDIO_FORMAT.ELEVENLABS_SAMPLE_RATE,
        AUDIO_FORMAT.EXOTEL_SAMPLE_RATE
      );

      // Accumulate in buffer
      session.audioBuffer = Buffer.concat([session.audioBuffer, resampledBuffer]);

      // Send chunks when we have enough data
      // Using smaller chunks (640 bytes = 20ms) for lower latency
      // Trade-off: More packets but faster response time
      const CHUNK_SIZE = session.MIN_CHUNK_SIZE || 640;

      while (session.audioBuffer.length >= CHUNK_SIZE) {
        // Check if interrupted during sending
        if (session.interrupted) {
          session.audioBuffer = Buffer.alloc(0);
          logger.debug('⏸️  Clearing audio buffer (interrupted)');
          break;
        }

        // Extract chunk
        const chunk = session.audioBuffer.slice(0, CHUNK_SIZE);
        session.audioBuffer = session.audioBuffer.slice(CHUNK_SIZE);

        // Send to Exotel with skipValidation=true for low-latency streaming
        sender.sendMedia(chunk, null, true);

        session.responseChunks = (session.responseChunks || 0) + 1;
      }

      // Log periodically
      if (session.responseChunks % 20 === 0 && session.responseChunks > 0) {
        logger.debug(`← Forwarded ${session.responseChunks} response chunks to Exotel`);
      }
    } catch (error) {
      logger.error('Error forwarding audio:', error.message);
    }
  }

  /**
   * Flush any remaining audio in the buffer to Exotel
   * Called when agent finishes speaking
   */
  flushAudioBuffer(session) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender || session.interrupted) {
      session.audioBuffer = Buffer.alloc(0);
      return;
    }

    // Send remaining audio if it's at least 320 bytes (one frame)
    if (session.audioBuffer.length >= 320) {
      // Pad to multiple of 320 bytes
      const paddedLength = Math.ceil(session.audioBuffer.length / 320) * 320;
      const paddedBuffer = Buffer.alloc(paddedLength);
      session.audioBuffer.copy(paddedBuffer);
      sender.sendMedia(paddedBuffer, null, true);  // Skip validation for low-latency
      logger.debug(`← Flushed remaining ${session.audioBuffer.length} bytes to Exotel`);
    }

    session.audioBuffer = Buffer.alloc(0);
  }

  /**
   * Send pong response to ElevenLabs
   */
  sendPong(session, eventId) {
    if (!session.elevenLabsWs || !session.connected) return;

    const pong = {
      type: 'pong',
      event_id: eventId
    };

    session.elevenLabsWs.send(JSON.stringify(pong));
    logger.debug(`→ Sent pong for event ${eventId}`);
  }

  /**
   * Get message callbacks for Exotel events
   */
  getMessageCallbacks(streamId, ws, sender) {
    const session = this.initializeSession(streamId);
    this.sessions.set(streamId, session);

    return {
      /**
       * Handle call start - connect to ElevenLabs
       */
      onStart: async (streamInfo) => {
        logger.info('═══════════════════════════════════════════════════════');
        logger.info('📞 Call started');
        logger.info(`   Stream ID: ${streamId.substring(0, 16)}...`);
        logger.info(`   Call SID: ${streamInfo.call_sid || 'N/A'}`);
        logger.info(`   From: ${streamInfo.from || 'N/A'}`);
        logger.info(`   To: ${streamInfo.to || 'N/A'}`);
        logger.info(`   Sample Rate: ${streamInfo.media_format?.sample_rate || 8000}Hz`);

        // Capture custom parameters from Exotel
        if (streamInfo.custom_parameters) {
          session.customParams = streamInfo.custom_parameters;
          logger.info(`   Custom Params: ${JSON.stringify(session.customParams)}`);
        }
        logger.info('═══════════════════════════════════════════════════════');

        try {
          // Connect to ElevenLabs Conversational AI with custom params
          await this.connectToElevenLabs(session);

          logger.info('🎙️  Bridge ready! Start speaking...');
        } catch (error) {
          logger.error('Failed to connect to ElevenLabs:', error.message);
        }
      },

      /**
       * Handle incoming audio from Exotel - resample and forward to ElevenLabs
       * This is the user's voice being sent to the AI
       */
      onMedia: (mediaData) => {
        if (!session.connected || !session.elevenLabsWs) {
          logger.warn('ElevenLabs not connected, dropping audio');
          return;
        }

        session.lastActivity = Date.now();

        try {
          // Exotel sends 16-bit PCM 8kHz as base64
          // ElevenLabs expects 16-bit PCM 16kHz

          // 1. Get the audio buffer (already decoded by messageHandler)
          const audioBuffer = mediaData.audioBuffer;

          // 2. Resample from 8kHz to 16kHz
          const resampledBuffer = AudioResampler.resample(
            audioBuffer,
            AUDIO_FORMAT.EXOTEL_SAMPLE_RATE,
            AUDIO_FORMAT.ELEVENLABS_SAMPLE_RATE
          );

          // 3. Encode back to base64 for ElevenLabs
          const base64Audio = resampledBuffer.toString('base64');

          // 4. Send to ElevenLabs
          const elevenLabsMessage = {
            user_audio_chunk: base64Audio
          };

          session.elevenLabsWs.send(JSON.stringify(elevenLabsMessage));

          // Log periodically
          session.audioChunks = (session.audioChunks || 0) + 1;
          if (session.audioChunks % 50 === 0) {
            logger.debug(`→ Forwarded ${session.audioChunks} audio chunks to ElevenLabs`);
          }

        } catch (error) {
          logger.error('Error forwarding audio to ElevenLabs:', error.message);
        }
      },

      /**
       * Handle DTMF - keypad presses from the caller
       */
      onDTMF: (dtmfData) => {
        logger.info(`📱 DTMF: ${dtmfData.digit}`);

        if (dtmfData.digit === '#') {
          logger.info('📞 Call ending (# pressed)');

          // Close ElevenLabs connection
          if (session.elevenLabsWs) {
            session.elevenLabsWs.close();
          }
        }

        // TODO: Could send DTMF info to ElevenLabs agent if needed
        // Some agents might want to handle numeric input
      },

      /**
       * Handle mark events from Exotel
       * Mark confirms that audio we sent has been played
       */
      onMark: (markData) => {
        logger.debug(`✓ Mark received: ${markData.name}`);

        // Mark indicates our audio finished playing
        // This can be used for conversation flow control
        if (markData.name === 'agent_response_complete') {
          session.agentSpeaking = false;
          logger.debug('🔊 Agent audio playback complete on Exotel');
        }
      },

      /**
       * Handle call end
       */
      onStop: (stopData) => {
        logger.info('═══════════════════════════════════════════════════════');
        logger.info('📞 Call ended');
        if (session.conversationId) {
          logger.info(`   Conversation: ${session.conversationId}`);
        }
        logger.info('═══════════════════════════════════════════════════════');

        // Close ElevenLabs connection
        if (session.elevenLabsWs) {
          session.elevenLabsWs.close();
        }

        // Cleanup
        this.sessions.delete(streamId);
      }
    };
  }
}

// Start server
const bot = new ElevenLabsConversationalBot();
const PORT = process.env.PORT || 5001;

bot.start(PORT);

logger.info('');
logger.info('═══════════════════════════════════════════════════════');
logger.info('🎙️  ElevenLabs Conversational AI Bridge Bot Ready!');
logger.info('═══════════════════════════════════════════════════════');
logger.info('');
logger.info('📞 How it works:');
logger.info('   ┌──────────┐      ┌─────────────┐      ┌────────────┐');
logger.info('   │  Exotel  │ ←──→ │ This Bridge │ ←──→ │ ElevenLabs │');
logger.info('   │  (Call)  │      │   Server    │      │   Agent    │');
logger.info('   └──────────┘      └─────────────┘      └────────────┘');
logger.info('      8kHz PCM         Resamples          16kHz PCM');
logger.info('');
logger.info('🔊 Audio Format Conversion:');
logger.info('   Exotel → Bridge: 16-bit PCM 8kHz (raw/slin)');
logger.info('   Bridge → ElevenLabs: 16-bit PCM 16kHz (pcm_16000)');
logger.info('   ElevenLabs → Bridge: 16-bit PCM 16kHz');
logger.info('   Bridge → Exotel: 16-bit PCM 8kHz');
logger.info('');
logger.info('⚡ Benefits:');
logger.info('   • Ultra-low latency (~1-2 sec vs 3-5 sec for separate services)');
logger.info('   • High quality ElevenLabs voices');
logger.info('   • Agent handles all AI processing (STT + LLM + TTS)');
logger.info('');
logger.info('═══════════════════════════════════════════════════════');
logger.info('Press Ctrl+C to stop');
logger.info('═══════════════════════════════════════════════════════');

