"""Dynamic entity discovery when chargers or plugs appear after setup."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .models import JullixInstallationSnapshot

_LOGGER = logging.getLogger(__name__)

EntityFactory = Callable[
    [str, JullixInstallationSnapshot],
    list[Any],
]


class JullixEntityDiscovery:
    """Track known devices and add entities when new hardware appears."""

    def __init__(self) -> None:
        self._known_chargers: dict[str, set[str]] = {}
        self._known_plugs: dict[str, set[str]] = {}
        self._initial_done = False
        self._listeners: dict[str, list[tuple[EntityFactory, Callable[[list[Any]], None]]]] = {
            "sensor": [],
            "switch": [],
            "select": [],
            "number": [],
        }

    def register_platform(
        self,
        platform: str,
        factory: EntityFactory,
        async_add_entities: Callable[[list[Any]], None],
    ) -> None:
        """Register a platform factory invoked when new devices are found."""
        self._listeners.setdefault(platform, []).append((factory, async_add_entities))

    def mark_initial(self, install_id: str, snap: JullixInstallationSnapshot) -> None:
        """Record devices present at platform setup (may be called per platform)."""
        self._known_chargers.setdefault(install_id, set()).update(
            c.mac for c in snap.chargers
        )
        self._known_plugs.setdefault(install_id, set()).update(p.mac for p in snap.plugs)

    def finalize_initial(self) -> None:
        """Enable dynamic discovery after all platforms finished initial setup."""
        self._initial_done = True

    def async_process_snapshot(
        self,
        install_id: str,
        snap: JullixInstallationSnapshot,
    ) -> None:
        """Add entities for chargers/plugs that were not present at setup."""
        if not self._initial_done:
            return

        new_charger_macs = {c.mac for c in snap.chargers} - self._known_chargers.get(
            install_id, set()
        )
        new_plug_macs = {p.mac for p in snap.plugs} - self._known_plugs.get(
            install_id, set()
        )
        if not new_charger_macs and not new_plug_macs:
            return

        if new_charger_macs:
            self._known_chargers.setdefault(install_id, set()).update(new_charger_macs)
            _LOGGER.info(
                "New charger(s) detected for %s: %s",
                install_id,
                ", ".join(sorted(new_charger_macs)),
            )
        if new_plug_macs:
            self._known_plugs.setdefault(install_id, set()).update(new_plug_macs)
            _LOGGER.info(
                "New plug(s) detected for %s: %s",
                install_id,
                ", ".join(sorted(new_plug_macs)),
            )

        filtered = _filter_snapshot_for_new_devices(
            snap, new_charger_macs, new_plug_macs
        )
        if filtered is None:
            return

        for platform, entries in self._listeners.items():
            for factory, async_add in entries:
                try:
                    entities = factory(install_id, filtered)
                except Exception as exc:
                    _LOGGER.warning(
                        "Entity discovery factory failed platform=%s install=%s: %s",
                        platform,
                        install_id,
                        exc,
                    )
                    continue
                if entities:
                    async_add(entities)


def _filter_snapshot_for_new_devices(
    snap: JullixInstallationSnapshot,
    new_charger_macs: set[str],
    new_plug_macs: set[str],
) -> JullixInstallationSnapshot | None:
    """Build a minimal snapshot view containing only new devices."""
    from dataclasses import replace

    if not new_charger_macs and not new_plug_macs:
        return None

    chargers = tuple(c for c in snap.chargers if c.mac in new_charger_macs)
    plugs = tuple(p for p in snap.plugs if p.mac in new_plug_macs)
    charger_control = {
        mac: snap.charger_control[mac]
        for mac in new_charger_macs
        if mac in snap.charger_control
    }
    charger_status = {
        mac: snap.charger_status_by_mac[mac]
        for mac in new_charger_macs
        if mac in snap.charger_status_by_mac
    }
    charger_events = {
        mac: snap.charger_events_by_mac[mac]
        for mac in new_charger_macs
        if mac in snap.charger_events_by_mac
    }
    charger_energies = {
        mac: snap.charger_energies_by_mac[mac]
        for mac in new_charger_macs
        if mac in snap.charger_energies_by_mac
    }
    plug_energy = {
        mac: snap.energy_totals.plug_energy_kwh_by_mac[mac]
        for mac in new_plug_macs
        if mac in snap.energy_totals.plug_energy_kwh_by_mac
    }

    return replace(
        snap,
        chargers=chargers if chargers else snap.chargers[:0],
        plugs=plugs if plugs else snap.plugs[:0],
        charger_control=charger_control,
        charger_status_by_mac=charger_status,
        charger_events_by_mac=charger_events,
        charger_energies_by_mac=charger_energies,
        energy_totals=replace(
            snap.energy_totals,
            plug_energy_kwh_by_mac=plug_energy,
            charger_energy_kwh_by_mac={
                mac: snap.energy_totals.charger_energy_kwh_by_mac[mac]
                for mac in new_charger_macs
                if mac in snap.energy_totals.charger_energy_kwh_by_mac
            },
        ),
    )
