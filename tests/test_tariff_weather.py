"""Tests for tariff unwrap and hourly weather selection (mirrored helpers)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.util import dt as dt_util

from custom_components.jullix.models.util import truncate_state


def _unwrap_tariff_payload(tariff: Any) -> Any:
    if isinstance(tariff, dict) and isinstance(tariff.get("tariff"), dict):
        return tariff["tariff"]
    return tariff


def _tariff_state(tariff: Any) -> str | None:
    tariff = _unwrap_tariff_payload(tariff)
    if isinstance(tariff, dict):
        for key in ("name", "description", "tariff_name"):
            val = tariff.get(key)
            if val is not None:
                return truncate_state(val)
        return truncate_state(tariff)
    if tariff is not None:
        return truncate_state(tariff)
    return None


def _parse_weather_row_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _weather_from_hourly_list(rows: list[Any]) -> tuple[Any, dict[str, Any]]:
    now = dt_util.utcnow()
    best: dict[str, Any] | None = None
    best_ts: datetime | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        ts = _parse_weather_row_time(row.get("time"))
        if ts is None or ts > now:
            continue
        if best_ts is None or ts >= best_ts:
            best = row
            best_ts = ts
    if best is None:
        for row in reversed(rows):
            if isinstance(row, dict):
                best = row
                break
    if best is None:
        return None, {}
    data = best.get("data") if isinstance(best.get("data"), dict) else best
    if not isinstance(data, dict):
        return truncate_state(data), {}
    state = data.get("temperature_2m", data.get("temperature"))
    attrs: dict[str, Any] = {}
    for src, dest in (
        ("cloud_cover", "cloud"),
        ("cloud", "cloud"),
        ("precipitation", "precipitation"),
        ("relative_humidity_2m", "humidity"),
        ("humidity", "humidity"),
        ("wind_speed_10m", "wind"),
        ("wind", "wind"),
        ("shortwave_radiation", "radiation"),
        ("radiation", "radiation"),
    ):
        if src in data and dest not in attrs:
            attrs[dest] = data.get(src)
    if best_ts is not None:
        attrs["time"] = best_ts.isoformat()
    return (truncate_state(state) if state is not None else None), attrs


def test_tariff_unwraps_nested_payload():
    payload = {"status": "ok", "tariff": {"name": "Dynamic", "description": "dyn"}}
    assert _tariff_state(payload) == "Dynamic"


def test_tariff_uses_description_when_no_name():
    assert _tariff_state({"tariff": {"description": "Peak/off-peak"}}) == "Peak/off-peak"


def test_tariff_truncates_long_fallback():
    long = "z" * 400
    assert len(_tariff_state({"tariff": {"other": long}}) or "") == 255


def test_weather_picks_latest_past_row():
    now = dt_util.utcnow()
    rows = [
        {
            "time": (now - timedelta(hours=2)).isoformat(),
            "data": {"temperature_2m": 10.0, "cloud": 20},
        },
        {
            "time": (now - timedelta(hours=1)).isoformat(),
            "data": {
                "temperature_2m": 12.5,
                "cloud_cover": 40,
                "precipitation": 0.1,
                "humidity": 70,
                "wind_speed_10m": 3.2,
                "shortwave_radiation": 100,
            },
        },
        {
            "time": (now + timedelta(hours=1)).isoformat(),
            "data": {"temperature_2m": 99.0},
        },
    ]
    state, attrs = _weather_from_hourly_list(rows)
    assert state == "12.5"
    assert attrs["cloud"] == 40
    assert attrs["precipitation"] == 0.1
    assert attrs["humidity"] == 70
    assert attrs["wind"] == 3.2
    assert attrs["radiation"] == 100
