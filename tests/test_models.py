"""Tests for Jullix domain models."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.jullix.models import (
    RawInstallFetches,
    build_installation_snapshot,
    parse_battery_detail,
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


def test_build_snapshot_empty_fetches():
    snap = build_installation_snapshot(RawInstallFetches())
    assert snap.power_summary.powers == {}
    assert snap.chargers == ()
