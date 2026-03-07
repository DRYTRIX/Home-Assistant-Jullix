"""Tests for Jullix API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.jullix.api import (
    JullixApiClient,
    JullixApiError,
    JullixAuthError,
)
from custom_components.jullix.const import API_BASE_URL


@pytest.fixture
def client():
    """API client with fake token."""
    return JullixApiClient(api_token="fake-token")


@pytest.mark.asyncio
async def test_headers(client):
    """Test request headers include auth and content-type."""
    assert "Authorization" in client._headers()
    assert client._headers()["Authorization"] == "Bearer fake-token"
    assert client._headers().get("Content-Type") == "application/json"


@pytest.mark.asyncio
async def test_get_installations_returns_list(client):
    """Test get_installations normalizes response to list."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = [{"id": "i1"}, {"id": "i2"}]
        result = await client.get_installations()
        assert result == [{"id": "i1"}, {"id": "i2"}]
        req.assert_called_once()

    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"installations": [{"id": "i1"}]}
        result = await client.get_installations()
        assert result == [{"id": "i1"}]


@pytest.mark.asyncio
async def test_get_chargers_returns_list(client):
    """Test get_chargers normalizes response to list."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = [{"id": "mac1", "name": "Charger 1"}]
        result = await client.get_chargers("install-1")
        assert len(result) == 1
        assert result[0]["id"] == "mac1"
        req.assert_called_once()
        assert "/charger/installation/install-1/all" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_set_charger_control_puts_payload(client):
    """Test set_charger_control sends PUT with correct path and payload."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {}
        await client.set_charger_control("AA:BB:CC", {"enabled": True})
        req.assert_called_once()
        assert req.call_args[0][0] == "PUT"
        assert "/charger/AA:BB:CC/control" in req.call_args[0][1]
        assert req.call_args[1]["json"] == {"enabled": True}


@pytest.mark.asyncio
async def test_set_plug_control_puts_payload(client):
    """Test set_plug_control sends PUT with correct path and payload."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {}
        await client.set_plug_control("PLUG:MAC", {"enabled": False})
        req.assert_called_once()
        assert req.call_args[0][0] == "PUT"
        assert "/plug/PLUG:MAC/control" in req.call_args[0][1]
        assert req.call_args[1]["json"] == {"enabled": False}


class _FakeResponse:
    """Minimal async context manager that yields a response-like object."""

    def __init__(self, status: int, text: str = "", content_length: int = 0):
        self.status = status
        self._text = text
        self.content_length = content_length
        self.reason = "Error"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def text(self):
        return self._text

    async def json(self):
        return {}


@pytest.mark.asyncio
async def test_request_raises_auth_error_on_401(client):
    """Test _request raises JullixAuthError on 401."""
    session = MagicMock()
    session.request.return_value = _FakeResponse(401, content_length=0)

    with patch.object(client, "_session", session):
        with pytest.raises(JullixAuthError):
            await client._request("GET", "/test")


@pytest.mark.asyncio
async def test_request_raises_api_error_on_4xx(client):
    """Test _request raises JullixApiError on 4xx/5xx."""
    session = MagicMock()
    session.request.return_value = _FakeResponse(404, text="Not found", content_length=9)

    with patch.object(client, "_session", session):
        with pytest.raises(JullixApiError):
            await client._request("GET", "/test")


@pytest.mark.asyncio
async def test_get_charger_control_and_status_paths(client):
    """Test charger control and status use correct paths."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": {"config": {"mode": "eco"}}}
        await client.get_charger_control("MAC1")
        req.assert_called_once()
        assert "/charger/MAC1/control" in req.call_args[0][1]

        req.reset_mock()
        req.return_value = {"charging": True}
        await client.get_charger_status("MAC1")
        req.assert_called_once()
        assert "/charger/MAC1/status" in req.call_args[0][1]
