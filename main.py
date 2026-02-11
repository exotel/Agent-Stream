"""
Exotel ↔ Gemini bridge. Serves Exotel WebSocket at /sales-agent/exotel/ws/audio/...
Run: SKIP_FULL_VALIDATION=1 uvicorn main:app --host 0.0.0.0 --port 4040
See 10_MINUTE_GUIDE.md to start the bot.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Mount exotel router at /sales-agent so WSS path is /sales-agent/exotel/ws/audio/...
from agents.gateway.sales_agent.exotel import router as exotel_router

app = FastAPI(title="Exotel Voicebot WSS")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(exotel_router, prefix="/sales-agent")

@app.get("/")
async def root():
    return {"status": "ok", "wss": "wss://<host>/sales-agent/exotel/ws/audio/<run_id>/<name>?sample_rate=16000"}


@app.get("/health")
async def health():
    """For load balancers and orchestrators (e.g. k8s readiness/liveness)."""
    return {"status": "ok"}
