"""App state and mock Redis for local WSS run."""
from typing import Any, Dict
from dataclasses import dataclass, field

@dataclass
class AppState:
    resources: Dict[str, Any] = field(default_factory=dict)

_app_state: AppState = None

def getAppState() -> AppState:
    global _app_state
    if _app_state is None:
        from agents.gateway.mock_redis import create_mock_redis
        _app_state = AppState(resources={"redis": create_mock_redis()})
    return _app_state

def set_app_state(state: AppState):
    global _app_state
    _app_state = state
