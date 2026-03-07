"""Tests for Jullix coordinator (merge and data shape)."""

from __future__ import annotations

import pytest

from custom_components.jullix.coordinator import _merge_local_data


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
