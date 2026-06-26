"""Jullix-Direct local EMS sensors (grid meter detail, charger extras, water)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.helpers.device_registry import DeviceInfo

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import (
    device_info_charger,
    device_info_grid,
    device_info_system,
)
from ..models.local_ems import LocalEmsSnapshot
from .base import JullixSensor, get_installation_snapshot


def _local_charger_device(
    install_id: str,
    install_name: str,
    snap: Any,
) -> DeviceInfo:
    if snap.chargers:
        ch = snap.chargers[0]
        model = ch.raw.get("model") or ch.raw.get("type")
        return device_info_charger(
            install_id,
            install_name,
            ch.mac,
            ch.display_name,
            model=str(model) if model is not None else None,
        )
    if snap.charger_detail_rows:
        return device_info_charger(
            install_id,
            install_name,
            "local_0",
            "Charger",
        )
    return device_info_system(install_id, install_name)


def create_local_ems_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    """Register local EMS sensors when a Jullix-Direct host is configured."""
    snap = get_installation_snapshot(coordinator, install_id)
    grid_dev = device_info_grid(install_id, install_name)
    sys_dev = device_info_system(install_id, install_name)
    ch_dev = _local_charger_device(install_id, install_name, snap)

    specs: list[tuple[str, str, str, DeviceInfo, Callable[[LocalEmsSnapshot], Any]]] = [
        (
            f"{install_id}_local_grid_power_in",
            "Grid power in",
            "local_grid_power_in",
            grid_dev,
            lambda e: e.power_in_w,
        ),
        (
            f"{install_id}_local_grid_power_out",
            "Grid power out",
            "local_grid_power_out",
            grid_dev,
            lambda e: e.power_out_w,
        ),
        (
            f"{install_id}_local_net_power",
            "Net power",
            "local_net_power",
            grid_dev,
            lambda e: e.net_power_w,
        ),
        (
            f"{install_id}_local_energy_import_t1",
            "Energy import T1",
            "local_energy_import_t1",
            grid_dev,
            lambda e: e.energy_in_1_kwh,
        ),
        (
            f"{install_id}_local_energy_import_t2",
            "Energy import T2",
            "local_energy_import_t2",
            grid_dev,
            lambda e: e.energy_in_2_kwh,
        ),
        (
            f"{install_id}_local_energy_export_t1",
            "Energy export T1",
            "local_energy_export_t1",
            grid_dev,
            lambda e: e.energy_out_1_kwh,
        ),
        (
            f"{install_id}_local_energy_export_t2",
            "Energy export T2",
            "local_energy_export_t2",
            grid_dev,
            lambda e: e.energy_out_2_kwh,
        ),
        (
            f"{install_id}_local_voltage_l1",
            "Voltage L1",
            "local_voltage_l1",
            grid_dev,
            lambda e: e.voltage_l1,
        ),
        (
            f"{install_id}_local_voltage_l2",
            "Voltage L2",
            "local_voltage_l2",
            grid_dev,
            lambda e: e.voltage_l2,
        ),
        (
            f"{install_id}_local_voltage_l3",
            "Voltage L3",
            "local_voltage_l3",
            grid_dev,
            lambda e: e.voltage_l3,
        ),
        (
            f"{install_id}_local_water_usage",
            "Water usage",
            "local_water_usage",
            sys_dev,
            lambda e: e.water_m3,
        ),
        (
            f"{install_id}_local_ev_soc",
            "EV battery SOC",
            "local_ev_battery_soc",
            ch_dev,
            lambda e: e.charger_soc,
        ),
        (
            f"{install_id}_local_ev_temperature",
            "EV charger temperature",
            "local_ev_charger_temperature",
            ch_dev,
            lambda e: e.charger_temperature,
        ),
        (
            f"{install_id}_local_ev_max_current",
            "EV max current",
            "local_ev_max_current",
            ch_dev,
            lambda e: e.charger_max_current,
        ),
        (
            f"{install_id}_local_ev_state",
            "EV charger state",
            "local_charger_state",
            ch_dev,
            lambda e: e.charger_state,
        ),
    ]

    entities: list[JullixSensor] = []
    for unique_id, name, tkey, dev, value_fn in specs:
        entities.append(
            JullixLocalEmsSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                unique_id=unique_id,
                name=name,
                device_info=dev,
                translation_key=tkey,
                value_fn=value_fn,
                sensor_kind=tkey,
            )
        )
    return entities


class JullixLocalEmsSensor(JullixSensor):
    """Snapshot-backed local EMS field."""

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        unique_id: str,
        name: str,
        *,
        value_fn: Callable[[LocalEmsSnapshot], Any],
        sensor_kind: str,
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
        self._value_fn = value_fn
        self._sensor_kind = sensor_kind
        self._apply_device_class(sensor_kind)

    def _apply_device_class(self, kind: str) -> None:
        if kind in (
            "local_grid_power_in",
            "local_grid_power_out",
            "local_net_power",
        ):
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 0
        elif kind.startswith("local_energy_"):
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_suggested_display_precision = 2
        elif kind.startswith("local_voltage_"):
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif kind == "local_water_usage":
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
            self._attr_device_class = SensorDeviceClass.WATER
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif kind == "local_ev_battery_soc":
            self._attr_native_unit_of_measurement = "%"
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif kind == "local_ev_charger_temperature":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1
        elif kind == "local_ev_max_current":
            self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_state_class = SensorStateClass.MEASUREMENT

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        local = snap.local_ems
        try:
            self._attr_native_value = self._value_fn(local)
        except (TypeError, KeyError):
            self._attr_native_value = None

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        try:
            return self._value_fn(snap.local_ems) is not None
        except (TypeError, KeyError):
            return False
