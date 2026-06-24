"""Extended charger API sensors (status, daily energy, events)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_charger
from ..models.util import safe_float, unwrap_data
from .base import JullixSensor, get_installation_snapshot


def _status_state(payload: Any) -> str | None:
    data = unwrap_data(payload)
    if isinstance(data, dict):
        for key in ("status", "state", "connection", "mode"):
            val = data.get(key)
            if val is not None:
                return str(val)
    return None


def _events_count(payload: Any) -> int | None:
    data = unwrap_data(payload)
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("events", "data", "items"):
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
    return None


def _charger_energy_kwh(payload: Any) -> float | None:
    data = unwrap_data(payload)
    if isinstance(data, dict):
        for key in ("energy", "energy_kwh", "total", "kwh", "total_energy"):
            v = safe_float(data.get(key))
            if v is not None:
                return v
    if isinstance(data, list) and data:
        total = 0.0
        found = False
        for item in data:
            if isinstance(item, dict):
                v = safe_float(
                    item.get("energy", item.get("energy_kwh", item.get("kwh")))
                )
                if v is not None:
                    total += v
                    found = True
        return total if found else None
    return None


def create_charger_extended_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    """Status, today energy, and event count per charger when extended API data exists."""
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    for ch in snap.chargers:
        mac = ch.mac
        model = ch.raw.get("model") or ch.raw.get("type")
        if model is not None:
            model = str(model)
        ch_dev = device_info_charger(
            install_id,
            install_name,
            mac,
            ch.display_name,
            model=model,
        )
        if mac in snap.charger_status_by_mac:
            entities.append(
                JullixChargerStatusSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    charger_mac=mac,
                    unique_id=f"{install_id}_charger_{mac}_status",
                    name="Status",
                    device_info=ch_dev,
                    translation_key="charger_status",
                )
            )
        if mac in snap.charger_energies_by_mac:
            entities.append(
                JullixChargerEnergyTodaySensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    charger_mac=mac,
                    unique_id=f"{install_id}_charger_{mac}_energy_today",
                    name="Energy today",
                    device_info=ch_dev,
                    translation_key="charger_energy_today",
                )
            )
        if mac in snap.charger_events_by_mac:
            entities.append(
                JullixChargerEventsSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    charger_mac=mac,
                    unique_id=f"{install_id}_charger_{mac}_events",
                    name="Events today",
                    device_info=ch_dev,
                    translation_key="charger_events",
                )
            )
    return entities


class JullixChargerStatusSensor(JullixSensor):
    """Charger connection/status from dedicated status endpoint."""

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        charger_mac: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._charger_mac = charger_mac

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        payload = snap.charger_status_by_mac.get(self._charger_mac)
        self._attr_native_value = _status_state(payload)
        data = unwrap_data(payload)
        self._attr_extra_state_attributes = data if isinstance(data, dict) else {}


class JullixChargerEnergyTodaySensor(JullixSensor):
    """Charger energy today (kWh) from energies endpoint."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        charger_mac: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._charger_mac = charger_mac

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        payload = snap.charger_energies_by_mac.get(self._charger_mac)
        self._attr_native_value = _charger_energy_kwh(payload)


class JullixChargerEventsSensor(JullixSensor):
    """Number of charger events returned by the events endpoint."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        charger_mac: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._charger_mac = charger_mac

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        payload = snap.charger_events_by_mac.get(self._charger_mac)
        self._attr_native_value = _events_count(payload)
        data = unwrap_data(payload)
        if isinstance(data, list):
            self._attr_extra_state_attributes = {"events": data[:20]}
        elif isinstance(data, dict):
            self._attr_extra_state_attributes = data
        else:
            self._attr_extra_state_attributes = {}
