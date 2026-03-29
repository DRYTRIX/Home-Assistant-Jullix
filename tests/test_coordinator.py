"""Tests for Jullix coordinator and local merge."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.jullix.models import (
    RawInstallFetches,
    build_installation_snapshot,
    merge_local_snapshot,
)
from custom_components.jullix.coordinator import JullixDataUpdateCoordinator

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "api"


def test_merge_local_snapshot_empty_local_returns_same():
    """merge_local_snapshot with empty local returns the same snapshot object."""
    platform = build_installation_snapshot(
        RawInstallFetches(chargers_response=[{"id": "1"}], power_summary={"data": {"powers": {}}})
    )
    result = merge_local_snapshot(platform, {})
    assert result is platform


def test_merge_local_snapshot_merge_charger_rows():
    """Local charger list overwrites detail charger rows."""
    platform = build_installation_snapshot(
        RawInstallFetches(detail_charger=[{"power": 0}])
    )
    result = merge_local_snapshot(
        platform, {"charger": [{"power": 7.4, "active": True}]}
    )
    assert len(result.charger_detail_rows) == 1
    assert result.charger_detail_rows[0]["power"] == 7.4


def test_merge_local_snapshot_merge_plug_rows():
    """Local plug list overwrites detail plug rows."""
    platform = build_installation_snapshot(RawInstallFetches(detail_plug=[]))
    result = merge_local_snapshot(
        platform, {"plug": [{"power": 100, "plug_state": True}]}
    )
    assert len(result.plug_detail_rows) == 1
    assert result.plug_detail_rows[0]["power"] == 100


def test_merge_local_snapshot_merge_solar_battery_meter():
    """Local solar, battery, and meter merge into snapshot."""
    platform = build_installation_snapshot(
        RawInstallFetches(detail_solar={}, detail_battery=[], detail_metering={})
    )
    local = {
        "solar": {"power": 3.0},
        "battery": [{"soc": 80}],
        "meter": {"channels": [{"value": 1.0}]},
    }
    result = merge_local_snapshot(platform, local)
    assert result.solar_detail.raw.get("power") == 3.0
    assert len(result.battery_slots) == 1
    assert result.battery_slots[0].soc == 80.0
    assert len(result.metering.channels) == 1
    assert result.metering.channels[0].get("value") == 1.0


def test_merge_local_snapshot_ignores_empty_charger_list():
    """Empty local charger list does not clear existing rows."""
    platform = build_installation_snapshot(
        RawInstallFetches(detail_charger=[{"power": 7}])
    )
    result = merge_local_snapshot(platform, {"charger": []})
    assert len(result.charger_detail_rows) == 1
    assert result.charger_detail_rows[0]["power"] == 7


def test_power_summary_fixture_parses_to_watts():
    """JSON fixture loads and grid power is converted kW → W."""
    raw = json.loads((FIXTURES / "power_summary.json").read_text())
    snap = build_installation_snapshot(RawInstallFetches(power_summary=raw))
    assert snap.power_summary.power_watts("grid") == 500.0


@pytest.fixture
def mock_hass():
    """Minimal HomeAssistant mock for coordinator."""
    return MagicMock()


def _async_return(value=None):
    """Helper: return an AsyncMock that resolves to value."""
    return AsyncMock(return_value=value)


class _MockApiClientForFetch:
    """Fake API client where every method is an AsyncMock (no MagicMock to await)."""

    get_power_summary = _async_return({"data": {"powers": {"grid": 0.5}}})
    get_actual_detail = _async_return({"data": []})
    get_chargers = _async_return([])
    get_charger_control = _async_return(
        {"data": {"config": {"mode": "eco", "max_power": 11.0}}}
    )
    get_plugs = _async_return([])
    get_history_plug_energy = _async_return({})
    get_cost_savings = _async_return({"savings": 10})
    get_cost_total = _async_return({"data": {"total": 50.0}})
    get_weather_alarm = _async_return({"data": []})
    get_statistics_energy_daily = _async_return({"data": []})
    get_statistics_energy_monthly = _async_return({"data": []})
    get_statistics_energy_yearly = _async_return({"data": []})
    get_algorithm_overview = _async_return({"data": {"state": "ok"}})
    get_tariff = _async_return({"data": {"tariff": "single"}})
    get_weather_forecast = _async_return({"data": []})
    get_cost_hourly_price = _async_return({})
    get_chargersession_installation = _async_return({})


@pytest.fixture
def mock_api_for_fetch():
    """API client mock for snapshot build. All methods are AsyncMocks."""
    return _MockApiClientForFetch()


@pytest.mark.asyncio
@patch("homeassistant.helpers.frame.report_usage")
async def test_build_snapshot_returns_expected_fields(
    _mock_report, mock_hass, mock_api_for_fetch
):
    """Coordinator builds snapshot with summary, algorithm, tariff, weather."""
    coordinator = JullixDataUpdateCoordinator(
        hass=mock_hass,
        api_client=mock_api_for_fetch,
        install_ids=["inst-1"],
        enable_cost=False,
    )
    result = await coordinator._build_snapshot_for_install("inst-1", extended=True)
    assert result.power_summary.power_watts("grid") == 500.0
    assert result.algorithm_overview == {"state": "ok"}
    assert result.tariff == {"tariff": "single"}
    assert result.weather_forecast == []


@pytest.mark.asyncio
@patch("homeassistant.helpers.frame.report_usage")
async def test_build_snapshot_with_cost_includes_cost_savings(
    _mock_report, mock_hass, mock_api_for_fetch
):
    """When enable_cost is True and extended, snapshot includes cost savings raw."""
    coordinator = JullixDataUpdateCoordinator(
        hass=mock_hass,
        api_client=mock_api_for_fetch,
        install_ids=["inst-1"],
        enable_cost=True,
    )
    result = await coordinator._build_snapshot_for_install("inst-1", extended=True)
    assert result.cost_savings.raw.get("savings") == 10
    assert result.cost_total.total == 50.0


@pytest.mark.asyncio
@patch("homeassistant.helpers.frame.report_usage")
async def test_build_snapshot_with_chargers_populates_charger_control(
    _mock_report, mock_hass, mock_api_for_fetch
):
    """When chargers are returned, charger_control is populated per charger."""
    mock_api_for_fetch.get_chargers = AsyncMock(
        return_value=[{"id": "mac-1", "name": "Charger 1"}]
    )
    mock_api_for_fetch.get_charger_control = AsyncMock(
        return_value={"data": {"config": {"mode": "eco", "max_power": 11.0}}}
    )
    coordinator = JullixDataUpdateCoordinator(
        hass=mock_hass,
        api_client=mock_api_for_fetch,
        install_ids=["inst-1"],
        enable_cost=False,
    )
    result = await coordinator._build_snapshot_for_install("inst-1", extended=False)
    assert len(result.chargers) == 1
    assert result.chargers[0].mac == "mac-1"
    assert "mac-1" in result.charger_control
    assert result.charger_control["mac-1"]["config"]["mode"] == "eco"


@pytest.mark.asyncio
@patch("homeassistant.helpers.frame.report_usage")
async def test_async_update_data_uses_last_good_when_build_raises(
    _mock_report, mock_hass, mock_api_for_fetch
):
    """If snapshot build raises, previous snapshot is kept for that installation."""
    coordinator = JullixDataUpdateCoordinator(
        hass=mock_hass,
        api_client=mock_api_for_fetch,
        install_ids=["inst-1"],
        enable_cost=False,
    )
    await coordinator._async_update_data()
    assert "inst-1" in coordinator.data
    good = coordinator.data["inst-1"]

    with patch.object(
        coordinator,
        "_build_snapshot_for_install",
        new_callable=AsyncMock,
        side_effect=RuntimeError("network down"),
    ):
        await coordinator._async_update_data()
    assert coordinator.data["inst-1"] is good
