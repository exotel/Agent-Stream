"""In-memory async Redis stub for local WSS (no real Redis)."""
import asyncio
from typing import Optional

class MockRedis:
    def __init__(self):
        self._store = {}

    async def set(self, key: str, value, ex: Optional[int] = None):
        self._store[key] = value

    async def get(self, key: str):
        return self._store.get(key)

    async def delete(self, key: str):
        self._store.pop(key, None)

def create_mock_redis():
    return MockRedis()
