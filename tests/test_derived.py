"""Tests for derived insight and tariff parsers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from custom_components.jullix.derived import (
    compute_energy_insight_ratios,
    parse_chargersession,
    parse_hourly_tariff,
    rolling_statistics_kwh_last_n_days,
)
from custom_components.jullix.models import RawInstallFetches, build_installation_snapshot

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "api"


def test_energy_insights_from_power_summary_fixture():
    raw = json.loads((FIXTURES / "power_summary.json").read_text())
    snap = build_installation_snapshot(RawInstallFetches(power_summary=raw))
    r = compute_energy_insight_ratios(snap)
    assert r.self_consumption_pct == 100.0
    assert r.solar_utilization_pct == 100.0
    assert r.grid_dependency_pct is not None
    assert r.grid_dependency_pct > 0


def test_energy_insights_no_solar():
    snap = build_installation_snapshot(
        RawInstallFetches(
            power_summary={"data": {"powers": {"grid": 0.5, "solar": 0, "home": 1.5}}}
        )
    )
    r = compute_energy_insight_ratios(snap)
    assert r.self_consumption_pct is None


def test_parse_hourly_tariff_fixture():
    raw = json.loads((FIXTURES / "cost_hourly_price.json").read_text())
    ins = parse_hourly_tariff(
        raw,
        reference_local=datetime(2026, 3, 15, 15, 30, 0),
    )
    assert ins is not None
    assert ins.cheapest_hour == 0
    assert ins.peak_hour == 15
    assert ins.recommended_charge_hour == 0
    assert ins.current_hour_price == 0.38
    assert ins.is_peak_now is True


def test_parse_chargersession_fixture():
    raw = json.loads((FIXTURES / "chargersession.json").read_text())
    cs = parse_chargersession(raw)
    assert cs is not None
    assert cs.session_id == "sess-abc"
    assert cs.energy_kwh == 12.5


def test_rolling_statistics_7d():
    raw = {
        "data": [
            {"date": "2026-03-23", "value": 10},
            {"date": "2026-03-24", "value": 5},
            {"date": "2026-03-29", "value": 3},
        ]
    }
    total = rolling_statistics_kwh_last_n_days(
        raw,
        n_days=7,
        today=__import__("datetime").date(2026, 3, 29),
    )
    assert total == 18.0
