# 10-minute setup

**Architecture:** See [README.md](README.md#architecture) for the diagram (Caller → Exotel → Bridge → Gemini).

---

## Steps

| # | What | Do this |
|---|------|--------|
| 1 | **Install** | `python3 -m venv venv` → `source venv/bin/activate` → `pip install -r requirements.txt` |
| 2 | **Config** | `cp .env.example .env` → set `GOOGLE_LIVE_WS_API` (Gemini key from [AI Studio](https://aistudio.google.com/apikey)). Never commit `.env`. |
| 3 | **Run** | `SKIP_FULL_VALIDATION=1 uvicorn main:app --host 0.0.0.0 --port 4040` |
| 4 | **Check** | http://localhost:4040/health → `{"status":"ok"}` |
| 5 | **Expose** | Second terminal: `ngrok http 4040` → copy HTTPS host (e.g. `abc123.ngrok-free.app`) |
| 6 | **Exotel** | Voicebot Applet → WebSocket URL = `wss://<ngrok-host>/sales-agent/exotel/ws/audio/manual-test-run/TestUser?sample-rate=16000` (or use dynamic URL: set Answered URL to `https://<ngrok-host>/sales-agent/exotel/handle-answered-calls`) |
| 7 | **Test** | Call the number → hear greeting and talk to bot |

---

## Customize

| Change | File |
|--------|------|
| System prompt / greeting | `app/configs/prompts.py` |
| Voice | `app/configs/gemini.py` → `speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName` (do **not** set `languageCode`) |
| Tools (e.g. end call) | `app/configs/gemini.py` → `tools` + `TOOL_REGISTRY` |
| Latency / VAD | `.env` → `GEMINI_SILENCE_DURATION_MS`, `EXOTEL_VAD_RMS_THRESHOLD`, etc. (see `.env.example`) |

---

## Troubleshooting

| Symptom | Check (in order) |
|--------|-------------------|
| **Bot greets then silent** | Logs: 1) `Sent personalized greeting` 2) `first_audio_sent_to_gemini_at` or `Flush to Gemini` 3) `first_gemini_audio_in_at` 4) `first_bot_audio_out_to_exotel_at` 5) `DROPPING bot audio` (raise VAD threshold if false) |
| **Exotel / JSON errors** | Outbound: `sequence_number`, `media.chunk`, `media.timestamp`, `stream_sid` as **strings**. Bridge does this by default. |
| **Startup config error** | Use `SKIP_FULL_VALIDATION=1` when Exotel/Redis not set; or set vars in `.env`. |
| **Gemini model not found** | `app/configs/gemini.py` → valid `setup.model` (e.g. `models/gemini-2.5-flash-native-audio-preview-12-2025`). |
| **Interrupt not working** | Logs: `VAD barge-in` or `Exotel event (interruption-related)`. Tune `EXOTEL_VAD_RMS_THRESHOLD`, `EXOTEL_BOT_GRACE_PERIOD_S`. |
| **Bot stops ~1 min** | Health check every 120s; only reconnects when Gemini WS not OPEN. Logs: `Connection closed`, `Persistent Gemini disconnect`. |

---

## Exotel protocol (short)

- **We receive:** `connected`, `start`, `media`, `mark`, `clear`, `dtmf`, `stop`
- **We send:** `media` (3.2KB–100KB, ×320 bytes), `mark`, `clear` (on interrupt so Exotel clears unplayed audio)
- **Sample rate:** `?sample-rate=8000|16000|24000` on WSS URL (default 8k; we use 16k when possible)

---

## Production

- Reverse proxy (Nginx/Caddy) + TLS; `PRODUCTION_MODE=true`; set Exotel/Redis in `.env`; remove `SKIP_FULL_VALIDATION=1`.
- Scale: one process = in-memory state per call; use sticky routing if multiple workers or instances.
