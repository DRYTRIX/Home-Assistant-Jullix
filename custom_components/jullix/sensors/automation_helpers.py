"""Sensors for tariff / charging automation (hourly price derived)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.util import dt as dt_util

from ..coordinator import JullixDataUpdateCoordinator
from ..derived import format_hour_hint, parse_hourly_tariff
from ..device_helpers import device_info_system
from .base import JullixSensor, get_installation_snapshot


def create_automation_helper_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    sys_dev = device_info_system(install_id, install_name)
    return [
        JullixRecommendedChargeTimeSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_recommended_charge_time",
            name="Recommended charge time",
            device_info=sys_dev,
            translation_key="recommended_charge_time",
        ),
        JullixCheapEnergyWindowSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_cheap_energy_window",
            name="Cheap energy window",
            device_info=sys_dev,
            translation_key="cheap_energy_window",
        ),
        JullixCurrentHourPriceSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_current_hour_price",
            name="Current hour price",
            device_info=sys_dev,
            translation_key="current_hour_price",
        ),
    ]


class JullixRecommendedChargeTimeSensor(JullixSensor):
    """Cheapest hour as local time string (for templates / automations)."""

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_hourly_tariff(
            snap.cost_hourly_price,
            reference_local=dt_util.now(),
        )
        if ins is None or ins.recommended_charge_hour is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return
        h = ins.recommended_charge_hour
        self._attr_native_value = format_hour_hint(h)
        self._attr_extra_state_attributes = {
            "hour": h,
            "cheapest_hour": ins.cheapest_hour,
            "peak_hour": ins.peak_hour,
        }


class JullixCheapEnergyWindowSensor(JullixSensor):
    """Cheap tariff window boundaries from hourly series."""

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_hourly_tariff(
            snap.cost_hourly_price,
            reference_local=dt_util.now(),
        )
        if ins is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return
        start = ins.cheap_window_start_hour
        end = ins.cheap_window_end_hour
        self._attr_native_value = (
            f"{start}-{end}" if start is not None and end is not None else None
        )
        self._attr_extra_state_attributes = {
            "start_hour": start,
            "end_hour": end,
            "prices_by_hour": ins.prices_by_hour,
        }


class JullixCurrentHourPriceSensor(JullixSensor):
    """Spot price for the current local hour when available."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_hourly_tariff(
            snap.cost_hourly_price,
            reference_local=dt_util.now(),
        )
        self._attr_native_value = ins.current_hour_price if ins else None
        self._attr_native_unit_of_measurement = "EUR/kWh"
