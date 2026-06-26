"""Pytest configuration and fixtures for Jullix integration tests."""

from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Generic, TypeVar
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
    ha_mock = MagicMock()
    ha_mock.config_entries.ConfigEntry = MagicMock()
    ha_mock.const.Platform = MagicMock()
    ha_mock.core.HomeAssistant = MagicMock()
    ha_mock.core.ServiceCall = MagicMock()

    _ha_util_dt = types.ModuleType("homeassistant.util.dt")

    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    _ha_util_dt.utcnow = _utcnow
    _ha_util = types.ModuleType("homeassistant.util")
    _ha_util.dt = _ha_util_dt
    sys.modules["homeassistant.util"] = _ha_util
    sys.modules["homeassistant.util.dt"] = _ha_util_dt

    _ha_helpers = types.ModuleType("homeassistant.helpers")

    class _ConfigValidationModule(types.ModuleType):
        """Stub cv module; unknown attrs behave like the old MagicMock cv."""

        def __getattr__(self, name: str) -> MagicMock:
            return MagicMock()

    _ha_helpers_config_validation = _ConfigValidationModule(
        "homeassistant.helpers.config_validation"
    )

    def _config_entry_only_config_schema(domain: str) -> object:
        """Stub for homeassistant.helpers.config_validation.config_entry_only_config_schema."""
        import voluptuous as vol

        return vol.Schema({vol.Optional(domain): object})

    _ha_helpers_config_validation.config_entry_only_config_schema = (
        _config_entry_only_config_schema
    )
    _ha_helpers.config_validation = _ha_helpers_config_validation

    _ha_helpers_device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    _ha_helpers_device_registry.DeviceEntry = MagicMock()
    _ha_helpers_device_registry.DeviceInfo = MagicMock()
    _ha_helpers.device_registry = _ha_helpers_device_registry

    _ha_helpers_typing = types.ModuleType("homeassistant.helpers.typing")
    _ha_helpers_typing.ConfigType = dict
    _ha_helpers.typing = _ha_helpers_typing

    _ha_helpers_entity = types.ModuleType("homeassistant.helpers.entity")
    _ha_helpers_entity.Entity = MagicMock()
    _ha_helpers_entity.EntityCategory = MagicMock()
    _ha_helpers.entity = _ha_helpers_entity

    _ha_helpers_frame = types.ModuleType("homeassistant.helpers.frame")
    _ha_helpers_frame.report_usage = MagicMock()
    _ha_helpers.frame = _ha_helpers_frame

    _ha_update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    _T_coordinator_data = TypeVar("_T_coordinator_data")

    class UpdateFailed(Exception):
        """Stub matching homeassistant.helpers.update_coordinator.UpdateFailed."""

    class DataUpdateCoordinator(Generic[_T_coordinator_data]):
        """Minimal base so JullixDataUpdateCoordinator can subclass without real HA."""

        def __init__(
            self,
            hass: object,
            logger: object,
            *,
            name: str | None = None,
            update_interval: object | None = None,
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval

    class CoordinatorEntity:
        """Stub entity base for platform modules under mock."""

    _ha_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    _ha_update_coordinator.UpdateFailed = UpdateFailed
    _ha_update_coordinator.CoordinatorEntity = CoordinatorEntity
    _ha_helpers.update_coordinator = _ha_update_coordinator
    ha_mock.helpers = _ha_helpers

    ha_mock.config_entries.SOURCE_REAUTH = "reauth"
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
    ha_mock.exceptions.ServiceValidationError = type(
        "ServiceValidationError",
        (Exception,),
        {},
    )
    sys.modules["homeassistant"] = ha_mock
    sys.modules["homeassistant.config_entries"] = ha_mock.config_entries
    sys.modules["homeassistant.const"] = ha_mock.const
    sys.modules["homeassistant.core"] = ha_mock.core
    sys.modules["homeassistant.data_entry_flow"] = ha_mock.data_entry_flow
    sys.modules["homeassistant.exceptions"] = ha_mock.exceptions
    sys.modules["homeassistant.helpers"] = _ha_helpers
    sys.modules["homeassistant.helpers.config_validation"] = _ha_helpers_config_validation
    sys.modules["homeassistant.helpers.device_registry"] = _ha_helpers_device_registry
    sys.modules["homeassistant.helpers.typing"] = _ha_helpers_typing
    sys.modules["homeassistant.helpers.update_coordinator"] = _ha_update_coordinator
    sys.modules["homeassistant.helpers.entity"] = _ha_helpers_entity
    sys.modules["homeassistant.helpers.frame"] = _ha_helpers_frame
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
def sample_installation_snapshot():
    """Sample installation snapshot as returned by coordinator."""
    from custom_components.jullix.models import RawInstallFetches, build_installation_snapshot

    return build_installation_snapshot(
        RawInstallFetches(
            power_summary={"data": {"powers": {"grid": 1.0, "solar": 2.0, "home": 1.5}}},
            chargers_response=[
                {"id": "mac-1", "name": "Charger 1", "active": True, "power": 7.4},
            ],
            charger_control_by_mac={
                "mac-1": {"config": {"mode": "eco", "max_power": 11.0}},
            },
            plugs_response=[
                {"id": "plug-mac-1", "name": "Plug 1", "power": 100},
            ],
            algorithm_overview={"state": "ok"},
            tariff={"tariff": "single"},
            weather_forecast=[],
            installation_meta={"name": "Test site"},
            charger_status_by_mac={"mac-1": {"data": {"status": "connected"}}},
            charger_events_by_mac={"mac-1": {"data": [{"event": "plug_in"}]}},
            charger_energies_by_mac={"mac-1": {"data": {"energy_kwh": 12.5}}},
            algorithm_settings={"data": {"enabled": True}},
            algorithm_results={"data": {"status": "ok"}},
            algorithm_usage={"data": {"mode": "auto"}},
            algorithm_pvpredict={"data": {"forecast": [1.0, 2.0]}},
        )
    )
