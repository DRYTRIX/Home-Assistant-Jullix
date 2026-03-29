"""Battery SoC and power sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_battery
from .base import JullixSensor, get_installation_snapshot


def create_battery_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    """Battery SoC and per-unit power from snapshot."""
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    multi = len(snap.battery_slots) > 1

    for slot in snap.battery_slots:
        bat_dev = device_info_battery(
            install_id, install_name, slot.index, multi
        )
        if slot.soc is not None:
            entities.append(
                JullixBatterySocSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    battery_index=slot.index,
                    unique_id=f"{install_id}_battery_{slot.index}_soc",
                    name="State of charge",
                    device_info=bat_dev,
                    translation_key="battery_state_of_charge",
                )
            )
        if slot.power_watts is not None or "power" in slot.raw:
            entities.append(
                JullixBatteryPowerSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    battery_index=slot.index,
                    unique_id=f"{install_id}_battery_{slot.index}_power",
                    name="Power",
                    device_info=bat_dev,
                    translation_key="battery_power",
                )
            )

    return entities


class JullixBatterySocSensor(JullixSensor):
    """Battery state of charge (%)."""

    _attr_native_unit_of_measurement = "%"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        battery_index: int,
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
        self._battery_index = battery_index

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        slots = snap.battery_slots
        if 0 <= self._battery_index < len(slots):
            self._attr_native_value = slots[self._battery_index].soc
        else:
            self._attr_native_value = None


class JullixBatteryPowerSensor(JullixSensor):
    """Per-battery power (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        battery_index: int,
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
        self._battery_index = battery_index

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        slots = snap.battery_slots
        if 0 <= self._battery_index < len(slots):
            self._attr_native_value = slots[self._battery_index].power_watts
        else:
            self._attr_native_value = None
