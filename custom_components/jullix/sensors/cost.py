"""Cost, savings, and monthly total sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_system
from ..models.util import safe_float
from .base import JullixSensor, get_installation_snapshot


def create_cost_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    sys_dev = device_info_system(install_id, install_name)
    raw = snap.cost_savings.raw
    cost_specs = (
        ("savings", "Savings", "cost_savings"),
        ("total", "Total cost", "cost_total_line"),
        ("total_cost", "Total cost", "cost_total_cost_line"),
    )
    for key, label, tkey in cost_specs:
        val = raw.get(key)
        if safe_float(val) is not None or (
            isinstance(val, dict) and "value" in val
        ):
            entities.append(
                JullixCostSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    key=key,
                    unique_id=f"{install_id}_cost_{key}",
                    name=label,
                    device_info=sys_dev,
                    translation_key=tkey,
                )
            )
    if snap.cost_total.raw is not None or snap.cost_total.total is not None:
        entities.append(
            JullixCostTotalSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                unique_id=f"{install_id}_cost_total_month",
                name="Cost this month",
                device_info=sys_dev,
                translation_key="cost_month_total",
            )
        )
    return entities


class JullixCostSensor(JullixSensor):
    """Cost / savings numeric values."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_currency = "EUR"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        key: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator,
            install_id,
            install_name,
            unique_id,
            name,
            **kwargs,
        )
        self._key = key

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        val = snap.cost_savings.raw.get(self._key)
        if isinstance(val, dict):
            val = val.get("value", val.get("amount"))
        self._attr_native_value = safe_float(val)


class JullixCostTotalSensor(JullixSensor):
    """Total cost this month."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_currency = "EUR"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator,
            install_id,
            install_name,
            unique_id,
            name,
            **kwargs,
        )

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        self._attr_native_value = snap.cost_total.total
        if self._attr_native_value is None and isinstance(snap.cost_total.raw, dict):
            self._attr_native_value = safe_float(
                snap.cost_total.raw.get(
                    "total",
                    snap.cost_total.raw.get("value", snap.cost_total.raw.get("amount")),
                )
            )
