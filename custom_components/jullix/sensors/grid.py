"""Grid detail and capacity-tariff (captar) sensors."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_grid
from ..models.util import power_value_to_watts
from .base import JullixSensor, get_installation_snapshot


def create_grid_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    """Grid detail power + captar when data is present."""
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    grid_dev = device_info_grid(install_id, install_name)

    if snap.grid_detail.power_watts() is not None:
        entities.append(
            JullixGridDetailPowerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                unique_id=f"{install_id}_grid_power",
                name="Grid power",
                device_info=grid_dev,
                translation_key="grid_power",
            )
        )

    entities.append(
        JullixCaptarSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_summary_captar",
            name="Capacity tariff",
            device_info=grid_dev,
            translation_key="capacity_tariff",
        )
    )

    return entities


class JullixGridDetailPowerSensor(JullixSensor):
    """Grid power from detail endpoint (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        self._attr_native_value = snap.grid_detail.power_watts()


class JullixCaptarSensor(JullixSensor):
    """Capacity tariff from grid detail or summary (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        raw = snap.grid_detail.captar_actual_raw()
        val = power_value_to_watts(raw)
        if val is None:
            val = snap.power_summary.power_watts("captar")
        self._attr_native_value = val
