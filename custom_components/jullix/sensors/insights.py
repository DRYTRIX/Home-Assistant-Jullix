"""Derived energy insight percentage sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import PERCENTAGE

from ..coordinator import JullixDataUpdateCoordinator
from ..derived import compute_energy_insight_ratios
from ..device_helpers import device_info_power_overview
from .base import JullixSensor, get_installation_snapshot


def create_insight_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    *,
    enable_statistics_roll: bool,
) -> list[JullixSensor]:
    """Instantaneous insight % sensors.

    Rolling 7-day energy is no longer created: the statistics API returns
    period1/period2 aggregates, not dated daily rows.
    """
    del enable_statistics_roll  # retained for call-site compatibility
    power_dev = device_info_power_overview(install_id, install_name, hass=coordinator.hass)
    return [
        JullixSelfConsumptionSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_insight_self_consumption",
            name="Self-consumption",
            device_info=power_dev,
            translation_key="insight_self_consumption",
        ),
        JullixSolarUtilizationSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_insight_solar_utilization",
            name="Solar utilization",
            device_info=power_dev,
            translation_key="insight_solar_utilization",
        ),
        JullixGridDependencySensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_insight_grid_dependency",
            name="Grid dependency",
            device_info=power_dev,
            translation_key="insight_grid_dependency",
        ),
    ]


class _InsightPercentSensor(JullixSensor):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    _insight_key: str

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ratios = compute_energy_insight_ratios(snap)
        val = getattr(ratios, self._insight_key)
        self._attr_native_value = val


class JullixSelfConsumptionSensor(_InsightPercentSensor):
    _insight_key = "self_consumption_pct"


class JullixSolarUtilizationSensor(_InsightPercentSensor):
    _insight_key = "solar_utilization_pct"


class JullixGridDependencySensor(_InsightPercentSensor):
    _insight_key = "grid_dependency_pct"
