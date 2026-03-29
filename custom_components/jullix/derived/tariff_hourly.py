"""Parse hourly dynamic tariff payloads for automation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from ..models.util import safe_float, unwrap_data


@dataclass(frozen=True)
class HourlyTariffInsight:
    """Cheapest/peak hours and whether the current hour looks like peak."""

    prices_by_hour: dict[int, float]
    cheapest_hour: int | None
    peak_hour: int | None
    recommended_charge_hour: int | None
    cheap_window_start_hour: int | None
    cheap_window_end_hour: int | None
    current_hour_price: float | None
    is_peak_now: bool


def _iter_hour_rows(raw: Any) -> list[tuple[int, float]]:
    rows: list[tuple[int, float]] = []
    data = unwrap_data(raw)
    items: list[Any]
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = (
            data.get("hours")
            or data.get("data")
            or data.get("prices")
            or data.get("values")
            or []
        )
        if isinstance(items, dict):
            items = [{"hour": k, **(v if isinstance(v, dict) else {"price": v})} for k, v in items.items()]
    else:
        return rows

    if not isinstance(items, list):
        return rows

    for item in items:
        if isinstance(item, (int, float)):
            continue
        if not isinstance(item, dict):
            continue
        h = item.get("hour")
        if h is None and "h" in item:
            h = item.get("h")
        if h is None:
            continue
        try:
            hi = int(h)
        except (TypeError, ValueError):
            continue
        p = safe_float(
            item.get(
                "price",
                item.get("eur", item.get("value", item.get("cost", item.get("amount")))),
            )
        )
        if p is not None:
            rows.append((hi % 24, p))
    return rows


def parse_hourly_tariff(
    raw: Any,
    *,
    reference_local: datetime | None = None,
) -> HourlyTariffInsight | None:
    """Build insight from API hourly price payload; None if no parsable rows."""
    rows = _iter_hour_rows(raw)
    if not rows:
        return None

    by_h: dict[int, float] = {}
    for h, p in rows:
        by_h[h] = p

    if not by_h:
        return None

    min_p = min(by_h.values())
    max_p = max(by_h.values())
    cheap_hours = sorted(h for h, p in by_h.items() if p <= min_p + 1e-9)
    peak_hours = sorted(h for h, p in by_h.items() if p >= max_p - 1e-9)

    cheap_start = cheap_hours[0] if cheap_hours else None
    cheap_end = cheap_hours[-1] if cheap_hours else None

    now = reference_local or datetime.now().astimezone()
    ch = now.hour
    cur = by_h.get(ch)
    is_peak = cur is not None and max_p > 0 and cur >= max_p * 0.98

    return HourlyTariffInsight(
        prices_by_hour=dict(by_h),
        cheapest_hour=cheap_hours[0] if cheap_hours else None,
        peak_hour=peak_hours[0] if peak_hours else None,
        recommended_charge_hour=cheap_hours[0] if cheap_hours else None,
        cheap_window_start_hour=cheap_start,
        cheap_window_end_hour=cheap_end,
        current_hour_price=cur,
        is_peak_now=bool(is_peak),
    )


def format_hour_hint(hour: int | None, day: date | None = None) -> str | None:
    """Human-readable local time for automations."""
    if hour is None:
        return None
    t = time(hour=hour, minute=0)
    if day:
        return datetime.combine(day, t).isoformat()
    return t.isoformat(timespec="minutes")
