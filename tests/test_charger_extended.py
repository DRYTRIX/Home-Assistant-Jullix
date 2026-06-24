"""Tests for Jullix extended-charger sensor value parsing.

charger_extended.py imports homeassistant.helpers.device_registry at module
scope, which isn't stubbed by the lightweight conftest HA mock (same as every
other platform module), so it can't be imported here. Mirror its pure helpers
instead, same approach as test_switch.py::_is_enabled.
"""

from __future__ import annotations

from typing import Any

from custom_components.jullix.models.util import safe_float, unwrap_data


def _status_state(payload: Any) -> str | None:
    """Mirror of charger_extended._status_state."""
    data = unwrap_data(payload)
    if isinstance(data, dict):
        for key in ("status", "state", "connection", "mode"):
            val = data.get(key)
            if val is not None:
                return str(val)
    return None


def _events_count(payload: Any) -> int | None:
    """Mirror of charger_extended._events_count."""
    data = unwrap_data(payload)
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("events", "data", "items"):
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
    return None


def _charger_energy_kwh(payload: Any) -> float | None:
    """Mirror of charger_extended._charger_energy_kwh."""
    data = unwrap_data(payload)
    if isinstance(data, dict):
        for key in ("energy", "energy_kwh", "total", "kwh", "total_energy"):
            v = safe_float(data.get(key))
            if v is not None:
                return v
    if isinstance(data, list) and data:
        total = 0.0
        found = False
        for item in data:
            if isinstance(item, dict):
                v = safe_float(
                    item.get("energy", item.get("energy_kwh", item.get("kwh")))
                )
                if v is not None:
                    total += v
                    found = True
        return total if found else None
    return None


def test_status_state_unwraps_and_finds_status_key():
    assert _status_state({"data": {"status": "connected"}}) == "connected"


def test_status_state_checks_key_priority_order():
    assert _status_state({"state": "idle", "connection": "online"}) == "idle"


def test_status_state_non_dict_returns_none():
    assert _status_state([1, 2]) is None


def test_status_state_no_matching_key_returns_none():
    assert _status_state({"foo": "bar"}) is None


def test_events_count_bare_list():
    assert _events_count([1, 2, 3]) == 3


def test_events_count_unwraps_data_envelope_list():
    assert _events_count({"data": [1, 2]}) == 2


def test_events_count_dict_events_key():
    assert _events_count({"events": [1, 2, 3, 4]}) == 4


def test_events_count_dict_items_key():
    assert _events_count({"items": [1]}) == 1


def test_events_count_no_list_field_returns_none():
    assert _events_count({"foo": "bar"}) is None


def test_events_count_none_returns_none():
    assert _events_count(None) is None


def test_charger_energy_kwh_dict_energy_kwh_key():
    assert _charger_energy_kwh({"energy_kwh": 12.5}) == 12.5


def test_charger_energy_kwh_unwraps_data_envelope():
    assert _charger_energy_kwh({"data": {"total": "7.5"}}) == 7.5


def test_charger_energy_kwh_key_priority_order():
    """'energy' is checked before 'total', even if both are present."""
    assert _charger_energy_kwh({"energy": 3.0, "total": 99.0}) == 3.0


def test_charger_energy_kwh_sums_list_of_dicts():
    payload = [{"energy": 1.0}, {"energy": 2.5}, {"kwh": 1.0}]
    assert _charger_energy_kwh(payload) == 4.5


def test_charger_energy_kwh_empty_list_returns_none():
    assert _charger_energy_kwh([]) is None


def test_charger_energy_kwh_list_without_numeric_fields_returns_none():
    assert _charger_energy_kwh([{"foo": "bar"}]) is None


def test_charger_energy_kwh_none_returns_none():
    assert _charger_energy_kwh(None) is None
