"""Pytest configuration and fixtures for Jullix integration tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure repo root is on path so custom_components can be imported when running tests
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Mock homeassistant only when not installed (so config flow tests can use real HA when available)
try:
    import homeassistant  # noqa: F401
    _HA_AVAILABLE = True
except ImportError:
    _HA_AVAILABLE = False

if not _HA_AVAILABLE and "homeassistant" not in sys.modules:
    from unittest.mock import MagicMock
    ha_mock = MagicMock()
    ha_mock.config_entries.ConfigEntry = MagicMock()
    ha_mock.const.Platform = MagicMock()
    ha_mock.core.HomeAssistant = MagicMock()
    ha_mock.core.ServiceCall = MagicMock()
    ha_mock.helpers.config_validation.cv = MagicMock()
    ha_mock.helpers.update_coordinator.DataUpdateCoordinator = MagicMock()
    ha_mock.helpers.update_coordinator.CoordinatorEntity = MagicMock()
    ha_mock.helpers.entity.Entity = MagicMock()
    ha_mock.components.switch.SwitchEntity = MagicMock()
    ha_mock.components.number.NumberEntity = MagicMock()
    ha_mock.components.select.SelectEntity = MagicMock()
    ha_mock.components.sensor.SensorEntity = MagicMock()
    ha_mock.components.sensor.SensorDeviceClass = MagicMock()
    ha_mock.components.sensor.SensorStateClass = MagicMock()
    ha_mock.data_entry_flow = MagicMock()
    ha_mock.core.callback = lambda f: f
    ha_mock.exceptions = MagicMock()
    ha_mock.exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    sys.modules["homeassistant"] = ha_mock
    sys.modules["homeassistant.config_entries"] = ha_mock.config_entries
    sys.modules["homeassistant.const"] = ha_mock.const
    sys.modules["homeassistant.core"] = ha_mock.core
    sys.modules["homeassistant.data_entry_flow"] = ha_mock.data_entry_flow
    sys.modules["homeassistant.exceptions"] = ha_mock.exceptions
    sys.modules["homeassistant.helpers"] = ha_mock.helpers
    sys.modules["homeassistant.helpers.config_validation"] = ha_mock.helpers.config_validation
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_mock.helpers.update_coordinator
    sys.modules["homeassistant.helpers.entity"] = ha_mock.helpers.entity
    sys.modules["homeassistant.components.switch"] = ha_mock.components.switch
    sys.modules["homeassistant.components.number"] = ha_mock.components.number
    sys.modules["homeassistant.components.select"] = ha_mock.components.select
    sys.modules["homeassistant.components.sensor"] = ha_mock.components.sensor
else:
    # When HA is installed, use real HA (e.g. for config_flow tests)
    pass


@pytest.fixture
def mock_api_client():
    """Create a mock Jullix API client with AsyncMock methods."""
    client = MagicMock()
    client.get_installations = AsyncMock(return_value=[{"id": "inst-1"}])
    client.get_power_summary = AsyncMock(return_value={"data": {"powers": {"grid": 1.0}}})
    client.get_actual_detail = AsyncMock(return_value={"data": []})
    client.get_chargers = AsyncMock(return_value=[
        {"id": "mac-charger-1", "name": "Charger 1", "active": True, "power": 7.4},
    ])
    client.get_charger_control = AsyncMock(return_value={
        "data": {"config": {"mode": "eco", "max_power": 11.0}},
    })
    client.get_plugs = AsyncMock(return_value=[
        {"id": "mac-plug-1", "name": "Plug 1", "power": 100},
    ])
    client.get_cost_savings = AsyncMock(return_value={})
    client.get_tariff = AsyncMock(return_value={"data": {"tariff": "single"}})
    client.get_algorithm_overview = AsyncMock(return_value={"data": {"state": "ok"}})
    client.get_weather_forecast = AsyncMock(return_value={"data": []})
    client.set_charger_control = AsyncMock(return_value={})
    client.set_plug_control = AsyncMock(return_value={})
    return client


@pytest.fixture
def sample_install_data():
    """Sample installation data as returned by coordinator."""
    return {
        "summary": {"powers": {"grid": 1.0, "solar": 2.0, "home": 1.5}},
        "chargers": [
            {"id": "mac-1", "name": "Charger 1", "active": True, "power": 7.4},
        ],
        "charger_control": {
            "mac-1": {"config": {"mode": "eco", "max_power": 11.0}},
        },
        "plugs": [
            {"id": "plug-mac-1", "name": "Plug 1", "power": 100},
        ],
        "charger": [],
        "plug": [],
        "algorithm_overview": {"state": "ok"},
        "tariff": {"tariff": "single"},
        "weather_forecast": [],
    }
