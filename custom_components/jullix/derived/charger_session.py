"""Charge session summary from installation session API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.util import safe_float, unwrap_data


@dataclass(frozen=True)
class ChargerSessionInsight:
    """Best-effort active session fields (API shape may vary)."""

    session_id: str | None
    energy_kwh: float | None
    charger_mac: str | None
    state: str | None
    raw_active: dict[str, Any] | None


def _pick_sessions_list(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("sessions", "data", "items", "active", "current"):
            v = data.get(key)
            if isinstance(v, list):
                return v
        return [data]
    return []


def parse_chargersession(raw: Any) -> ChargerSessionInsight | None:
    """Pick the most likely active session from the installation chargersession payload."""
    data = unwrap_data(raw)
    sessions = _pick_sessions_list(data)
    if not sessions:
        return None

    active: dict[str, Any] | None = None
    for s in sessions:
        if not isinstance(s, dict):
            continue
        st = str(s.get("state", s.get("status", ""))).lower()
        if st in ("active", "charging", "running", "in_progress", "open"):
            active = s
            break
    if active is None:
        for s in sessions:
            if isinstance(s, dict):
                active = s
                break
    if active is None:
        return None

    sid = active.get("id", active.get("session_id", active.get("sessionId")))
    e = safe_float(
        active.get(
            "energy",
            active.get(
                "energy_kwh",
                active.get("kwh", active.get("total_energy", active.get("charged"))),
            ),
        )
    )
    mac = active.get("charger_mac", active.get("chargerMac", active.get("charger_id")))
    state = active.get("state", active.get("status"))

    return ChargerSessionInsight(
        session_id=str(sid) if sid is not None else None,
        energy_kwh=e,
        charger_mac=str(mac) if mac is not None else None,
        state=str(state) if state is not None else None,
        raw_active=dict(active),
    )


def estimate_session_cost_eur(energy_kwh: float | None, avg_price_eur_per_kwh: float) -> float | None:
    """Rough cost if average dynamic price is known."""
    if energy_kwh is None or avg_price_eur_per_kwh <= 0:
        return None
    return round(energy_kwh * avg_price_eur_per_kwh, 4)
