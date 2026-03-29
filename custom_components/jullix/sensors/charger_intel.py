"""Charge session and cost estimate sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy

from ..coordinator import JullixDataUpdateCoordinator
from ..derived import (
    estimate_session_cost_eur,
    parse_chargersession,
    parse_hourly_tariff,
)
from ..device_helpers import device_info_system
from .base import JullixSensor, get_installation_snapshot


def create_charger_intel_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    sys_dev = device_info_system(install_id, install_name)
    return [
        JullixSessionIdSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_charger_session_id",
            name="Active charge session",
            device_info=sys_dev,
            translation_key="charger_session_id",
        ),
        JullixSessionEnergySensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_charger_session_energy",
            name="Session energy",
            device_info=sys_dev,
            translation_key="charger_session_energy",
        ),
        JullixSessionCostSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_charger_session_cost_estimate",
            name="Session cost estimate",
            device_info=sys_dev,
            translation_key="charger_session_cost_estimate",
        ),
        JullixChargingSuggestionSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_charging_suggestion",
            name="Charging suggestion",
            device_info=sys_dev,
            translation_key="charging_suggestion",
        ),
    ]


class JullixSessionIdSensor(JullixSensor):
    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_chargersession(snap.chargersession_raw)
        self._attr_native_value = ins.session_id if ins else None
        self._attr_extra_state_attributes = (
            {"state": ins.state, "charger_mac": ins.charger_mac} if ins else {}
        )


class JullixSessionEnergySensor(JullixSensor):
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_chargersession(snap.chargersession_raw)
        self._attr_native_value = ins.energy_kwh if ins else None


class JullixSessionCostSensor(JullixSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 4

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_chargersession(snap.chargersession_raw)
        tariff = parse_hourly_tariff(snap.cost_hourly_price)
        avg = 0.0
        if tariff and tariff.prices_by_hour:
            vals = list(tariff.prices_by_hour.values())
            avg = sum(vals) / len(vals)
        cost = estimate_session_cost_eur(
            ins.energy_kwh if ins else None,
            avg,
        )
        self._attr_native_value = cost
        self._attr_native_unit_of_measurement = "EUR"


class JullixChargingSuggestionSensor(JullixSensor):
    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_chargersession(snap.chargersession_raw)
        tariff = parse_hourly_tariff(snap.cost_hourly_price)
        algo = snap.algorithm_overview
        parts: list[str] = []
        if isinstance(algo, dict):
            st = algo.get("status", algo.get("state"))
            if st:
                parts.append(f"Optimizer: {st}")
        if ins and ins.session_id and ins.energy_kwh is not None:
            parts.append(f"Session {ins.energy_kwh:.2f} kWh")
        if tariff and tariff.recommended_charge_hour is not None:
            parts.append(f"Prefer charging around {tariff.recommended_charge_hour}:00")
        if tariff and tariff.is_peak_now:
            parts.append("Current hour is near peak price")
        self._attr_native_value = "; ".join(parts) if parts else None
