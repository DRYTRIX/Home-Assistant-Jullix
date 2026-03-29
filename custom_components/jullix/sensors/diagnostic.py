"""Diagnostic sensors: API health and refresh timing."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from ..api import JullixAuthError
from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_system
from .base import JullixSensor


def create_diagnostic_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[SensorEntity]:
    """Connection health, latency, last success timestamp."""
    sys_dev = device_info_system(install_id, install_name)
    return [
        JullixConnectionHealthSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_connection_health",
            name="Connection health",
            device_info=sys_dev,
            translation_key="connection_health",
        ),
        JullixApiLatencySensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_api_latency",
            name="API latency",
            device_info=sys_dev,
            translation_key="api_latency",
        ),
        JullixLastUpdateSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=f"{install_id}_last_successful_update",
            name="Last successful update",
            device_info=sys_dev,
            translation_key="last_successful_update",
        ),
    ]


class JullixConnectionHealthSensor(JullixSensor):
    """ok / degraded / auth_error."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def _update_from_snapshot(self) -> None:
        err = self.coordinator.last_installation_errors.get(self._install_id)
        if isinstance(err, JullixAuthError):
            self._attr_native_value = "auth_error"
        elif err is not None:
            self._attr_native_value = "degraded"
        else:
            self._attr_native_value = "ok"


class JullixApiLatencySensor(JullixSensor):
    """Last refresh round-trip for this installation (ms)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_suggested_display_precision = 0

    def _update_from_snapshot(self) -> None:
        m = self.coordinator.install_metrics.get(self._install_id)
        self._attr_native_value = m.last_latency_ms if m else None


class JullixLastUpdateSensor(JullixSensor):
    """UTC timestamp of last successful snapshot build."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def _update_from_snapshot(self) -> None:
        m = self.coordinator.install_metrics.get(self._install_id)
        self._attr_native_value = m.last_success_at if m else None
