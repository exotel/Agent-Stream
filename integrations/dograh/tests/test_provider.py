"""Unit tests for Exotel telephony provider (Connect Voice AI API).

Copy into dograh as: api/tests/telephony/exotel/test_provider.py
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.services.telephony.providers.exotel.provider import ExotelProvider


def _provider(**overrides) -> ExotelProvider:
    config = {
        "account_sid": "exotelaccount",
        "api_key": "key123",
        "api_token": "token456",
        "api_base_url": "https://api.in.exotel.com",
        "from_numbers": ["+9180XXXXXXX1"],
    }
    config.update(overrides)
    return ExotelProvider(config)


def test_validate_config_requires_credentials():
    assert _provider().validate_config() is True
    assert _provider(api_token=None).validate_config() is False


def test_can_handle_webhook_disabled_for_outbound_scope():
    assert not ExotelProvider.can_handle_webhook(
        {"CallSid": "abc", "AccountSid": "exotelaccount"},
        {"user-agent": "Exotel/1.0"},
    )


@pytest.mark.asyncio
async def test_initiate_call_posts_connect_with_stream_url():
    provider = _provider()

    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(
        return_value=json.dumps(
            {"Call": {"Sid": "call-sid-1", "Status": "in-progress"}}
        )
    )
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.post = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "api.services.telephony.providers.exotel.provider.aiohttp.ClientSession",
            return_value=session,
        ),
        patch(
            "api.services.telephony.providers.exotel.provider.get_backend_endpoints",
            new_callable=AsyncMock,
            return_value=("https://api.example.test", "wss://api.example.test"),
        ),
    ):
        result = await provider.initiate_call(
            to_number="+919999999999",
            webhook_url="https://unused.example.test",
            workflow_run_id=42,
            workflow_id=7,
            organization_id=9,
        )

    assert result.call_id == "call-sid-1"
    assert result.caller_number == "+9180XXXXXXX1"

    _, kwargs = session.post.call_args
    form = kwargs["data"]
    assert form["From"] == "+919999999999"
    assert form["CallerId"] == "+9180XXXXXXX1"
    assert form["StreamType"] == "bidirectional"
    assert form["StreamUrl"] == "wss://api.example.test/api/v1/telephony/ws/7/9/42"
    assert form["StatusCallback"].endswith("/exotel/status-callback/42")
    assert form["StatusCallbackEvents[]"] == "terminal"


@pytest.mark.asyncio
async def test_initiate_call_raises_on_api_error():
    provider = _provider()

    response = MagicMock()
    response.status = 400
    response.text = AsyncMock(return_value="bad request")
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.post = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "api.services.telephony.providers.exotel.provider.aiohttp.ClientSession",
            return_value=session,
        ),
        patch(
            "api.services.telephony.providers.exotel.provider.get_backend_endpoints",
            new_callable=AsyncMock,
            return_value=("https://api.example.test", "wss://api.example.test"),
        ),
        pytest.raises(HTTPException),
    ):
        await provider.initiate_call(
            to_number="+919999999999",
            webhook_url="https://unused",
            workflow_run_id=1,
            workflow_id=1,
            organization_id=1,
        )


def test_parse_status_callback():
    parsed = _provider().parse_status_callback(
        {
            "CallSid": "call-1",
            "Status": "completed",
            "From": "+911",
            "To": "+912",
            "Duration": "12",
        }
    )
    assert parsed["call_id"] == "call-1"
    assert parsed["status"] == "completed"
    assert parsed["duration"] == "12"


def test_supports_transfers_false():
    assert _provider().supports_transfers() is False
