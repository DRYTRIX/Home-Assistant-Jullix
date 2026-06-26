"""Tests for Jullix-Direct local EMS parsing and entity value extraction."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.jullix.models import RawInstallFetches, build_installation_snapshot, merge_local_snapshot
from custom_components.jullix.models.local_ems import parse_local_ems

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "local_ems"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_parse_local_ems_full_fixture():
    local = {
        "meter": _load("meter.json"),
        "battery": _load("battery.json"),
        "charger": _load("charger.json"),
        "solar": _load("solar.json"),
    }
    ems = parse_local_ems(local)
    assert ems.power_in_w == 1500.0
    assert ems.power_out_w == 300.0
    assert ems.net_power_w == 1200.0
    assert ems.energy_in_1_kwh == 1234.5
    assert ems.energy_in_2_kwh == 567.8
    assert ems.energy_out_1_kwh == 90.1
    assert ems.energy_out_2_kwh == 12.3
    assert ems.voltage_l1 == 230.1
    assert ems.voltage_l2 == 231.0
    assert ems.voltage_l3 == 229.8
    assert ems.water_m3 == 42.5
    assert ems.battery_voltage == 51.2
    assert ems.battery_fault is False
    assert ems.solar_fault is False
    assert ems.charger_soc == 55.0
    assert ems.charger_temperature == 28.6
    assert ems.charger_max_current == 16.0
    assert ems.charger_state == "charging"
    assert ems.charger_busy is True
    assert ems.charger_three_phase is True


def test_parse_local_ems_empty():
    ems = parse_local_ems({})
    assert ems.has_meter_data() is False
    assert ems.has_charger_data() is False


def test_merge_local_snapshot_populates_local_ems():
    platform = build_installation_snapshot(RawInstallFetches(power_summary={"data": {"powers": {}}}))
    local = {
        "meter": _load("meter.json"),
        "battery": _load("battery.json"),
        "charger": _load("charger.json"),
        "solar": _load("solar.json"),
    }
    result = merge_local_snapshot(platform, local)
    assert result.local_ems.power_in_w == 1500.0
    assert result.local_ems.charger_busy is True
    assert result.battery_slots[0].voltage == 51.2
    assert result.battery_slots[0].fault is False
