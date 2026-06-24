"""Extended algorithm API sensors (settings, results, usage, PV predict)."""

from __future__ import annotations

from typing import Any

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_system
from ..models.util import unwrap_data
from .base import JullixSensor, get_installation_snapshot


def _dict_summary(payload: Any, *keys: str) -> str | None:
    data = unwrap_data(payload)
    if isinstance(data, dict):
        for key in keys:
            val = data.get(key)
            if val is not None:
                return str(val)
        if len(data) == 1:
            return str(next(iter(data.values())))
    elif payload is not None:
        return str(payload)
    return None


def create_algorithm_extended_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    sys_dev = device_info_system(install_id, install_name)

    specs: list[tuple[Any, str, str, str]] = [
        (snap.algorithm_settings, "algorithm_settings", "Optimizer settings", "algorithm_settings"),
        (snap.algorithm_results, "algorithm_results", "Optimization results", "algorithm_results"),
        (snap.algorithm_usage, "algorithm_usage", "Usage model", "algorithm_usage"),
        (snap.algorithm_pvpredict, "algorithm_pvpredict", "Solar prediction", "algorithm_pvpredict"),
    ]
    for raw, suffix, label, tkey in specs:
        if raw is None:
            continue
        entities.append(
            JullixAlgorithmExtendedSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                field=suffix,
                unique_id=f"{install_id}_{suffix}",
                name=label,
                device_info=sys_dev,
                translation_key=tkey,
            )
        )
    return entities


class JullixAlgorithmExtendedSensor(JullixSensor):
    """Single-line summary from extended algorithm endpoints."""

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        field: str,
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
        self._field = field

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        payload = getattr(snap, self._field, None)
        self._attr_native_value = _dict_summary(
            payload, "status", "state", "mode", "enabled", "result", "summary"
        )
        data = unwrap_data(payload)
        self._attr_extra_state_attributes = data if isinstance(data, dict) else {}
