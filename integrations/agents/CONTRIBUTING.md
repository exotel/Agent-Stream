# Contributing agent recipes

Guidelines for adding Exotel AgentStream voice agent recipes under `integrations/agents/`.

## Naming

```text
{llm}-{stt}-{tts}-{orchestration}     # pipelines
{model}-native                        # speech-to-speech
{model}-pipecat                       # S2S via Pipecat
```

Include provider + model series in each segment (e.g. `deepgramnova3`, `elevenflashv2.5`, `cartesiasonic3`). Size variants (`mini` / `flash`) belong in `.env`, not the folder name, unless two sizes are used together.

### Orchestration values

| Value | Meaning |
|-------|---------|
| `native` | Direct API integration |
| `pipecat` | Pipecat framework + ExotelFrameSerializer / AgentStream WSS |

## Required layout

```text
{recipe}/
├── README.md          # Setup, Connect Voice AI StreamUrl, env table
├── .env.example
├── requirements.txt
├── server.py          # FastAPI; expose /ws for AgentStream
├── agent.py           # AI-specific logic (optional but preferred)
└── system_prompt.md   # Optional default prompt
```

Prefer importing [`_shared.wss_server`](_shared/wss_server.py) for Exotel media events instead of re-implementing the protocol.

## Telephony rules

- Use **Exotel AgentStream** only (`connected` / `start` / `media` / `mark` / `clear` / `stop`).
- Document Connect Voice AI: `StreamType=bidirectional`, `StreamUrl=wss://…/ws?sample-rate=8000`.
- Do not rename Exotel env vars (`EXOTEL_ACCOUNT_SID`, `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_CALLER_ID`).
- Do not mention other CPaaS vendors in READMEs or code comments.
