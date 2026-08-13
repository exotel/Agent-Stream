# OpenAPI — Exotel Connect Voice AI

Machine-readable HTTP contracts for placing AgentStream outbound calls.

| Spec | Covers |
|------|--------|
| [exotel-connect-voice-ai.yaml](exotel-connect-voice-ai.yaml) | `POST /v1/Accounts/{AccountSid}/Calls/connect` — **direct bot** and **with Flow** modes |

## Why this exists

Markdown guides are great for go-live. OpenAPI lets you:

- Browse / try the API in [Swagger Editor](https://editor.swagger.io/)
- Generate typed clients (OpenAPI Generator, Speakeasy, etc.)
- Diff request/response fields in PRs

**Out of scope (on purpose):** AgentStream WebSocket media frames and ExoML gRPC leg events — those are not REST. See [AGENTSTREAM_WSS_PROTOCOL.md](../AGENTSTREAM_WSS_PROTOCOL.md) and the [Exotel AgentStream docs](https://docs.exotel.com/exotel-agentstream).

## View in Swagger UI

1. Open [https://editor.swagger.io/](https://editor.swagger.io/)
2. **File → Import file** and select `exotel-connect-voice-ai.yaml`
3. Or paste the raw GitHub URL after this file is on `main`

## Auth reminder

HTTP Basic: **API Key** = username, **API Token** = password. Prefer env vars / the repo helper:

```bash
python shared/place_connect_call.py --to +91… --stream-url "wss://…"
```

## Human-readable companions

- [Connect Voice AI (repo)](../CONNECT_VOICE_AI.md)
- [docs.exotel.com — Connect Voice AI](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)
- [docs.exotel.com — Connect with Flow](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-with-flow-api)
