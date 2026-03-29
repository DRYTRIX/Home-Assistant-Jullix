"""Smart plug list and installation plug energy."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .util import extract_plug_energy_total_kwh, plug_display_name, plug_mac_from_dict, unwrap_data

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlugDevice:
    """One plug from installation list."""

    index: int
    mac: str
    display_name: str
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return dict(self.raw)


def parse_plugs_list(data: Any) -> tuple[PlugDevice, ...]:
    """Normalize get_plugs response."""
    out: list[PlugDevice] = []
    try:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "plugs" in data:
            items = data["plugs"]
            if not isinstance(items, list):
                items = []
        else:
            items = []
        for i, plug in enumerate(items):
            if not isinstance(plug, dict):
                continue
            mac = plug_mac_from_dict(plug, i)
            out.append(
                PlugDevice(
                    index=i,
                    mac=mac,
                    display_name=plug_display_name(plug, i),
                    raw=dict(plug),
                )
            )
    except (TypeError, ValueError) as e:
        _LOGGER.debug("Plugs list parse failed: %s", e)
    return tuple(out)


def parse_plug_energy_today(raw: Any) -> tuple[Any, float | None]:
    """Return raw (for attributes) and total kWh if computable."""
    if raw is None:
        return (None, None)
    data = unwrap_data(raw)
    kwh = extract_plug_energy_total_kwh(data)
    return (data, kwh)
