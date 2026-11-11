"""Tests for statistics period1/period2 parsing helpers."""

from __future__ import annotations

from custom_components.jullix.models.util import (
    extract_statistics_total_kwh,
    flatten_statistics_period,
    statistics_periods,
    truncate_state,
)

PERIOD_PAYLOAD = {
    "status": "ok",
    "statistics": {
        "period1": {
            "home": {"energy": 14.86},
            "solar": {"energy": 2.30},
            "grid": {"imported": 22.01, "injected": 0.21},
            "battery": {"energy_charged": 12.80, "energy_discharged": 5.80},
            "car": {"energy_charged": 0, "energy_discharged": 0},
            "gas": 0.91,
            "heatpump": None,
            "water": 0,
        },
        "period2": {
            "home": {"energy": 29.0},
            "solar": {"energy": 1.0},
            "grid": {"imported": 10.0, "injected": 0.5},
            "battery": {"energy_charged": 1.0, "energy_discharged": 2.0},
            "car": {"energy_charged": 0, "energy_discharged": 0},
            "gas": 1.2,
            "heatpump": None,
            "water": 0,
        },
    },
}


def test_extract_statistics_period1_home_energy():
    assert extract_statistics_total_kwh(PERIOD_PAYLOAD) == 14.86


def test_extract_statistics_legacy_total():
    assert extract_statistics_total_kwh({"total": 42.5}) == 42.5
    assert extract_statistics_total_kwh({"value": 3.0}) == 3.0


def test_extract_statistics_legacy_list():
    assert extract_statistics_total_kwh([{"energy": 1.0}, {"value": 2.0}]) == 3.0


def test_extract_statistics_none():
    assert extract_statistics_total_kwh(None) is None


def test_flatten_statistics_period():
    flat = flatten_statistics_period(PERIOD_PAYLOAD["statistics"]["period1"])
    assert flat["home"] == 14.86
    assert flat["solar_energy"] == 2.30
    assert flat["grid_imported"] == 22.01
    assert flat["grid_injected"] == 0.21
    assert flat["battery_energy_charged"] == 12.80
    assert flat["battery_energy_discharged"] == 5.80
    assert flat["gas"] == 0.91
    assert flat["heatpump"] is None
    assert flat["water"] == 0


def test_statistics_periods():
    p1, p2 = statistics_periods(PERIOD_PAYLOAD)
    assert p1 is not None and p1["home"]["energy"] == 14.86
    assert p2 is not None and p2["home"]["energy"] == 29.0


def test_truncate_state():
    assert truncate_state(None) is None
    assert truncate_state("ok") == "ok"
    long = "x" * 300
    assert len(truncate_state(long) or "") == 255
