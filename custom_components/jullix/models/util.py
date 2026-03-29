"""Shared parsing helpers for Jullix API payloads."""

from __future__ import annotations

import logging
from typing import Any

from ..const import API_POWER_IN_KW

_LOGGER = logging.getLogger(__name__)


def safe_float(value: Any, default: float | None = None) -> float | None:
    """Coerce value to float; return default on failure."""
    if value is None:
        return default
    if isinstance(value, dict):
        if "power" in value:
            return safe_float(value["power"], default)
        if "import" in value or "export" in value:
            imp = safe_float(value.get("import"), 0) or 0
            exp = safe_float(value.get("export"), 0) or 0
            return imp - exp
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    """Coerce value to int; return default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def power_value_to_watts(value: Any) -> float | None:
    """Normalize power to watts (handles kW from API when API_POWER_IN_KW)."""
    if value is None:
        return None
    raw: float | None = None
    if isinstance(value, (int, float)):
        raw = float(value)
    elif isinstance(value, dict):
        if "power" in value:
            raw = safe_float(value["power"])
        elif "value" in value:
            raw = safe_float(value["value"])
        else:
            imp = safe_float(value.get("import"))
            exp = safe_float(value.get("export"))
            if imp is not None or exp is not None:
                raw = (imp or 0) - (exp or 0)
    if raw is None:
        return None
    if API_POWER_IN_KW:
        return raw * 1000.0
    return raw


def unwrap_data(raw: Any) -> Any:
    """Unwrap API envelope {\"data\": ...} or return payload as-is."""
    if isinstance(raw, dict) and "data" in raw:
        return raw.get("data", raw)
    return raw


def charger_mac_from_dict(ch: dict[str, Any], index: int) -> str:
    """Resolve charger MAC / id from API object."""
    return str(
        ch.get("id", ch.get("device_id", ch.get("mac", ch.get("mac_address", str(index)))))
    )


def charger_display_name(ch: dict[str, Any], index: int) -> str:
    """Human-readable charger name."""
    return str(
        ch.get("name", ch.get("description", ch.get("label", f"Charger {index + 1}")))
    )


def plug_mac_from_dict(plug: dict[str, Any], index: int) -> str:
    """Resolve plug MAC / id from API object."""
    return str(
        plug.get(
            "id",
            plug.get("device_id", plug.get("mac", plug.get("mac_address", str(index)))),
        )
    )


def plug_display_name(plug: dict[str, Any], index: int) -> str:
    """Human-readable plug name."""
    return str(
        plug.get("name", plug.get("description", plug.get("label", f"Plug {index + 1}")))
    )


def extract_plug_energy_total_kwh(value: Any) -> float | None:
    """Total kWh from plug energy API response."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        if "total" in value:
            return safe_float(value["total"])
        if "value" in value:
            return safe_float(value["value"])
        if "energy" in value:
            return safe_float(value["energy"])
        if "data" in value:
            return extract_plug_energy_total_kwh(value["data"])
    if isinstance(value, list):
        total = 0.0
        for item in value:
            if isinstance(item, (int, float)):
                total += float(item)
            elif isinstance(item, dict):
                v = item.get("value", item.get("energy", item.get("total")))
                if v is not None:
                    try:
                        total += float(v)
                    except (TypeError, ValueError):
                        pass
        return total if total else None
    return None


def extract_statistics_total_kwh(value: Any) -> float | None:
    """Total kWh from statistics API response."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        total = value.get("total", value.get("value", value.get("sum")))
        if total is not None:
            return safe_float(total)
        for key in ("data", "values", "entries"):
            if key in value and isinstance(value[key], list):
                s = sum(
                    safe_float(
                        x.get("value", x.get("energy", x)) if isinstance(x, dict) else x
                    )
                    or 0
                    for x in value[key]
                )
                return s if s else None
    if isinstance(value, list):
        s = sum(
            safe_float(x.get("value", x.get("energy", x)) if isinstance(x, dict) else x)
            or 0
            for x in value
        )
        return s if s else None
    return None
