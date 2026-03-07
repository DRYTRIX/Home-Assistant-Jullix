"""Tests for Jullix custom service handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.jullix import (
    DOMAIN,
    _handle_assign_chargersession,
    _handle_run_algorithm_hourly,
    _handle_set_charger_control,
)


@pytest.fixture
def hass_with_jullix():
    """Fake hass with DOMAIN data and one config entry."""
    hass = MagicMock()
    api = AsyncMock()
    coord = AsyncMock()
    coord.async_request_refresh = AsyncMock()
    hass.data = {
        DOMAIN: {
            "entry-1": {
                "install_ids": ["inst-1", "inst-2"],
                "api_client": api,
                "coordinator": coord,
            },
        },
    }
    hass.data[DOMAIN]["entry-1"]["api_client"] = api
    hass.data[DOMAIN]["entry-1"]["coordinator"] = coord
    return hass


@pytest.mark.asyncio
async def test_set_charger_control_calls_api_and_refreshes(hass_with_jullix):
    """set_charger_control finds entry, calls API, refreshes coordinator."""
    call = MagicMock()
    call.data = {
        "installation_id": "inst-1",
        "charger_mac": "AA:BB:CC",
        "enabled": True,
    }
    api = hass_with_jullix.data[DOMAIN]["entry-1"]["api_client"]
    coord = hass_with_jullix.data[DOMAIN]["entry-1"]["coordinator"]

    await _handle_set_charger_control(hass_with_jullix, call)

    api.set_charger_control.assert_called_once_with("AA:BB:CC", {"enabled": True})
    coord.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_set_charger_control_with_mode_and_max_power(hass_with_jullix):
    """set_charger_control sends config with mode and max_power."""
    call = MagicMock()
    call.data = {
        "installation_id": "inst-1",
        "charger_mac": "AA:BB:CC",
        "mode": "eco",
        "max_power": 11.0,
    }
    api = hass_with_jullix.data[DOMAIN]["entry-1"]["api_client"]

    await _handle_set_charger_control(hass_with_jullix, call)

    api.set_charger_control.assert_called_once()
    payload = api.set_charger_control.call_args[0][1]
    assert payload["config"]["mode"] == "eco"
    assert payload["config"]["max_power"] == 11.0


@pytest.mark.asyncio
async def test_set_charger_control_unknown_installation_raises(hass_with_jullix):
    """set_charger_control raises HomeAssistantError when installation_id not in any entry."""
    from homeassistant.exceptions import HomeAssistantError
    call = MagicMock()
    call.data = {
        "installation_id": "unknown-install",
        "charger_mac": "AA:BB:CC",
        "enabled": True,
    }
    with pytest.raises(HomeAssistantError, match="No Jullix config entry found"):
        await _handle_set_charger_control(hass_with_jullix, call)


@pytest.mark.asyncio
async def test_run_algorithm_hourly_calls_api_and_refreshes(hass_with_jullix):
    """run_algorithm_hourly calls API and refreshes coordinator."""
    call = MagicMock()
    call.data = {"installation_id": "inst-1"}
    api = hass_with_jullix.data[DOMAIN]["entry-1"]["api_client"]
    coord = hass_with_jullix.data[DOMAIN]["entry-1"]["coordinator"]

    await _handle_run_algorithm_hourly(hass_with_jullix, call)

    api.run_algorithm_hourly.assert_called_once_with("inst-1")
    coord.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_assign_chargersession_calls_api(hass_with_jullix):
    """assign_chargersession sends payload and refreshes."""
    call = MagicMock()
    call.data = {
        "installation_id": "inst-1",
        "session_id": "sess-123",
        "charger_mac": "MAC1",
    }
    api = hass_with_jullix.data[DOMAIN]["entry-1"]["api_client"]
    coord = hass_with_jullix.data[DOMAIN]["entry-1"]["coordinator"]

    await _handle_assign_chargersession(hass_with_jullix, call)

    api.assign_chargersession.assert_called_once()
    payload = api.assign_chargersession.call_args[0][0]
    assert payload["session_id"] == "sess-123"
    assert payload["charger_mac"] == "MAC1"
    coord.async_request_refresh.assert_called_once()
