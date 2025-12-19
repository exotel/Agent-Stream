const http = require('http');
const https = require('https');
const fs = require('fs');
const express = require('express');
const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');
const config = require('./config');
const Logger = require('./utils/logger');
const RequestLogger = require('./middleware/requestLogger');
const MessageHandler = require('./handlers/messageHandler');
const MessageSender = require('./handlers/messageSender');

const logger = new Logger('SERVER');

/**
 * Exotel WSS Server
 * Handles both unidirectional and bidirectional audio streaming
 */
class ExotelWSSServer {
  constructor(options = {}) {
    this.app = express();
    this.server = null;
    this.wss = null;
    this.connections = new Map();
    this.options = options;

    this.setupExpress();
  }

  /**
   * Setup Express routes
   */
  setupExpress() {
    this.app.use(express.json());

    // Request logging middleware
    if (config.logging.logHttpRequests) {
      this.app.use(RequestLogger.middleware());
    }

    // Health check endpoint
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'ok',
        uptime: process.uptime(),
        connections: this.connections.size,
        timestamp: new Date().toISOString()
      });
    });

    // Dynamic WSS endpoint (returns WSS URL for Exotel)
    this.app.get('/get-websocket-url', (req, res) => {
      const { 'sample-rate': sampleRate, ...customParams } = req.query;

      // Build WebSocket URL
      const protocol = config.ssl.enabled ? 'wss' : 'ws';
      const host = req.get('host');
      let wsUrl = `${protocol}://${host}${config.server.wsPath}`;

      // Add sample rate if provided
      const params = [];
      if (sampleRate) {
        params.push(`sample-rate=${sampleRate}`);
      }

      // Add custom parameters
      Object.keys(customParams).forEach(key => {
        params.push(`${key}=${customParams[key]}`);
      });

      if (params.length > 0) {
        wsUrl += `?${params.join('&')}`;
      }

      logger.info(`Generated dynamic WebSocket URL: ${wsUrl}`);
      res.json({ url: wsUrl });
    });

    // Connection info endpoint
    this.app.get('/connections', (req, res) => {
      const connections = Array.from(this.connections.values()).map(conn => ({
        streamId: conn.streamId,
        stats: conn.handler.getStats(),
        senderStats: conn.sender?.getStats()
      }));

      res.json({
        total: connections.length,
        connections
      });
    });
  }

  /**
   * Authenticate WebSocket connection
   */
  authenticate(req) {
    if (!config.auth.enabled) {
      return true;
    }

    const auth = req.headers['authorization'];
    if (!auth || !auth.startsWith('Basic ')) {
      logger.warn('Missing or invalid authorization header');
      return false;
    }

    try {
      const credentials = Buffer.from(auth.slice(6), 'base64').toString();
      const [apiKey, apiToken] = credentials.split(':');

      if (apiKey === config.auth.apiKey && apiToken === config.auth.apiToken) {
        return true;
      }

      logger.warn('Invalid credentials');
      return false;
    } catch (error) {
      logger.error('Authentication error:', error.message);
      return false;
    }
  }

  /**
   * Setup WebSocket server
   */
  setupWebSocket() {
    this.wss = new WebSocket.Server({
      server: this.server,
      path: config.server.wsPath
    });

    // ═══════════════════════════════════════════════════════
    // Keepalive Interval - Ping all clients every 30 seconds
    // Prevents Exotel session timeouts on long calls
    // ═══════════════════════════════════════════════════════
    this.keepaliveInterval = setInterval(() => {
      this.wss.clients.forEach((ws) => {
        if (ws.isAlive === false) {
          logger.debug('Terminating inactive WebSocket connection');
          return ws.terminate();
        }
        ws.isAlive = false;
        ws.ping();
      });
    }, 30000); // Ping every 30 seconds

    this.wss.on('close', () => {
      clearInterval(this.keepaliveInterval);
    });

    this.wss.on('connection', (ws, req) => {
      const streamId = uuidv4();
      const clientIp = req.socket.remoteAddress;
      const userAgent = req.headers['user-agent'];

      logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      logger.info('🔌 New WebSocket Connection');
      logger.info(`   Stream ID: ${streamId}`);
      logger.info(`   Client IP: ${clientIp}`);
      logger.info(`   User Agent: ${userAgent || 'N/A'}`);

      // Authenticate if enabled
      const authenticated = this.authenticate(req);
      if (!authenticated) {
        logger.warn(`❌ Unauthorized connection attempt from ${clientIp}`);
        ws.close(1008, 'Unauthorized');
        return;
      }
      logger.info('   Auth: ✓ Authenticated');

      // Parse query parameters
      const url = new URL(req.url, `http://${req.headers.host}`);
      const sampleRate = url.searchParams.get('sample-rate');
      const customParams = {};
      url.searchParams.forEach((value, key) => {
        if (key !== 'sample-rate') {
          customParams[key] = value;
        }
      });

      const parsedSampleRate = sampleRate ? parseInt(sampleRate) : config.audio.defaultSampleRate;
      logger.info(`   Sample Rate: ${parsedSampleRate} Hz`);

      if (Object.keys(customParams).length > 0) {
        logger.info('   Custom Params:', customParams);
      }
      logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

      // Create message handler and sender
      const handler = new MessageHandler(streamId);
      const sender = new MessageSender(ws, streamId, handler.eventLogger);

      // Log connection event
      handler.eventLogger.logConnection({
        clientIp,
        userAgent,
        sampleRate: parsedSampleRate,
        customParams,
        authenticated
      });

      // Get message callbacks ONCE per connection (not per message!)
      const callbacks = this.getMessageCallbacks(streamId, ws, sender);

      // Store connection info
      this.connections.set(streamId, {
        streamId,
        ws,
        handler,
        sender,
        clientIp,
        userAgent,
        sampleRate: parsedSampleRate,
        customParams,
        connectedAt: new Date(),
        callbacks, // Store callbacks in connection
        isAlive: true
      });

      // ═══════════════════════════════════════════════════════
      // WebSocket Keepalive (Ping/Pong) - Prevents session timeout
      // Exotel sessions can timeout after inactivity
      // ═══════════════════════════════════════════════════════
      ws.isAlive = true;
      ws.on('pong', () => {
        ws.isAlive = true;
        const conn = this.connections.get(streamId);
        if (conn) conn.isAlive = true;
      });

      // Handle incoming messages
      ws.on('message', (message) => {
        handler.handleMessage(ws, message.toString(), callbacks);
      });

      // Handle connection close
      ws.on('close', (code, reason) => {
        const conn = this.connections.get(streamId);
        const duration = conn ? Date.now() - conn.connectedAt.getTime() : 0;

        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        logger.info('🔌 WebSocket Connection Closed');
        logger.info(`   Stream ID: ${streamId}`);
        logger.info(`   Close Code: ${code}`);
        logger.info(`   Reason: ${reason || 'No reason provided'}`);
        logger.info(`   Duration: ${(duration / 1000).toFixed(2)}s`);
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

        // Log disconnection event
        if (handler.eventLogger) {
          handler.eventLogger.logDisconnection(code, reason);
        }

        this.connections.delete(streamId);
      });

      // Handle errors
      ws.on('error', (error) => {
        logger.error(`❌ WebSocket error for stream ${streamId}:`, error.message);

        // Log error event
        if (handler.eventLogger) {
          handler.eventLogger.logError(error, { streamId, clientIp });
        }
      });
    });

    logger.info(`WebSocket server listening on path: ${config.server.wsPath}`);
  }

  /**
   * Get message callbacks for handling Exotel events
   * Override this method in your implementation to customize behavior
   */
  getMessageCallbacks(streamId, ws, sender) {
    return {
      onStart: (streamInfo) => {
        logger.info(`Stream ${streamId} started`);
        // Override in your implementation
      },

      onMedia: (mediaData) => {
        // Override in your implementation for custom audio processing
        // Example: echo back the audio for bidirectional streaming
        // sender.sendMedia(mediaData.audioBuffer, mediaData.timestamp);
      },

      onDTMF: (dtmfData) => {
        logger.info(`DTMF received on stream ${streamId}: ${dtmfData.digit}`);
        // Override in your implementation
      },

      onStop: (stopData) => {
        logger.info(`Stream ${streamId} stopped: ${stopData.reason}`);
        // Override in your implementation
      },

      onMark: (markData) => {
        logger.debug(`Mark received on stream ${streamId}: ${markData.name}`);
        // Override in your implementation
      }
    };
  }

  /**
   * Start the server
   */
  start() {
    return new Promise((resolve, reject) => {
      try {
        // Create HTTP or HTTPS server
        if (config.ssl.enabled) {
          if (!config.ssl.certPath || !config.ssl.keyPath) {
            throw new Error('SSL enabled but certificate paths not provided');
          }

          const credentials = {
            cert: fs.readFileSync(config.ssl.certPath),
            key: fs.readFileSync(config.ssl.keyPath)
          };

          this.server = https.createServer(credentials, this.app);
          logger.info('Using HTTPS/WSS (secure)');
        } else {
          this.server = http.createServer(this.app);
          logger.info('Using HTTP/WS (non-secure)');
        }

        // Setup WebSocket
        this.setupWebSocket();

        // Start listening
        this.server.listen(config.server.port, config.server.host, () => {
          const protocol = config.ssl.enabled ? 'https' : 'http';
          const wsProtocol = config.ssl.enabled ? 'wss' : 'ws';

          logger.info('═══════════════════════════════════════════════════════');
          logger.info('🚀 Exotel WSS Server started successfully!');
          logger.info('═══════════════════════════════════════════════════════');
          logger.info(`📡 HTTP Server: ${protocol}://${config.server.host}:${config.server.port}`);
          logger.info(`🔌 WebSocket: ${wsProtocol}://${config.server.host}:${config.server.port}${config.server.wsPath}`);
          logger.info(`🏥 Health Check: ${protocol}://${config.server.host}:${config.server.port}/health`);
          logger.info(`🔗 Dynamic URL: ${protocol}://${config.server.host}:${config.server.port}/get-websocket-url`);
          logger.info('═══════════════════════════════════════════════════════');

          resolve();
        });

        this.server.on('error', (error) => {
          logger.error('Server error:', error.message);
          reject(error);
        });

      } catch (error) {
        logger.error('Failed to start server:', error.message);
        reject(error);
      }
    });
  }

  /**
   * Stop the server
   */
  stop() {
    return new Promise((resolve) => {
      logger.info('Shutting down server...');

      // Close all WebSocket connections
      this.connections.forEach((conn, streamId) => {
        logger.info(`Closing connection: ${streamId}`);
        conn.ws.close(1001, 'Server shutting down');
      });

      // Close WebSocket server
      if (this.wss) {
        this.wss.close(() => {
          logger.info('WebSocket server closed');
        });
      }

      // Close HTTP server
      if (this.server) {
        this.server.close(() => {
          logger.info('HTTP server closed');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}

// Start server if run directly
if (require.main === module) {
  const server = new ExotelWSSServer();

  server.start().catch((error) => {
    logger.error('Failed to start server:', error);
    process.exit(1);
  });

  // Graceful shutdown
  const shutdown = async () => {
    logger.info('Received shutdown signal');
    await server.stop();
    process.exit(0);
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

module.exports = ExotelWSSServer;

