"""Tests for Jullix coordinator (merge and data shape)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.jullix.coordinator import (
    JullixDataUpdateCoordinator,
    _merge_local_data,
)


def test_merge_local_data_empty_local():
    """_merge_local_data returns copy of platform_data when local is empty."""
    platform = {"chargers": [{"id": "1"}], "summary": {}}
    result = _merge_local_data(platform, {})
    assert result == platform
    assert result is not platform


def test_merge_local_data_merge_charger():
    """_merge_local_data overwrites charger with local charger data."""
    platform = {"chargers": [], "charger": [{"power": 0}]}
    local = {"charger": [{"power": 7.4, "active": True}]}
    result = _merge_local_data(platform, local)
    assert result["charger"] == [{"power": 7.4, "active": True}]


def test_merge_local_data_merge_plug():
    """_merge_local_data overwrites plug with local plug data."""
    platform = {"plugs": [], "plug": []}
    local = {"plug": [{"power": 100, "plug_state": True}]}
    result = _merge_local_data(platform, local)
    assert result["plug"] == [{"power": 100, "plug_state": True}]


def test_merge_local_data_merge_solar_battery_meter():
    """_merge_local_data merges solar, battery, and meter."""
    platform = {"solar": {}, "battery": [], "metering": {}}
    local = {
        "solar": {"power": 3.0},
        "battery": [{"soc": 80}],
        "meter": {"channels": [{"value": 1.0}]},
    }
    result = _merge_local_data(platform, local)
    assert result["solar"] == {"power": 3.0}
    assert result["battery"] == [{"soc": 80}]
    assert "metering" in result
    assert result["metering"].get("channels") == [{"value": 1.0}]


def test_merge_local_data_ignores_empty_local_values():
    """_merge_local_data does not overwrite with empty local lists."""
    platform = {"charger": [{"power": 7}]}
    local = {"charger": []}
    result = _merge_local_data(platform, local)
    # Empty list is falsy, so charger is not set per the code (if local_data["charger"] is falsy)
    assert result["charger"] == [{"power": 7}]


@pytest.fixture
def mock_hass():
    """Minimal HomeAssistant mock for coordinator."""
    return MagicMock()


@pytest.fixture
def mock_api_for_fetch():
    """API client mock that returns valid data for _fetch_installation_data."""
    client = MagicMock()
    client.get_power_summary = AsyncMock(return_value={"data": {"powers": {"grid": 0.5}}})
    client.get_actual_detail = AsyncMock(
        return_value={"data": []}
    )  # empty for most; battery/solar etc. can be list/dict
    client.get_chargers = AsyncMock(return_value=[])
    client.get_plugs = AsyncMock(return_value=[])
    client.get_cost_savings = AsyncMock(return_value={"savings": 10})
    client.get_cost_total = AsyncMock(return_value={"data": {"total": 50.0}})
    client.get_weather_alarm = AsyncMock(return_value={"data": []})
    client.get_statistics_energy_daily = AsyncMock(return_value={"data": []})
    client.get_statistics_energy_monthly = AsyncMock(return_value={"data": []})
    client.get_statistics_energy_yearly = AsyncMock(return_value={"data": []})
    client.get_algorithm_overview = AsyncMock(return_value={"data": {"state": "ok"}})
    client.get_tariff = AsyncMock(return_value={"data": {"tariff": "single"}})
    client.get_weather_forecast = AsyncMock(return_value={"data": []})
    return client


@pytest.mark.asyncio
@patch("homeassistant.helpers.frame.report_usage")
async def test_fetch_installation_data_returns_expected_keys(
    _mock_report, mock_hass, mock_api_for_fetch
):
    """_fetch_installation_data returns dict with summary, algorithm_overview, tariff, weather_forecast."""
    coordinator = JullixDataUpdateCoordinator(
        hass=mock_hass,
        api_client=mock_api_for_fetch,
        install_ids=["inst-1"],
        enable_cost=False,
    )
    result = await coordinator._fetch_installation_data("inst-1")
    assert "summary" in result
    assert result["summary"].get("powers", {}).get("grid") == 0.5
    assert "algorithm_overview" in result
    assert result["algorithm_overview"] == {"state": "ok"}
    assert "tariff" in result
    assert result["tariff"] == {"tariff": "single"}
    assert "weather_forecast" in result


@pytest.mark.asyncio
@patch("homeassistant.helpers.frame.report_usage")
async def test_fetch_installation_data_with_cost_includes_cost(
    _mock_report, mock_hass, mock_api_for_fetch
):
    """When enable_cost is True, result includes cost key."""
    coordinator = JullixDataUpdateCoordinator(
        hass=mock_hass,
        api_client=mock_api_for_fetch,
        install_ids=["inst-1"],
        enable_cost=True,
    )
    result = await coordinator._fetch_installation_data("inst-1")
    assert "cost" in result
    assert result["cost"] == {"savings": 10}


@pytest.mark.asyncio
@patch("homeassistant.helpers.frame.report_usage")
async def test_fetch_installation_data_with_chargers_populates_charger_control(
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
    result = await coordinator._fetch_installation_data("inst-1")
    assert "chargers" in result
    assert result["chargers"] == [{"id": "mac-1", "name": "Charger 1"}]
    assert "charger_control" in result
    assert "mac-1" in result["charger_control"]
    assert result["charger_control"]["mac-1"]["config"]["mode"] == "eco"
