/**
 * Exotel API Utility
 *
 * Provides methods to interact with Exotel's REST API
 * for making calls, checking status, and managing voice bots.
 *
 * Reference: https://developer.exotel.com/api
 */

const https = require('https');
const Logger = require('./logger');

const logger = new Logger('EXOTEL-API');

class ExotelApi {
  /**
   * Initialize Exotel API client
   * @param {Object} config - Configuration object
   * @param {string} config.apiKey - Exotel API Key
   * @param {string} config.apiToken - Exotel API Token
   * @param {string} config.accountSid - Exotel Account SID
   * @param {string} config.subdomain - Exotel subdomain (default: api.exotel.com)
   */
  constructor(config = {}) {
    this.apiKey = config.apiKey || process.env.EXOTEL_API_KEY;
    this.apiToken = config.apiToken || process.env.EXOTEL_API_TOKEN;
    this.accountSid = config.accountSid || process.env.EXOTEL_ACCOUNT_SID;
    this.subdomain = config.subdomain || process.env.EXOTEL_SUBDOMAIN || 'api.exotel.com';

    if (!this.apiKey || !this.apiToken || !this.accountSid) {
      logger.warn('Exotel API credentials not fully configured');
    }
  }

  /**
   * Make a call using Exotel API
   * @param {Object} options - Call options
   * @param {string} options.from - Customer phone number (who receives the call)
   * @param {string} options.to - Virtual number (Exotel number)
   * @param {string} options.callerId - Caller ID to display
   * @param {string} options.flowUrl - URL of the call flow (ExoML)
   * @param {string} options.wssUrl - WebSocket URL for streaming (optional, included in flowUrl)
   * @param {Object} options.customParameters - Custom parameters to pass
   * @returns {Promise<Object>} Call details
   */
  async makeCall(options) {
    const { from, to, callerId, flowUrl, customParameters } = options;

    if (!from || !to || !callerId || !flowUrl) {
      throw new Error('Missing required parameters: from, to, callerId, flowUrl');
    }

    const postData = new URLSearchParams({
      From: from,
      To: to,
      CallerId: callerId,
      Url: flowUrl
    });

    // Add custom parameters if provided
    if (customParameters) {
      Object.entries(customParameters).forEach(([key, value]) => {
        postData.append(`CustomField[${key}]`, value);
      });
    }

    const requestOptions = {
      hostname: this.subdomain,
      port: 443,
      path: `/v1/Accounts/${this.accountSid}/Calls/connect.json`,
      method: 'POST',
      auth: `${this.apiKey}:${this.apiToken}`,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(postData.toString())
      }
    };

    return new Promise((resolve, reject) => {
      const req = https.request(requestOptions, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const response = JSON.parse(data);
            if (response.Call) {
              logger.info(`✅ Call initiated: ${response.Call.Sid}`);
              resolve(response.Call);
            } else if (response.RestException) {
              logger.error(`❌ Call failed: ${response.RestException.Message}`);
              reject(new Error(response.RestException.Message));
            } else {
              resolve(response);
            }
          } catch (e) {
            reject(new Error(`Failed to parse response: ${data}`));
          }
        });
      });

      req.on('error', reject);
      req.write(postData.toString());
      req.end();
    });
  }

  /**
   * Get call status
   * @param {string} callSid - Call SID
   * @returns {Promise<Object>} Call details
   */
  async getCallStatus(callSid) {
    const requestOptions = {
      hostname: this.subdomain,
      port: 443,
      path: `/v1/Accounts/${this.accountSid}/Calls/${callSid}.json`,
      method: 'GET',
      auth: `${this.apiKey}:${this.apiToken}`
    };

    return new Promise((resolve, reject) => {
      const req = https.request(requestOptions, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const response = JSON.parse(data);
            resolve(response.Call || response);
          } catch (e) {
            reject(new Error(`Failed to parse response: ${data}`));
          }
        });
      });

      req.on('error', reject);
      req.end();
    });
  }

  /**
   * Build flow URL with WSS parameter
   * @param {string} flowId - Exotel flow ID
   * @param {string} wssUrl - WebSocket URL for streaming
   * @returns {string} Complete flow URL
   */
  buildFlowUrl(flowId, wssUrl) {
    const encodedWss = encodeURIComponent(wssUrl);
    return `http://my.exotel.com/${this.accountSid}/exoml/start_voice/${flowId}?wss_url=${encodedWss}`;
  }

  /**
   * Quick helper to make a call with WebSocket streaming
   * @param {string} customerPhone - Customer phone number
   * @param {string} virtualNumber - Exotel virtual number
   * @param {string} flowId - Exotel flow ID
   * @param {string} wssUrl - WebSocket URL
   * @returns {Promise<Object>} Call details
   */
  async callWithStreaming(customerPhone, virtualNumber, flowId, wssUrl) {
    return this.makeCall({
      from: customerPhone,
      to: virtualNumber,
      callerId: virtualNumber,
      flowUrl: this.buildFlowUrl(flowId, wssUrl)
    });
  }
}

/**
 * Exotel Event Reference
 *
 * INCOMING EVENTS (Exotel → Bot):
 *
 * | Event     | When                    | Data                                  |
 * |-----------|-------------------------|---------------------------------------|
 * | connected | WebSocket established   | { event: 'connected' }                |
 * | start     | Call begins streaming   | { start: { call_sid, from, to, ... }} |
 * | media     | Audio chunk (every 40ms)| { media: { payload, timestamp }}      |
 * | dtmf      | Keypad press            | { dtmf: { digit, duration }}          |
 * | mark      | Audio playback event    | { mark: { name }}                     |
 * | stop      | Stream ends             | { stop: { reason }}                   |
 *
 * OUTGOING EVENTS (Bot → Exotel):
 *
 * | Event | Purpose                        | Data                              |
 * |-------|--------------------------------|-----------------------------------|
 * | media | Send audio to caller           | { media: { payload, timestamp }}  |
 * | mark  | Track playback position        | { mark: { name }}                 |
 * | clear | Stop audio, enable barge-in    | { event: 'clear' }                |
 *
 * AUDIO FORMAT:
 * - Encoding: Base64
 * - Format: 16-bit PCM
 * - Sample Rate: 8000 Hz
 * - Chunk Size: 320 bytes (40ms) min, 3200 bytes (200ms) recommended
 *
 * CLEAR EVENT:
 * - Send BEFORE new audio to stop current playback
 * - Enables barge-in (user interruption)
 * - Should be sent immediately when user starts speaking
 *
 * MARK EVENT:
 * - Use to track audio playback progress
 * - Exotel sends mark back when audio reaches that point
 * - Useful for timing and analytics
 */

module.exports = ExotelApi;

