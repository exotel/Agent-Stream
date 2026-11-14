"""Offline tests for llm_gemini: no network and no Google credentials are used."""

import asyncio
import importlib
import json
import sys
import threading
import types

import httpx
import pytest

from integrations.agents._shared import providers

GEMINI_ENV = (
    "GOOGLE_API_KEY",
    "GEMINI_MODEL",
    "SYSTEM_PROMPT",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
)
REPLY = {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in GEMINI_ENV:
        monkeypatch.delenv(name, raising=False)
    providers._vertex_adc.cache_clear()


@pytest.fixture
def sent(monkeypatch):
    """Answer llm_gemini's HTTP calls in memory and record the requests."""
    requests = []
    real_client = httpx.AsyncClient

    def reply(request):
        requests.append(request)
        return httpx.Response(200, json=REPLY)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(reply), **kwargs),
    )
    return requests


class FakeCredentials:
    def __init__(self):
        self.token = None
        self.refresh_threads = []

    @property
    def token_state(self):
        return "fresh" if self.token else "invalid"

    def refresh(self, request):
        self.refresh_threads.append(threading.current_thread())
        self.token = "fake-token"

    def apply(self, headers):
        headers["authorization"] = f"Bearer {self.token}"


@pytest.fixture
def vertex(monkeypatch):
    """Turn the Vertex AI path on, with a fake google-auth instead of real ADC."""
    credentials = FakeCredentials()
    adc = types.SimpleNamespace(project="adc-project", calls=0)

    def default(scopes):
        adc.calls += 1
        return credentials, adc.project

    google = types.SimpleNamespace()
    google.auth = types.SimpleNamespace(default=default)
    google.auth.credentials = types.SimpleNamespace(
        TokenState=types.SimpleNamespace(FRESH="fresh")
    )
    google.auth.transport = types.SimpleNamespace()
    google.auth.transport.requests = types.SimpleNamespace(Request=object)
    for name, module in {
        "google": google,
        "google.auth": google.auth,
        "google.auth.credentials": google.auth.credentials,
        "google.auth.transport": google.auth.transport,
        "google.auth.transport.requests": google.auth.transport.requests,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    return credentials, adc


def test_api_key_path(sent, monkeypatch):
    """Without the switch, the request still goes to the Gemini API with the key."""
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")

    assert asyncio.run(providers.llm_gemini("hi")) == "hello"

    (request,) = sent
    assert request.url.host == "generativelanguage.googleapis.com"
    assert request.url.path == "/v1beta/models/gemini-3.5-flash-lite:generateContent"
    assert request.url.params["key"] == "fake-key"
    assert "authorization" not in request.headers


@pytest.mark.parametrize(
    ("location", "host"),
    [
        ("global", "aiplatform.googleapis.com"),
        ("us", "aiplatform.us.rep.googleapis.com"),
        ("asia-south1", "asia-south1-aiplatform.googleapis.com"),
    ],
)
def test_vertex_path(sent, vertex, monkeypatch, location, host):
    """With the switch on, the request goes to Vertex AI with a bearer token."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", location)

    assert asyncio.run(providers.llm_gemini("hi")) == "hello"

    (request,) = sent
    assert request.url.host == host
    assert request.url.path == (
        f"/v1/projects/my-project/locations/{location}"
        "/publishers/google/models/gemini-3.5-flash-lite:generateContent"
    )
    assert request.headers["authorization"] == "Bearer fake-token"
    assert "key" not in request.url.params


def test_vertex_blank_env_uses_defaults(sent, vertex, monkeypatch):
    """Blank values, as `cp .env.example .env` leaves them, fall back to defaults."""
    for name in ("GEMINI_MODEL", "SYSTEM_PROMPT", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"):
        monkeypatch.setenv(name, "")

    asyncio.run(providers.llm_gemini("hi"))

    (request,) = sent
    assert request.url.host == "aiplatform.googleapis.com"
    assert request.url.path == (
        "/v1/projects/adc-project/locations/global"
        "/publishers/google/models/gemini-3.5-flash-lite:generateContent"
    )
    system = json.loads(request.content)["system_instruction"]["parts"][0]["text"]
    assert system == "You are a concise helpful phone assistant."


def test_vertex_token_is_reused_and_refreshed_off_the_event_loop(sent, vertex):
    """ADC loads once, and the blocking token refresh runs in a worker thread."""
    credentials, adc = vertex

    asyncio.run(providers.llm_gemini("one"))
    asyncio.run(providers.llm_gemini("two"))

    assert adc.calls == 1
    assert len(credentials.refresh_threads) == 1
    assert credentials.refresh_threads[0] is not threading.current_thread()


def test_vertex_without_project_fails_before_sending(sent, vertex):
    """No project in the env or in ADC gives a clear error and sends nothing."""
    vertex[1].project = None

    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        asyncio.run(providers.llm_gemini("hi"))
    assert sent == []


def test_providers_imports_without_google_auth(monkeypatch):
    """Recipes that don't use Vertex AI don't need google-auth installed."""
    monkeypatch.setitem(sys.modules, "google", None)

    importlib.reload(providers)
