"""Per-charger power sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_charger
from .base import JullixSensor, get_installation_snapshot


def create_charger_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    for ch in snap.chargers:
        model = ch.raw.get("model") or ch.raw.get("type")
        if model is not None:
            model = str(model)
        ch_dev = device_info_charger(
            install_id,
            install_name,
            ch.mac,
            ch.display_name,
            model=model,
        )
        entities.append(
            JullixChargerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                charger_index=ch.index,
                charger_mac=ch.mac,
                unique_id=f"{install_id}_charger_{ch.mac}",
                name="Power",
                device_info=ch_dev,
                translation_key="charger_power",
            )
        )
    return entities


class JullixChargerSensor(JullixSensor):
    """Charger power (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        charger_index: int,
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
        self._charger_index = charger_index
        self._charger_mac = charger_mac

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        self._attr_native_value = snap.charger_power_watts(self._charger_index)
