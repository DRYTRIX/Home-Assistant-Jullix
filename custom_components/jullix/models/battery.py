"""Battery stack snapshots."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .util import power_value_to_watts, safe_float

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatterySlot:
    """One battery unit (SoC, power, identifiers)."""

    index: int
    soc: float | None
    power_watts: float | None
    name: str | None
    localid: str | None
    id_value: str | None
    raw: dict[str, Any]

    def display_name(self, fallback: str) -> str:
        return self.name or self.localid or fallback


def parse_battery_detail(detail: Any) -> tuple[BatterySlot, ...]:
    """Parse battery detail API payload (list of devices or single dict)."""
    slots: list[BatterySlot] = []
    try:
        if isinstance(detail, dict):
            soc = safe_float(detail.get("soc"))
            if soc is not None or detail.get("power") is not None:
                inner = detail.get("battery") if isinstance(detail.get("battery"), dict) else {}
                soc = safe_float(inner.get("soc"), soc)
                pw = power_value_to_watts(detail.get("power"))
                slots.append(
                    BatterySlot(
                        index=0,
                        soc=soc,
                        power_watts=pw,
                        name=inner.get("name") if inner else detail.get("name"),
                        localid=str(inner.get("localid"))
                        if inner.get("localid") is not None
                        else None,
                        id_value=str(inner.get("id")) if inner.get("id") is not None else None,
                        raw=dict(detail),
                    )
                )
            return tuple(slots)
        if not isinstance(detail, list):
            return tuple(slots)
        for i, item in enumerate(detail):
            if not isinstance(item, dict):
                continue
            bat = item.get("battery") or {}
            if not isinstance(bat, dict):
                bat = {}
            soc = safe_float(bat.get("soc"))
            if soc is None:
                soc = safe_float(item.get("soc"))
            pw = power_value_to_watts(item.get("power"))
            name = item.get("name") or bat.get("name")
            localid = bat.get("localid")
            id_val = item.get("id") or bat.get("id")
            slots.append(
                BatterySlot(
                    index=i,
                    soc=soc,
                    power_watts=pw,
                    name=str(name) if name is not None else None,
                    localid=str(localid) if localid is not None else None,
                    id_value=str(id_val) if id_val is not None else None,
                    raw=dict(item),
                )
            )
    except (TypeError, ValueError) as e:
        _LOGGER.debug("Battery parse failed: %s", e)
    return tuple(slots)
