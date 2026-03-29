"""Tests for Jullix entity platforms (sensor, switch, number, select) setup and attributes."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

pytest.importorskip("homeassistant")
if isinstance(sys.modules.get("homeassistant"), MagicMock):
    pytest.skip(
        "Entity tests require real Home Assistant (install homeassistant)",
        allow_module_level=True,
    )

from custom_components.jullix.const import DOMAIN
from custom_components.jullix.models import RawInstallFetches, build_installation_snapshot
from custom_components.jullix.runtime_state import InstallRuntimeMetrics


@pytest.fixture
def sample_installation_snapshot():
    """Sample installation snapshot as returned by coordinator."""
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
        )
    )


@pytest.fixture
def hass_and_entry(sample_installation_snapshot):
    """Minimal hass and entry with coordinator data for entity setup."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test-entry"
    entry.options = {}
    coordinator = MagicMock()
    coordinator.data = {"inst-1": sample_installation_snapshot}
    coordinator.last_installation_errors = {}
    coordinator.install_metrics = {
        "inst-1": InstallRuntimeMetrics(last_latency_ms=120.0, last_success_at=None)
    }
    hass.data = {
        DOMAIN: {
            "test-entry": {
                "coordinator": coordinator,
                "install_ids": ["inst-1"],
                "api_client": MagicMock(),
            }
        }
    }
    return hass, entry


@pytest.mark.asyncio
async def test_sensor_setup_creates_entities(hass_and_entry, sample_installation_snapshot):
    """Sensor async_setup_entry creates entities with expected unique_ids."""
    from custom_components.jullix import sensor

    hass, entry = hass_and_entry
    added = []

    def capture(entities):
        added.extend(entities)

    await sensor.async_setup_entry(hass, entry, capture)

    assert len(added) > 0
    unique_ids = [getattr(e, "unique_id", None) for e in added]
    assert any(uid and "inst-1_summary" in uid for uid in unique_ids)
    assert any(uid and "inst-1_charger" in uid for uid in unique_ids)
    assert any(uid and "connection_health" in (uid or "") for uid in unique_ids)
    assert any(uid and "insight_self_consumption" in (uid or "") for uid in unique_ids)


@pytest.mark.asyncio
async def test_binary_sensor_setup_when_cost_enabled(hass_and_entry):
    """Binary sensor platform adds peak tariff when cost option is on."""
    from custom_components.jullix import binary_sensor

    hass, entry = hass_and_entry
    entry.options = {"enable_cost": True}
    added = []

    def capture(entities):
        added.extend(entities)

    await binary_sensor.async_setup_entry(hass, entry, capture)
    assert len(added) == 1
    assert "peak_tariff" in (added[0].unique_id or "")


@pytest.mark.asyncio
async def test_switch_setup_creates_entities(hass_and_entry):
    """Switch async_setup_entry creates charger and plug switches with expected unique_ids."""
    from custom_components.jullix import switch

    hass, entry = hass_and_entry
    entry.options = {"enable_charger_control": True, "enable_plug_control": True}
    added = []

    def capture(entities):
        added.extend(entities)

    await switch.async_setup_entry(hass, entry, capture)

    assert len(added) > 0
    unique_ids = [getattr(e, "unique_id", None) for e in added]
    assert any(uid and "inst-1_charger_mac-1_switch" in uid for uid in unique_ids)
    assert any(uid and "inst-1_plug_plug-mac-1_switch" in uid for uid in unique_ids)


@pytest.mark.asyncio
async def test_number_setup_creates_charger_power_entity(hass_and_entry):
    """Number async_setup_entry creates charger max power entity."""
    from custom_components.jullix import number

    hass, entry = hass_and_entry
    added = []

    def capture(entities):
        added.extend(entities)

    await number.async_setup_entry(hass, entry, capture)

    assert len(added) > 0
    unique_ids = [getattr(e, "unique_id", None) for e in added]
    assert any(
        uid and "inst-1_charger" in (uid or "") and "max_power" in (uid or "")
        for uid in unique_ids
    )


@pytest.mark.asyncio
async def test_select_setup_creates_charger_mode_entity(hass_and_entry):
    """Select async_setup_entry creates charger mode entity."""
    from custom_components.jullix import select

    hass, entry = hass_and_entry
    added = []

    def capture(entities):
        added.extend(entities)

    await select.async_setup_entry(hass, entry, capture)

    assert len(added) > 0
    unique_ids = [getattr(e, "unique_id", None) for e in added]
    assert any(
        uid and "inst-1_charger" in (uid or "") and "mode" in (uid or "")
        for uid in unique_ids
    )
