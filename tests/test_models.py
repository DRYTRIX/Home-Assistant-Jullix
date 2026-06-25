"""Tests for Jullix domain models."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.jullix.models import (
    RawInstallFetches,
    backfill_battery_slot_energy,
    build_installation_snapshot,
    parse_battery_detail,
    parse_battery_energy_history,
)
from custom_components.jullix.models.summary import PowerSummarySnapshot

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "api"


def test_power_summary_from_fixture():
    raw = json.loads((FIXTURES / "power_summary.json").read_text())
    ps = PowerSummarySnapshot.from_api(raw)
    assert ps.power_watts("solar") == 2000.0


def test_battery_detail_from_fixture():
    raw = json.loads((FIXTURES / "battery_detail.json").read_text())
    data = raw.get("data", raw)
    slots = parse_battery_detail(data)
    assert len(slots) == 1
    assert slots[0].soc == 85.0
    assert slots[0].power_watts == 1200.0
    assert slots[0].energy_charged_kwh == 1523.4
    assert slots[0].energy_discharged_kwh == 1401.7


def test_battery_detail_unwraps_envelope():
    raw = json.loads((FIXTURES / "battery_detail.json").read_text())
    slots = parse_battery_detail(raw)
    assert len(slots) == 1
    assert slots[0].energy_charged_kwh == 1523.4


def test_battery_energy_history_from_fixture():
    raw = json.loads((FIXTURES / "battery_energy_history.json").read_text())
    charged, discharged = parse_battery_energy_history(raw)
    assert charged == 1523.4
    assert discharged == 1401.7


def test_backfill_battery_slot_energy_single_slot():
    slots = parse_battery_detail(
        [{"name": "Pack A", "power": 1.0, "battery": {"soc": 50.0}}]
    )
    history = json.loads((FIXTURES / "battery_energy_history.json").read_text())
    filled = backfill_battery_slot_energy(slots, history)
    assert filled[0].energy_charged_kwh == 1523.4
    assert filled[0].energy_discharged_kwh == 1401.7


def test_build_snapshot_backfills_battery_energy_from_history():
    detail = json.loads((FIXTURES / "battery_detail.json").read_text())
    history = json.loads((FIXTURES / "battery_energy_history.json").read_text())
    detail["data"][0].pop("energy_charged")
    detail["data"][0].pop("energy_discharged")
    snap = build_installation_snapshot(
        RawInstallFetches(
            detail_battery=detail,
            battery_energy_history=history,
        )
    )
    assert len(snap.battery_slots) == 1
    assert snap.battery_slots[0].energy_charged_kwh == 1523.4
    assert snap.battery_slots[0].energy_discharged_kwh == 1401.7


def test_build_snapshot_empty_fetches():
    snap = build_installation_snapshot(RawInstallFetches())
    assert snap.power_summary.powers == {}
    assert snap.chargers == ()
