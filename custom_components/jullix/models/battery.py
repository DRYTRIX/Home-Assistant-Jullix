"""Battery stack snapshots."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Any

from .util import power_value_to_watts, safe_float, unwrap_data

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatterySlot:
    """One battery unit (SoC, power, cumulative energy, identifiers)."""

    index: int
    soc: float | None
    power_watts: float | None
    energy_charged_kwh: float | None
    energy_discharged_kwh: float | None
    voltage: float | None
    fault: bool | None
    name: str | None
    localid: str | None
    id_value: str | None
    raw: dict[str, Any]

    def display_name(self, fallback: str) -> str:
        return self.name or self.localid or fallback


def _energy_kwh_from_item(item: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract cumulative charged/discharged kWh from one battery payload dict."""
    charged = safe_float(item.get("energy_charged"))
    if charged is None:
        charged = safe_float(item.get("charged"))
    discharged = safe_float(item.get("energy_discharged"))
    if discharged is None:
        discharged = safe_float(item.get("discharged"))
    bat = item.get("battery")
    if isinstance(bat, dict):
        if charged is None:
            charged = safe_float(bat.get("energy_charged")) or safe_float(bat.get("charged"))
        if discharged is None:
            discharged = safe_float(bat.get("energy_discharged")) or safe_float(
                bat.get("discharged")
            )
    return charged, discharged


def _slot_from_item(item: dict[str, Any], index: int) -> BatterySlot:
    bat = item.get("battery") or {}
    if not isinstance(bat, dict):
        bat = {}
    soc = safe_float(bat.get("soc"))
    if soc is None:
        soc = safe_float(item.get("soc"))
    pw = power_value_to_watts(item.get("power"))
    charged, discharged = _energy_kwh_from_item(item)
    voltage = safe_float(bat.get("voltage"))
    if voltage is None:
        voltage = safe_float(item.get("voltage"))
    fault: bool | None = None
    if "fault" in bat:
        fault = bool(bat["fault"])
    elif "fault" in item:
        fault = bool(item["fault"])
    name = item.get("name") or bat.get("name")
    localid = bat.get("localid")
    id_val = item.get("id") or bat.get("id")
    return BatterySlot(
        index=index,
        soc=soc,
        power_watts=pw,
        energy_charged_kwh=charged,
        energy_discharged_kwh=discharged,
        voltage=voltage,
        fault=fault,
        name=str(name) if name is not None else None,
        localid=str(localid) if localid is not None else None,
        id_value=str(id_val) if id_val is not None else None,
        raw=dict(item),
    )


def parse_battery_detail(detail: Any) -> tuple[BatterySlot, ...]:
    """Parse battery detail API payload (list of devices or single dict)."""
    slots: list[BatterySlot] = []
    try:
        detail = unwrap_data(detail)
        if isinstance(detail, dict):
            soc = safe_float(detail.get("soc"))
            charged, discharged = _energy_kwh_from_item(detail)
            if (
                soc is not None
                or detail.get("power") is not None
                or charged is not None
                or discharged is not None
            ):
                slots.append(_slot_from_item(detail, 0))
            return tuple(slots)
        if not isinstance(detail, list):
            return tuple(slots)
        for i, item in enumerate(detail):
            if isinstance(item, dict):
                slots.append(_slot_from_item(item, i))
    except (TypeError, ValueError) as e:
        _LOGGER.debug("Battery parse failed: %s", e)
    return tuple(slots)


def parse_battery_energy_history(raw: Any) -> tuple[float | None, float | None]:
    """Extract cumulative battery charged/discharged kWh from cloud history API."""
    if raw is None:
        return None, None
    data = unwrap_data(raw)
    if isinstance(data, dict):
        charged, discharged = _energy_kwh_from_item(data)
        if charged is not None or discharged is not None:
            return charged, discharged
        for key in ("devices", "batteries", "entries", "values"):
            nested = data.get(key)
            if isinstance(nested, list):
                data = nested
                break
        else:
            return None, None
    if isinstance(data, list):
        total_charged = 0.0
        total_discharged = 0.0
        found_charged = False
        found_discharged = False
        for item in data:
            if not isinstance(item, dict):
                continue
            charged, discharged = _energy_kwh_from_item(item)
            if charged is not None:
                total_charged += charged
                found_charged = True
            if discharged is not None:
                total_discharged += discharged
                found_discharged = True
        return (
            total_charged if found_charged else None,
            total_discharged if found_discharged else None,
        )
    return None, None


def _history_item_for_slot(
    slot: BatterySlot, history_items: list[Any]
) -> dict[str, Any] | None:
    """Match a history row to a battery slot by localid or id."""
    for item in history_items:
        if not isinstance(item, dict):
            continue
        bat = item.get("battery")
        if not isinstance(bat, dict):
            bat = item
        item_localid = bat.get("localid") or item.get("localid")
        item_id = item.get("id") or bat.get("id")
        if slot.localid and item_localid and str(slot.localid) == str(item_localid):
            return item
        if slot.id_value and item_id and str(slot.id_value) == str(item_id):
            return item
    return None


def backfill_battery_slot_energy(
    slots: tuple[BatterySlot, ...], history_raw: Any
) -> tuple[BatterySlot, ...]:
    """Fill missing per-slot energy totals from cloud battery energy history."""
    if not slots or history_raw is None:
        return slots

    data = unwrap_data(history_raw)
    if isinstance(data, list) and data:
        updated: list[BatterySlot] = []
        for slot in slots:
            item = _history_item_for_slot(slot, data)
            if item is None and len(data) == len(slots):
                item = data[slot.index] if isinstance(data[slot.index], dict) else None
            if not isinstance(item, dict):
                updated.append(slot)
                continue
            hist_charged, hist_discharged = _energy_kwh_from_item(item)
            updated.append(
                replace(
                    slot,
                    energy_charged_kwh=slot.energy_charged_kwh
                    if slot.energy_charged_kwh is not None
                    else hist_charged,
                    energy_discharged_kwh=slot.energy_discharged_kwh
                    if slot.energy_discharged_kwh is not None
                    else hist_discharged,
                )
            )
        if any(
            s.energy_charged_kwh is not None or s.energy_discharged_kwh is not None
            for s in updated
        ):
            return tuple(updated)

    hist_charged, hist_discharged = parse_battery_energy_history(history_raw)
    if len(slots) == 1 and (hist_charged is not None or hist_discharged is not None):
        slot = slots[0]
        return (
            replace(
                slot,
                energy_charged_kwh=slot.energy_charged_kwh
                if slot.energy_charged_kwh is not None
                else hist_charged,
                energy_discharged_kwh=slot.energy_discharged_kwh
                if slot.energy_discharged_kwh is not None
                else hist_discharged,
            ),
        )
    return slots
