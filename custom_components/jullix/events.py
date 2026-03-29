"""Fire Home Assistant bus events on meaningful Jullix transitions."""

from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_SOC_EMPTY_PCT,
    BATTERY_SOC_FULL_PCT,
    CHARGER_ACTIVE_POWER_W,
    CHARGER_IDLE_POWER_W,
    DOMAIN,
    EVENT_JULLIX,
    GRID_OUTAGE_CONSECUTIVE_POLLS,
    GRID_OUTAGE_IDLE_W,
    GRID_OUTAGE_IMPORT_THRESHOLD_W,
)
from .models import JullixInstallationSnapshot
from .runtime_state import InstallEdgeState

_LOGGER = logging.getLogger(__name__)


def _grid_import_w(snap: JullixInstallationSnapshot) -> float | None:
    gw = snap.power_summary.power_watts("grid")
    if gw is None:
        return None
    return max(0.0, gw)


def _first_battery_soc(snap: JullixInstallationSnapshot) -> float | None:
    if not snap.battery_slots:
        return None
    return snap.battery_slots[0].soc


def edge_state_from_snapshot(
    snap: JullixInstallationSnapshot,
    *,
    prev: InstallEdgeState | None = None,
) -> InstallEdgeState:
    """Snapshot-derived edge state without firing events."""
    macs = dict(prev.charger_power_by_mac if prev else {})
    for ch in snap.chargers:
        macs[ch.mac] = snap.charger_power_watts(ch.index) or 0.0
    return InstallEdgeState(
        charger_power_by_mac=macs,
        battery_soc=_first_battery_soc(snap),
        grid_import_w=_grid_import_w(snap),
        grid_low_streak=prev.grid_low_streak if prev else 0,
        in_grid_outage=prev.in_grid_outage if prev else False,
    )


def detect_and_fire_events(
    hass: HomeAssistant,
    install_id: str,
    snap: JullixInstallationSnapshot,
    prev: InstallEdgeState | None,
    last_error: Exception | None,
) -> InstallEdgeState:
    """Compare snapshot to prev edge state; fire jullix_event for edges; return new state."""
    if last_error is not None:
        if prev is not None:
            return prev
        return edge_state_from_snapshot(snap)

    new_state = InstallEdgeState(
        charger_power_by_mac=dict(prev.charger_power_by_mac if prev else {}),
        battery_soc=_first_battery_soc(snap),
        grid_import_w=_grid_import_w(snap),
        grid_low_streak=prev.grid_low_streak if prev else 0,
        in_grid_outage=prev.in_grid_outage if prev else False,
    )

    # Charger started / stopped (per MAC)
    for ch in snap.chargers:
        mac = ch.mac
        pw = snap.charger_power_watts(ch.index) or 0.0
        old = new_state.charger_power_by_mac.get(mac)
        if old is None:
            new_state.charger_power_by_mac[mac] = pw
            continue
        new_state.charger_power_by_mac[mac] = pw
        if old < CHARGER_ACTIVE_POWER_W <= pw:
            hass.bus.async_fire(
                EVENT_JULLIX,
                {
                    "type": "charger_started",
                    "domain": DOMAIN,
                    "installation_id": install_id,
                    "charger_mac": mac,
                    "power_w": pw,
                },
            )
        elif old >= CHARGER_ACTIVE_POWER_W > pw and pw <= CHARGER_IDLE_POWER_W:
            hass.bus.async_fire(
                EVENT_JULLIX,
                {
                    "type": "charger_stopped",
                    "domain": DOMAIN,
                    "installation_id": install_id,
                    "charger_mac": mac,
                    "power_w": pw,
                },
            )

    # Battery SoC thresholds (first stack)
    soc = new_state.battery_soc
    if soc is not None and prev and prev.battery_soc is not None:
        if prev.battery_soc < BATTERY_SOC_FULL_PCT <= soc:
            hass.bus.async_fire(
                EVENT_JULLIX,
                {
                    "type": "battery_full",
                    "domain": DOMAIN,
                    "installation_id": install_id,
                    "soc": soc,
                },
            )
        if prev.battery_soc > BATTERY_SOC_EMPTY_PCT >= soc:
            hass.bus.async_fire(
                EVENT_JULLIX,
                {
                    "type": "battery_empty",
                    "domain": DOMAIN,
                    "installation_id": install_id,
                    "soc": soc,
                },
            )

    # Grid outage / reconnect (consecutive low-import polls; best-effort heuristic)
    imp = new_state.grid_import_w
    if imp is not None:
        if imp <= GRID_OUTAGE_IDLE_W:
            new_state.grid_low_streak = (prev.grid_low_streak if prev else 0) + 1
        else:
            new_state.grid_low_streak = 0

        if (
            not new_state.in_grid_outage
            and new_state.grid_low_streak >= GRID_OUTAGE_CONSECUTIVE_POLLS
        ):
            new_state.in_grid_outage = True
            hass.bus.async_fire(
                EVENT_JULLIX,
                {
                    "type": "grid_outage",
                    "domain": DOMAIN,
                    "installation_id": install_id,
                    "grid_import_w": imp,
                },
            )
        elif new_state.in_grid_outage and imp > GRID_OUTAGE_IMPORT_THRESHOLD_W:
            new_state.in_grid_outage = False
            new_state.grid_low_streak = 0
            hass.bus.async_fire(
                EVENT_JULLIX,
                {
                    "type": "grid_reconnect",
                    "domain": DOMAIN,
                    "installation_id": install_id,
                    "grid_import_w": imp,
                },
            )

    return new_state


