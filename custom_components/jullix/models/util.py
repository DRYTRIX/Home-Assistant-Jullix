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


def truncate_state(value: Any, max_len: int = 255) -> str | None:
    """Coerce to string for entity state; cap length for HA's 255-char limit."""
    if value is None:
        return None
    text = str(value)
    if len(text) > max_len:
        return text[:max_len]
    return text


def flatten_statistics_period(period: Any) -> dict[str, Any]:
    """Flatten a statistics period object into attribute-friendly keys."""
    if not isinstance(period, dict):
        return {}
    out: dict[str, Any] = {}

    home = period.get("home")
    if isinstance(home, dict):
        if "energy" in home:
            out["home"] = home.get("energy")
    elif home is not None:
        out["home"] = home

    solar = period.get("solar")
    if isinstance(solar, dict):
        if "energy" in solar:
            out["solar_energy"] = solar.get("energy")
    elif solar is not None:
        out["solar_energy"] = solar

    grid = period.get("grid")
    if isinstance(grid, dict):
        if "imported" in grid:
            out["grid_imported"] = grid.get("imported")
        if "injected" in grid:
            out["grid_injected"] = grid.get("injected")

    battery = period.get("battery")
    if isinstance(battery, dict):
        if "energy_charged" in battery:
            out["battery_energy_charged"] = battery.get("energy_charged")
        if "energy_discharged" in battery:
            out["battery_energy_discharged"] = battery.get("energy_discharged")

    car = period.get("car")
    if isinstance(car, dict):
        if "energy_charged" in car:
            out["car_energy_charged"] = car.get("energy_charged")
        if "energy_discharged" in car:
            out["car_energy_discharged"] = car.get("energy_discharged")

    for key in ("gas", "heatpump", "water"):
        if key in period:
            out[key] = period.get(key)

    return out


def _period1_home_energy(value: dict[str, Any]) -> float | None:
    """Extract period1.home.energy from current statistics shape."""
    stats = value.get("statistics", value)
    if not isinstance(stats, dict):
        return None
    period1 = stats.get("period1")
    if not isinstance(period1, dict):
        return None
    home = period1.get("home")
    if isinstance(home, dict):
        return safe_float(home.get("energy"))
    return safe_float(home)


def extract_statistics_total_kwh(value: Any) -> float | None:
    """Total kWh from statistics API response."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        period1_home = _period1_home_energy(value)
        if period1_home is not None:
            return period1_home
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
        # Nested envelope without period1 handled above
        if "statistics" in value and isinstance(value["statistics"], dict):
            nested = value["statistics"]
            total = nested.get("total", nested.get("value", nested.get("sum")))
            if total is not None:
                return safe_float(total)
    if isinstance(value, list):
        s = sum(
            safe_float(x.get("value", x.get("energy", x)) if isinstance(x, dict) else x)
            or 0
            for x in value
        )
        return s if s else None
    return None


def statistics_periods(value: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (period1, period2) dicts from a statistics API response."""
    if not isinstance(value, dict):
        return None, None
    stats = value.get("statistics", value)
    if not isinstance(stats, dict):
        return None, None
    p1 = stats.get("period1")
    p2 = stats.get("period2")
    return (
        p1 if isinstance(p1, dict) else None,
        p2 if isinstance(p2, dict) else None,
    )
