"""Tests for jullix_event edge detection."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.jullix.const import DOMAIN, EVENT_JULLIX
from custom_components.jullix.events import detect_and_fire_events, edge_state_from_snapshot
from custom_components.jullix.models import RawInstallFetches, build_installation_snapshot
from custom_components.jullix.runtime_state import InstallEdgeState


def test_charger_started_fires_event():
    snap_low = build_installation_snapshot(
        RawInstallFetches(
            power_summary={"data": {"powers": {}}},
            chargers_response=[{"id": "m1", "name": "C1", "power": 0.05}],
        )
    )
    snap_high = build_installation_snapshot(
        RawInstallFetches(
            power_summary={"data": {"powers": {}}},
            chargers_response=[{"id": "m1", "name": "C1", "power": 7.4}],
        )
    )
    hass = MagicMock()
    prev = edge_state_from_snapshot(snap_low)
    detect_and_fire_events(hass, "inst-1", snap_high, prev, None)
    hass.bus.async_fire.assert_called()
    types = [c.args[0] for c in hass.bus.async_fire.call_args_list]
    assert EVENT_JULLIX in types
    payload = hass.bus.async_fire.call_args[0][1]
    assert payload.get("type") == "charger_started"
    assert payload.get("installation_id") == "inst-1"
    assert payload.get("domain") == DOMAIN


def test_fetch_error_preserves_prev_edge_state():
    snap = build_installation_snapshot(
        RawInstallFetches(chargers_response=[{"id": "m1", "power": 7.4}])
    )
    hass = MagicMock()
    prev = edge_state_from_snapshot(snap)
    out = detect_and_fire_events(hass, "inst-1", snap, prev, RuntimeError("fail"))
    assert out is prev
    hass.bus.async_fire.assert_not_called()


def test_grid_outage_after_two_low_polls():
    snap_high = build_installation_snapshot(
        RawInstallFetches(power_summary={"data": {"powers": {"grid": 2.0}}})
    )
    snap_low = build_installation_snapshot(
        RawInstallFetches(power_summary={"data": {"powers": {"grid": 0.01}}})
    )
    hass = MagicMock()
    s0 = InstallEdgeState()
    s1 = detect_and_fire_events(hass, "i", snap_high, s0, None)
    assert not hass.bus.async_fire.called
    s2 = detect_and_fire_events(hass, "i", snap_low, s1, None)
    assert not hass.bus.async_fire.called
    s3 = detect_and_fire_events(hass, "i", snap_low, s2, None)
    hass.bus.async_fire.assert_called()
    assert hass.bus.async_fire.call_args[0][1]["type"] == "grid_outage"
    s4 = detect_and_fire_events(hass, "i", snap_high, s3, None)
    assert hass.bus.async_fire.call_args_list[-1][0][1]["type"] == "grid_reconnect"
