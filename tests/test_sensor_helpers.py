"""Tests for Jullix plug energy parsing (models layer)."""

from __future__ import annotations

from custom_components.jullix.models.util import extract_plug_energy_total_kwh as _extract_plug_energy_total


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
