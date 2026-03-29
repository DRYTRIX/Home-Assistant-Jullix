"""Derived energy insight percentage sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE

from ..coordinator import JullixDataUpdateCoordinator
from ..derived import compute_energy_insight_ratios, rolling_statistics_kwh_last_n_days
from ..device_helpers import device_info_power_overview
from .base import JullixSensor, get_installation_snapshot


def create_insight_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    *,
    enable_statistics_roll: bool,
) -> list[JullixSensor]:
    """Instantaneous insight % sensors and optional rolling 7-day energy."""
    power_dev = device_info_power_overview(install_id, install_name)
    entities: list[JullixSensor] = [
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
    if enable_statistics_roll:
        entities.append(
            JullixRolling7dEnergySensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                unique_id=f"{install_id}_statistics_energy_7d",
                name="Energy rolling 7 days",
                device_info=power_dev,
                translation_key="statistics_energy_7d",
            )
        )
    return entities


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


class JullixRolling7dEnergySensor(JullixSensor):
    """Sum of dated daily statistics rows for last 7 days when API provides them."""

    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        self._attr_native_value = rolling_statistics_kwh_last_n_days(
            snap.statistics_energy_daily,
            n_days=7,
        )
