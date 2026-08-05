# Dograh ↔ Exotel native integration (review package)

**Branch:** `feature/dograh-integration`  
**Upstream target:** [dograh-hq/dograh](https://github.com/dograh-hq/dograh)  
**API:** [Connect Voice AI](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)

This branch holds the **Dograh-native Exotel telephony provider** for internal review before opening a PR on `dograh-hq/dograh`.

## Scope

| In scope | Out of scope |
| --- | --- |
| Outbound `POST .../Calls/connect` | Inbound Voicebot applet (follow-up) |
| `StreamType=bidirectional` + Dograh WSS | Call transfer |
| StatusCallback (`terminal`) | |
| UI config (Account SID, API Key/Token) | |

## How Dograh uses Connect Voice AI

```
Dograh UI "Call"
    → POST {api_base}/v1/Accounts/{AccountSid}/Calls/connect
         From=<callee>
         CallerId=<ExoPhone>
         StreamUrl=wss://<dograh>/api/v1/telephony/ws/{wf}/{org}/{run}
         StreamType=bidirectional
         StatusCallback=https://<dograh>/api/v1/telephony/exotel/status-callback/{run}
    → Exotel dials PSTN
    → On answer, Exotel opens StreamUrl (AgentStream WSS)
    → Dograh agent pipeline runs
```

Auth: HTTP Basic (`API Key` / `API Token`).  
Base URL: `https://api.in.exotel.com` (Mumbai) or `https://api.exotel.com` (Singapore).

## Inbound (not in this package — ops notes)

1. Create a flow in App Bazaar  
2. Add **Voicebot** applet (`wss://…` or HTTPS returning `{"url":"wss://…"}`)  
3. **Assign an ExoPhone** to that flow  

Inbound provider wiring in Dograh is intentionally disabled (`can_handle_webhook → False`) until a follow-up.

## Files to copy into Dograh

| This repo | Dograh path |
| --- | --- |
| `integrations/dograh/providers/exotel/*` | `api/services/telephony/providers/exotel/` |
| `integrations/dograh/tests/test_provider.py` | `api/tests/telephony/exotel/test_provider.py` |
| `integrations/dograh/WIRING.md` | apply the listed one-line edits |

## Review checklist

- [ ] `initiate_call` matches Connect Voice AI fields  
- [ ] StreamUrl is Dograh WSS, not an answer URL  
- [ ] Status callback route updates workflow run  
- [ ] No edits to `factory.py` / `run_pipeline.py` / shared telephony routes  
- [ ] Code quality suitable for Dograh OSS review (not AI slop)  

## Quick Connect API smoke test (without Dograh)

```bash
# Point StreamUrl at this Agent-Stream bot or any AgentStream WSS
python scripts/place_connect_call.py --to +91XXXXXXXXXX
```

See `scripts/place_connect_call.py` and env vars in `env.example`.
