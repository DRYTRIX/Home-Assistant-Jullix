"""Charger list and per-charger control payloads."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .util import charger_display_name, charger_mac_from_dict, unwrap_data

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChargerDevice:
    """One charger from installation list."""

    index: int
    mac: str
    display_name: str
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Shape expected by legacy code paths (mutable copy)."""
        return dict(self.raw)


def parse_chargers_list(data: Any) -> tuple[ChargerDevice, ...]:
    """Normalize get_chargers response to ChargerDevice tuple."""
    out: list[ChargerDevice] = []
    try:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "chargers" in data:
            items = data["chargers"]
            if not isinstance(items, list):
                items = []
        else:
            items = []
        for i, ch in enumerate(items):
            if not isinstance(ch, dict):
                continue
            mac = charger_mac_from_dict(ch, i)
            out.append(
                ChargerDevice(
                    index=i,
                    mac=mac,
                    display_name=charger_display_name(ch, i),
                    raw=dict(ch),
                )
            )
    except (TypeError, ValueError) as e:
        _LOGGER.debug("Chargers list parse failed: %s", e)
    return tuple(out)


def parse_charger_control_payload(raw: Any) -> dict[str, Any]:
    """Inner control dict for one MAC (unwrap data envelope)."""
    data = unwrap_data(raw)
    return dict(data) if isinstance(data, dict) else {}
