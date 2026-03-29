"""Rolling sums from statistics daily API shapes."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..models.util import safe_float, unwrap_data


def _parse_day_key(item: dict[str, Any]) -> date | None:
    for key in ("date", "day", "d"):
        v = item.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            try:
                return date.fromisoformat(v[:10])
            except ValueError:
                continue
    y = item.get("year")
    m = item.get("month")
    d = item.get("day")
    if y is not None and m is not None and d is not None:
        try:
            return date(int(y), int(m), int(d))
        except (TypeError, ValueError):
            pass
    return None


def rolling_statistics_kwh_last_n_days(
    raw: Any,
    *,
    n_days: int = 7,
    today: date | None = None,
) -> float | None:
    """Sum energy (kWh) for the last N calendar days if payload has dated entries."""
    data = unwrap_data(raw)
    items: list[Any] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("data", "days", "values", "entries"):
            if isinstance(data.get(key), list):
                items = data[key]
                break

    if not items:
        return None

    day_vals: dict[date, float] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        d = _parse_day_key(item)
        if d is None:
            continue
        v = safe_float(
            item.get("value", item.get("energy", item.get("total", item.get("kwh"))))
        )
        if v is not None:
            day_vals[d] = v

    if not day_vals:
        return None

    end = today or date.today()
    start = end - timedelta(days=n_days - 1)
    total = 0.0
    any_hit = False
    d = start
    while d <= end:
        if d in day_vals:
            total += day_vals[d]
            any_hit = True
        d += timedelta(days=1)

    return total if any_hit else None
