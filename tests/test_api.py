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


@pytest.mark.asyncio
async def test_get_plugs_returns_list(client):
    """Test get_plugs normalizes response to list and uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = [{"id": "plug1", "name": "Plug 1"}]
        result = await client.get_plugs("inst-1")
        assert len(result) == 1
        assert result[0]["id"] == "plug1"
        req.assert_called_once()
        assert "/plug/installation/inst-1/all" in req.call_args[0][1]
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"plugs": [{"id": "p1"}]}
        result = await client.get_plugs("inst-1")
        assert result == [{"id": "p1"}]


@pytest.mark.asyncio
async def test_get_power_summary_path(client):
    """Test get_power_summary uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": {"powers": {"grid": 1.0}}}
        await client.get_power_summary("inst-42")
        req.assert_called_once()
        assert req.call_args[0][0] == "GET"
        assert "/actual/inst-42/summary/power" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_get_actual_detail_path(client):
    """Test get_actual_detail uses correct path with detail_type."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": []}
        await client.get_actual_detail("inst-1", "battery")
        req.assert_called_once()
        assert "/actual/inst-1/detail/battery" in req.call_args[0][1]
        await client.get_actual_detail("inst-1", "solar")
        assert "/actual/inst-1/detail/solar" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_get_cost_savings_path(client):
    """Test get_cost_savings uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": {}}
        await client.get_cost_savings("inst-1")
        req.assert_called_once()
        assert "/cost/savings/inst-1" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_get_tariff_path(client):
    """Test get_tariff uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": {"tariff": "single"}}
        await client.get_tariff("inst-1")
        req.assert_called_once()
        assert "/tariff/inst-1" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_get_algorithm_overview_path(client):
    """Test get_algorithm_overview uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": {}}
        await client.get_algorithm_overview("inst-1")
        req.assert_called_once()
        assert "/algorithm/overview/inst-1" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_get_weather_forecast_path(client):
    """Test get_weather_forecast uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": []}
        await client.get_weather_forecast("inst-1")
        req.assert_called_once()
        assert "/weather/forecast/inst-1" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_run_algorithm_hourly_path(client):
    """Test run_algorithm_hourly uses GET and correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {}
        await client.run_algorithm_hourly("inst-1")
        req.assert_called_once()
        assert req.call_args[0][0] == "GET"
        assert "/algorithm/run-hourly/inst-1" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_assign_chargersession_path_and_payload(client):
    """Test assign_chargersession uses PUT and forwards payload."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {}
        payload = {"session_id": "s1", "charger_mac": "mac1", "car_id": "car1"}
        await client.assign_chargersession(payload)
        req.assert_called_once()
        assert req.call_args[0][0] == "PUT"
        assert "/chargersession/assign" in req.call_args[0][1]
        assert req.call_args[1]["json"] == payload


@pytest.mark.asyncio
async def test_get_installation_path(client):
    """Test get_installation uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"id": "inst-1", "name": "Home"}
        result = await client.get_installation("inst-1")
        assert result["id"] == "inst-1"
        req.assert_called_once()
        assert "/installation/inst-1" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_get_statistics_energy_daily_path(client):
    """Test get_statistics_energy_daily uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": []}
        await client.get_statistics_energy_daily("inst-1")
        req.assert_called_once()
        assert "/statistics/energy/inst-1/daily" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_get_weather_alarm_path(client):
    """Test get_weather_alarm uses correct path."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {"data": []}
        await client.get_weather_alarm("inst-1")
        req.assert_called_once()
        assert "/weather/alarm/inst-1" in req.call_args[0][1]


@pytest.mark.asyncio
async def test_update_tariff_put_path(client):
    """Test update_tariff sends PUT with correct path and payload."""
    with patch.object(client, "_request", new_callable=AsyncMock) as req:
        req.return_value = {}
        await client.update_tariff("inst-1", {"tariff": "dual"})
        req.assert_called_once()
        assert req.call_args[0][0] == "PUT"
        assert "/tariff/inst-1" in req.call_args[0][1]
        assert req.call_args[1]["json"] == {"tariff": "dual"}
