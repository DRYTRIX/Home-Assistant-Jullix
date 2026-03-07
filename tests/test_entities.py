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


@pytest.fixture
def hass_and_entry(sample_install_data):
    """Minimal hass and entry with coordinator data for entity setup."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test-entry"
    entry.options = {}
    coordinator = MagicMock()
    coordinator.data = {"inst-1": sample_install_data}
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
async def test_sensor_setup_creates_entities(hass_and_entry, sample_install_data):
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
    # Switch entities use DOMAIN-prefixed unique_id (e.g. jullix_inst-1_charger_mac-1_switch)
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
