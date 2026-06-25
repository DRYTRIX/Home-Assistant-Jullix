"""Tests for energy totals parsing."""

from __future__ import annotations

from custom_components.jullix.models.energy_totals import (
    EnergyTotalsSnapshot,
    build_energy_totals,
    parse_metering_energy_totals,
)


def test_parse_metering_grid_import_export():
    channels = (
        {"id": "grid_import", "energy": 1200.5, "unit": "kWh"},
        {"id": "grid_export", "energy": 45.2, "unit": "kWh"},
    )
    gi, ge, sol = parse_metering_energy_totals({}, channels)
    assert gi == 1200.5
    assert ge == 45.2
    assert sol is None


def test_build_energy_totals_from_local_ems():
    totals = build_energy_totals(
        metering_src={},
        metering_channels=(),
        local_meter_solar={
            "meter": {"energy_import": 500.0, "energy_export": 12.0},
            "solar": {"energy": 300.0},
        },
    )
    assert totals.grid_import_kwh == 500.0
    assert totals.grid_export_kwh == 12.0
    assert totals.solar_production_kwh == 300.0


def test_energy_totals_empty():
    assert EnergyTotalsSnapshot.empty().grid_import_kwh is None
