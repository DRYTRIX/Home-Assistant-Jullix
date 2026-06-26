"""Battery SoC, power, and cumulative energy sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfElectricPotential, UnitOfPower

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_battery
from .base import JullixSensor, get_installation_snapshot


def create_battery_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    *,
    local_host: str | None = None,
) -> list[JullixSensor]:
    """Battery SoC, power, and cumulative energy from snapshot."""
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
        if slot.energy_charged_kwh is not None or "energy_charged" in slot.raw:
            entities.append(
                JullixBatteryEnergyChargedSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    battery_index=slot.index,
                    unique_id=f"{install_id}_battery_{slot.index}_energy_charged",
                    name="Energy charged",
                    device_info=bat_dev,
                    translation_key="battery_energy_charged",
                )
            )
        if slot.energy_discharged_kwh is not None or "energy_discharged" in slot.raw:
            entities.append(
                JullixBatteryEnergyDischargedSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    battery_index=slot.index,
                    unique_id=f"{install_id}_battery_{slot.index}_energy_discharged",
                    name="Energy discharged",
                    device_info=bat_dev,
                    translation_key="battery_energy_discharged",
                )
            )
        if (
            slot.voltage is not None
            or "voltage" in slot.raw
            or (local_host and slot.index == 0)
        ):
            entities.append(
                JullixBatteryVoltageSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    battery_index=slot.index,
                    unique_id=f"{install_id}_battery_{slot.index}_voltage",
                    name="Voltage",
                    device_info=bat_dev,
                    translation_key="battery_voltage",
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


class JullixBatteryEnergyChargedSensor(JullixSensor):
    """Cumulative battery charge energy (kWh)."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
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
            self._attr_native_value = slots[self._battery_index].energy_charged_kwh
        else:
            self._attr_native_value = None


class JullixBatteryEnergyDischargedSensor(JullixSensor):
    """Cumulative battery discharge energy (kWh)."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
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
            self._attr_native_value = slots[self._battery_index].energy_discharged_kwh
        else:
            self._attr_native_value = None


class JullixBatteryVoltageSensor(JullixSensor):
    """Battery voltage (V)."""

    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_device_class = SensorDeviceClass.VOLTAGE
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
            voltage = slots[self._battery_index].voltage
            if voltage is None and self._battery_index == 0:
                voltage = snap.local_ems.battery_voltage
            self._attr_native_value = voltage
        else:
            self._attr_native_value = None

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        slots = snap.battery_slots
        if 0 <= self._battery_index < len(slots):
            slot = slots[self._battery_index]
            if slot.voltage is not None:
                return True
            if self._battery_index == 0 and snap.local_ems.battery_voltage is not None:
                return True
        return False
