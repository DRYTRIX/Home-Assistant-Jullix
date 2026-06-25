"""Optional session history sensors (last recorded charge session)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_system
from ..session_history import SessionHistoryRecorder
from .base import JullixSensor


def create_session_history_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    recorder: SessionHistoryRecorder | None,
) -> list[JullixSensor]:
    """Expose the most recent stored charge session when history is enabled."""
    if recorder is None:
        return []
    return [
        JullixLastSessionEnergySensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            recorder=recorder,
            unique_id=f"{install_id}_last_session_energy",
            name="Last session energy",
            device_info=device_info_system(install_id, install_name),
            translation_key="last_session_energy",
        ),
        JullixLastSessionIdSensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            recorder=recorder,
            unique_id=f"{install_id}_last_session_id",
            name="Last session ID",
            device_info=device_info_system(install_id, install_name),
            translation_key="last_session_id",
        ),
    ]


def _last_session(
    recorder: SessionHistoryRecorder, install_id: str
) -> dict[str, Any] | None:
    return recorder.last_session_for(install_id)


class JullixLastSessionEnergySensor(JullixSensor):
    """Energy from the last stored charge session."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        recorder: SessionHistoryRecorder,
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
        self._recorder = recorder

    def _update_from_snapshot(self) -> None:
        row = _last_session(self._recorder, self._install_id)
        if row:
            self._attr_native_value = row.get("energy_kwh")
            self._attr_extra_state_attributes = {
                k: v
                for k, v in row.items()
                if k not in ("installation_id", "energy_kwh")
            }
        else:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}


class JullixLastSessionIdSensor(JullixSensor):
    """Session id of the last stored charge session."""

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        recorder: SessionHistoryRecorder,
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
        self._recorder = recorder

    def _update_from_snapshot(self) -> None:
        row = _last_session(self._recorder, self._install_id)
        self._attr_native_value = row.get("session_id") if row else None
