"""Extended algorithm API sensors (settings, results, usage, PV predict)."""

from __future__ import annotations

from typing import Any

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_system
from ..models.util import truncate_state, unwrap_data
from .base import JullixSensor, get_installation_snapshot


def _dict_summary(payload: Any, *keys: str) -> str | None:
    data = unwrap_data(payload)
    if isinstance(data, dict):
        for key in keys:
            val = data.get(key)
            if val is not None:
                return truncate_state(val)
        if len(data) == 1:
            return truncate_state(next(iter(data.values())))
    elif payload is not None:
        return truncate_state(payload)
    return None


def _pvpredict_empty(payload: Any) -> bool:
    """True when pvpredict returned no forecast series."""
    data = unwrap_data(payload)
    if not isinstance(data, dict):
        return payload is not None and payload == []
    predict = data.get("predict", data.get("forecast"))
    solar = data.get("solar")
    run = data.get("run")
    predict_empty = isinstance(predict, list) and len(predict) == 0
    solar_empty = solar is None or (isinstance(solar, list) and len(solar) == 0)
    # Match observed empty shape: {"predict": [], "solar": [], "run": null}
    if predict_empty and solar_empty:
        return True
    if predict_empty and run is None and "predict" in data:
        return True
    return False


def create_algorithm_extended_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    sys_dev = device_info_system(install_id, install_name, hass=coordinator.hass)

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
        self._attr_available = True

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        payload = getattr(snap, self._field, None)
        data = unwrap_data(payload)

        if self._field == "algorithm_pvpredict":
            if _pvpredict_empty(payload):
                self._attr_available = False
                self._attr_native_value = None
                attrs: dict[str, Any] = {"reason": "empty_prediction"}
                if isinstance(data, dict):
                    attrs.update({k: data.get(k) for k in ("predict", "solar", "run") if k in data})
                self._attr_extra_state_attributes = attrs
                return
            self._attr_available = True
            # Prefer a compact summary when series exist
            if isinstance(data, dict):
                predict = data.get("predict", data.get("forecast"))
                if isinstance(predict, list) and predict:
                    self._attr_native_value = truncate_state(f"{len(predict)} points")
                    self._attr_extra_state_attributes = (
                        data if isinstance(data, dict) else {}
                    )
                    return
            self._attr_native_value = _dict_summary(
                payload, "status", "state", "mode", "enabled", "result", "summary"
            )
            self._attr_extra_state_attributes = data if isinstance(data, dict) else {}
            return

        self._attr_available = True
        self._attr_native_value = _dict_summary(
            payload, "status", "state", "mode", "enabled", "result", "summary"
        )
        self._attr_extra_state_attributes = data if isinstance(data, dict) else {}
