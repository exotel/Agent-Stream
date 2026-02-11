"""Minimal auth for local run."""
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    if not x_api_key and __import__("os").getenv("REQUIRE_AUTH", "").lower() == "true":
        raise HTTPException(status_code=401, detail="API key required")
    return x_api_key or "local"
