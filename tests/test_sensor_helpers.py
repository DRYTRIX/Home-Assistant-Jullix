"""Tests for Jullix sensor helper functions."""

from __future__ import annotations

from typing import Any

import pytest


def _safe_float(value: Any, default: float | None = None) -> float | None:
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_plug_energy_total(value: Any) -> float | None:
    """Mirror of sensor._extract_plug_energy_total: extract total from plug energy response."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        if "total" in value:
            return _safe_float(value["total"])
        if "value" in value:
            return _safe_float(value["value"])
        if "energy" in value:
            return _safe_float(value["energy"])
        if "data" in value:
            return _extract_plug_energy_total(value["data"])
    if isinstance(value, list):
        total = 0.0
        for item in value:
            if isinstance(item, (int, float)):
                total += float(item)
            elif isinstance(item, dict):
                v = item.get("value", item.get("energy", item.get("total")))
                if v is not None:
                    total += float(v)
        return total if total else None
    return None


def test_extract_plug_energy_total_none():
    """_extract_plug_energy_total returns None for None."""
    assert _extract_plug_energy_total(None) is None


def test_extract_plug_energy_total_number():
    """_extract_plug_energy_total returns float for number."""
    assert _extract_plug_energy_total(10.5) == 10.5
    assert _extract_plug_energy_total(100) == 100.0


def test_extract_plug_energy_total_dict_total():
    """_extract_plug_energy_total uses 'total' key."""
    assert _extract_plug_energy_total({"total": 25.0}) == 25.0


def test_extract_plug_energy_total_dict_value():
    """_extract_plug_energy_total uses 'value' key."""
    assert _extract_plug_energy_total({"value": 3.14}) == 3.14


def test_extract_plug_energy_total_dict_energy():
    """_extract_plug_energy_total uses 'energy' key."""
    assert _extract_plug_energy_total({"energy": 7.0}) == 7.0


def test_extract_plug_energy_total_list_sum():
    """_extract_plug_energy_total sums list of numbers/dicts."""
    assert _extract_plug_energy_total([1.0, 2.0, 3.0]) == 6.0
    assert _extract_plug_energy_total([{"value": 1}, {"value": 2}]) == 3.0


def test_extract_plug_energy_total_nested_data():
    """_extract_plug_energy_total unwraps 'data' key."""
    assert _extract_plug_energy_total({"data": {"total": 42.0}}) == 42.0
