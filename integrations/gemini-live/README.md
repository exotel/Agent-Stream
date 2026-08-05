# Exotel ↔ Gemini Live bridge (Node.js)

Exotel streams call audio over WebSocket; this server forwards it to **Google Gemini Live** and streams AI speech back.

**Catalog path:** `integrations/gemini-live/`

## Quick start

```bash
cd integrations/gemini-live
cp .env.example .env
# Edit .env: set GEMINI_API_KEY (from https://aistudio.google.com/apikey)
npm install
npm start
```

Server runs on **port 4041** by default. WSS path:

`ws://localhost:4041/sales-agent/exotel/ws/audio/<run_id>/<name>?sample-rate=16000`

- **Health:** `http://localhost:4041/health`

### Connect Voice AI test

```bash
python ../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/sales-agent/exotel/ws/audio/manual-test-run/TestUser?sample-rate=16000"
```

See [docs/CONNECT_VOICE_AI.md](../../docs/CONNECT_VOICE_AI.md).

## Will it work?

**We can’t guarantee it** until you run a real call. This Node version was built to mirror the Python bridge (same Exotel protocol, same Gemini Live flow). What *does* give confidence:

1. **Same protocol** – Exotel events (connected, start, media, mark, clear, stop), chunk sizes (3.2KB min, 320-byte align), and sending `clear` to Exotel on interrupt.
2. **Same flow** – Session config → setupComplete → greeting → audio in/out with resampling (8k/16k → 16k for Gemini; 24k → 8k/16k for Exotel).
3. **Your testing** – Use the same Exotel Voicebot Applet and number you use for the Python bridge; point the applet at `wss://<your-host>:4041/sales-agent/exotel/ws/audio/manual-test-run/TestUser?sample-rate=16000`. If you hear the greeting and can talk to the bot, it’s working.

**If something breaks:** Compare with the Python bridge (same Exotel + Gemini). Check server logs; the Python 10_MINUTE_GUIDE troubleshooting (logs to check, flush, VAD) still applies conceptually. This Node version is **lighter** (no VAD/flush logic yet); if the bot doesn’t answer after the greeting, we can add a minimal flush like the Python side.

## Differences from Python bridge

- **Port:** 4041 (Python uses 4040).
- **No Redis** – No session persistence or outbound call mapping; WSS-only.
- **No VAD / flush** – Simpler inbound path; may add later if needed for “bot didn’t answer”.
- **Single file flow** – `server.js` + `gemini-client.js` + `audio.js`; easy to tweak.

## Production

Run behind TLS (e.g. Nginx) and set `PORT` in `.env`. Do not commit `.env`.
