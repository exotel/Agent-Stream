require('dotenv').config();
const http = require('http');
const WebSocket = require('ws');
const { connectGemini } = require('./gemini-client');
const { resampleForGemini, resampleForExotel, chunkForExotel } = require('./audio');

const PORT = parseInt(process.env.PORT || '4041', 10);
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const WSS_PATH_PREFIX = '/sales-agent/exotel/ws/audio/';

const connections = new Map();

function getPathMatch(url) {
  const path = url.split('?')[0];
  if (!path.startsWith(WSS_PATH_PREFIX)) return null;
  const rest = path.slice(WSS_PATH_PREFIX.length);
  const parts = rest.split('/');
  if (parts.length < 2) return null;
  return { runId: parts[0], name: parts[1] };
}

function createHttpServer() {
  return http.createServer((req, res) => {
    if (req.url === '/health' || req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok', wss: `wss://<host>:${PORT}${WSS_PATH_PREFIX}<run_id>/<name>?sample-rate=16000` }));
      return;
    }
    res.writeHead(404);
    res.end();
  });
}

function run() {
  if (!GEMINI_API_KEY) {
    console.error('Set GEMINI_API_KEY in .env');
    process.exit(1);
  }

  const server = createHttpServer();
  const wss = new WebSocket.Server({ noServer: true });

  server.on('upgrade', (request, socket, head) => {
    const match = getPathMatch(request.url);
    if (!match) {
      socket.destroy();
      return;
    }
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request, match);
    });
  });

  wss.on('connection', (exotelWs, request, { runId, name }) => {
    const streamSid = `node-${runId}-${Date.now()}`;
    const urlParams = new URL(request.url || '', 'http://localhost').searchParams;
    const exotelRate = parseInt(urlParams.get('sample-rate') || '8000', 10) || 8000;

    let geminiClient = null;
    let exotelSeq = 1;
    let exotelChunk = 1;
    let outBuffer = Buffer.alloc(0);
    let dropUntil = 0;
    let startTime = Date.now();

    const sendToExotel = (event, payload) => {
      if (exotelWs.readyState !== WebSocket.OPEN) return;
      exotelWs.send(JSON.stringify({ event, stream_sid: streamSid, sequence_number: String(exotelSeq++), ...payload }));
    };

    const sendMediaToExotel = (pcmBase64) => {
      if (exotelWs.readyState !== WebSocket.OPEN) return;
      const ts = Math.max(0, Date.now() - startTime);
      sendToExotel('media', {
        media: { payload: pcmBase64, timestamp: String(ts), chunk: String(exotelChunk++) },
      });
      sendToExotel('mark', { mark: { name: 'playback_chunk', timestamp: String(ts) } });
    };

    const sendClearToExotel = () => {
      sendToExotel('clear', {});
    };

    geminiClient = connectGemini(GEMINI_API_KEY, {
      onOpen: () => console.log('[Gemini] Connected for', streamSid),
      onSetupComplete: () => console.log('[Gemini] Setup complete, greeting sent for', streamSid),
      onInterrupted: () => {
        dropUntil = Date.now() + 800;
        outBuffer = Buffer.alloc(0);
        sendClearToExotel();
      },
      onAudio: (base64Audio) => {
        if (Date.now() < dropUntil) return;
        const pcm24 = Buffer.from(base64Audio, 'base64');
        const pcm = resampleForExotel(pcm24, exotelRate);
        outBuffer = Buffer.concat([outBuffer, pcm]);
        const { chunks, remainder } = chunkForExotel(outBuffer);
        outBuffer = remainder;
        for (const chunk of chunks) {
          sendMediaToExotel(chunk.toString('base64'));
        }
      },
      onError: (e) => console.error('[Gemini] Error', streamSid, e.message),
      onClose: () => {},
    });

    connections.set(streamSid, { exotelWs, geminiClient });

    let inboundBuffer = Buffer.alloc(0);
    const GEMINI_CHUNK = 640;
    let lastFlushAt = 0;
    const FLUSH_INTERVAL_MS = 1200;

    const maybeFlushInbound = () => {
      if (inboundBuffer.length < GEMINI_CHUNK || !geminiClient) return;
      const now = Date.now();
      if (now - lastFlushAt < FLUSH_INTERVAL_MS) return;
      lastFlushAt = now;
      const toSend = inboundBuffer.subarray(0, inboundBuffer.length);
      inboundBuffer = Buffer.alloc(0);
      geminiClient.sendAudio(toSend.toString('base64'));
    };

    exotelWs.on('message', (raw) => {
      try {
        const data = JSON.parse(raw.toString());
        const event = data.event;

        if (event === 'connected') {
          console.log('[Exotel] Connected', streamSid);
          return;
        }
        if (event === 'start') {
          console.log('[Exotel] Start', streamSid, exotelRate);
          startTime = data.start ? Date.now() : startTime;
          return;
        }
        if (event === 'clear' || (event === 'mark' && (data.mark?.name === 'clear' || data.mark?.name === 'interrupt'))) {
          dropUntil = Date.now() + 1000;
          outBuffer = Buffer.alloc(0);
          sendClearToExotel();
          if (inboundBuffer.length > 0 && geminiClient) {
            const toSend = resampleForGemini(inboundBuffer, exotelRate);
            geminiClient.sendAudio(toSend.toString('base64'));
          }
          inboundBuffer = Buffer.alloc(0);
          return;
        }
        if (event === 'stop') {
          geminiClient?.close();
          connections.delete(streamSid);
          return;
        }
        if (event === 'media' && data.media?.payload) {
          const pcm = Buffer.from(data.media.payload, 'base64');
          inboundBuffer = Buffer.concat([inboundBuffer, resampleForGemini(pcm, exotelRate)]);
          while (inboundBuffer.length >= GEMINI_CHUNK) {
            const chunk = inboundBuffer.subarray(0, GEMINI_CHUNK);
            inboundBuffer = inboundBuffer.subarray(GEMINI_CHUNK);
            geminiClient?.sendAudio(chunk.toString('base64'));
          }
          maybeFlushInbound();
        }
      } catch (e) {
        console.error('[Exotel] Message error', e.message);
      }
    });

    exotelWs.on('close', () => {
      geminiClient?.close();
      connections.delete(streamSid);
    });
    exotelWs.on('error', () => {
      geminiClient?.close();
      connections.delete(streamSid);
    });
  });

  server.listen(PORT, '0.0.0.0', () => {
    console.log(`Exotel ↔ Gemini bridge (Node) on http://0.0.0.0:${PORT}`);
    console.log(`WSS: ws://localhost:${PORT}${WSS_PATH_PREFIX}<run_id>/<name>?sample-rate=16000`);
  });
}

run();
