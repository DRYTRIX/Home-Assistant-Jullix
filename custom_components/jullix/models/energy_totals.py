"""Cumulative energy totals for Energy Dashboard (grid, solar, devices)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .util import extract_plug_energy_total_kwh, safe_float, unwrap_data

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnergyTotalsSnapshot:
    """Normalized cumulative kWh totals per installation."""

    grid_import_kwh: float | None = None
    grid_export_kwh: float | None = None
    solar_production_kwh: float | None = None
    charger_energy_kwh_by_mac: dict[str, float] = field(default_factory=dict)
    plug_energy_kwh_by_mac: dict[str, float] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> EnergyTotalsSnapshot:
        return cls()


def _energy_from_dict(data: dict[str, Any]) -> float | None:
    for key in (
        "energy",
        "energy_kwh",
        "total_energy",
        "total",
        "kwh",
        "production",
        "energy_production",
        "energy_total",
    ):
        val = safe_float(data.get(key))
        if val is not None:
            return val
    return None


def _match_channel_id(ch_id: str, *needles: str) -> bool:
    low = ch_id.lower().replace("-", "_").replace(" ", "_")
    return any(n in low for n in needles)


def parse_metering_energy_totals(
    metering_src: dict[str, Any],
    channels: tuple[dict[str, Any], ...],
) -> tuple[float | None, float | None, float | None]:
    """Extract grid import/export and solar production kWh from metering."""
    grid_import: float | None = None
    grid_export: float | None = None
    solar: float | None = None

    for ch in channels:
        ch_id = str(ch.get("id", ch.get("channel_id", ch.get("name", ""))))
        if not _metering_channel_is_energy(ch):
            continue
        val = safe_float(ch.get("energy", ch.get("value")))
        if val is None:
            continue
        if _match_channel_id(ch_id, "import", "grid_in", "grid_import", "from_grid"):
            grid_import = val
        elif _match_channel_id(ch_id, "export", "grid_out", "grid_export", "to_grid"):
            grid_export = val
        elif _match_channel_id(ch_id, "solar", "pv", "production"):
            solar = val

    for key, val in metering_src.items():
        if not isinstance(val, (int, float, dict)):
            continue
        key_l = str(key).lower()
        if isinstance(val, dict):
            e = _energy_from_dict(val)
        else:
            e = safe_float(val)
        if e is None:
            continue
        if _match_channel_id(key_l, "import", "grid_in"):
            grid_import = grid_import if grid_import is not None else e
        elif _match_channel_id(key_l, "export", "grid_out"):
            grid_export = grid_export if grid_export is not None else e
        elif _match_channel_id(key_l, "solar", "pv"):
            solar = solar if solar is not None else e

    return grid_import, grid_export, solar


def _metering_channel_is_energy(channel: dict[str, Any]) -> bool:
    unit = str(channel.get("unit", "")).lower().replace(" ", "")
    if "kwh" in unit or "mwh" in unit:
        return True
    if unit.endswith("wh") and "kw" not in unit:
        return True
    energy_v = channel.get("energy")
    power_v = channel.get("power")
    if energy_v is not None and power_v is None:
        return True
    if "kw" in unit and "h" not in unit:
        return False
    if unit in ("w", "watt", "watts", "kw"):
        return False
    return bool(energy_v is not None)


def parse_local_ems_energy_totals(
    local_data: dict[str, Any],
) -> tuple[float | None, float | None, float | None]:
    """Parse cumulative kWh from Jullix-Direct EMS meter/solar payloads."""
    grid_import = grid_export = solar = None
    meter = unwrap_data(local_data.get("meter"))
    if isinstance(meter, dict):
        grid_import = safe_float(
            meter.get("energy_import", meter.get("import_energy", meter.get("import")))
        )
        grid_export = safe_float(
            meter.get("energy_export", meter.get("export_energy", meter.get("export")))
        )
        if grid_import is None:
            grid_import = _energy_from_dict(meter) if _match_channel_id(
                str(meter.get("type", "")), "import", "grid"
            ) else None
    solar_raw = unwrap_data(local_data.get("solar"))
    if isinstance(solar_raw, dict):
        solar = _energy_from_dict(solar_raw)
    elif isinstance(solar_raw, list) and solar_raw and isinstance(solar_raw[0], dict):
        solar = _energy_from_dict(solar_raw[0])
    return grid_import, grid_export, solar


def parse_statistics_energy_categories(stats_raw: Any) -> tuple[float | None, float | None, float | None]:
    """Best-effort grid/solar totals from statistics API breakdown."""
    data = unwrap_data(stats_raw)
    grid_import = grid_export = solar = None
    if not isinstance(data, (dict, list)):
        return None, None, None

    def _walk(node: Any) -> None:
        nonlocal grid_import, grid_export, solar
        if isinstance(node, dict):
            label = str(
                node.get("category", node.get("type", node.get("name", node.get("key", ""))))
            ).lower()
            val = safe_float(
                node.get("value", node.get("energy", node.get("total", node.get("kwh"))))
            )
            if val is not None:
                if _match_channel_id(label, "import", "grid_in", "from_grid"):
                    grid_import = val
                elif _match_channel_id(label, "export", "grid_out", "to_grid"):
                    grid_export = val
                elif _match_channel_id(label, "solar", "pv", "production"):
                    solar = val
            for v in node.values():
                if isinstance(v, (dict, list)):
                    _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(data)
    return grid_import, grid_export, solar


def parse_charger_energy_totals(
    energies_by_mac: dict[str, Any],
) -> dict[str, float]:
    """Per-charger energy totals from extended energies API."""
    out: dict[str, float] = {}
    for mac, payload in energies_by_mac.items():
        data = unwrap_data(payload)
        if isinstance(data, dict):
            for key in ("total_energy", "energy_total", "lifetime", "cumulative"):
                v = safe_float(data.get(key))
                if v is not None:
                    out[str(mac)] = v
                    break
            else:
                v = safe_float(
                    data.get("energy", data.get("energy_kwh", data.get("total", data.get("kwh"))))
                )
                if v is not None:
                    out[str(mac)] = v
        elif isinstance(data, list):
            v = extract_plug_energy_total_kwh(data)
            if v is not None:
                out[str(mac)] = v
    return out


def parse_plug_energy_by_mac(raw_by_mac: dict[str, Any]) -> dict[str, float]:
    """Per-plug cumulative kWh from plug energy API responses."""
    out: dict[str, float] = {}
    for mac, payload in raw_by_mac.items():
        v = extract_plug_energy_total_kwh(unwrap_data(payload))
        if v is not None:
            out[str(mac)] = v
    return out


def build_energy_totals(
    *,
    metering_src: dict[str, Any],
    metering_channels: tuple[dict[str, Any], ...],
    statistics_daily: Any = None,
    charger_energies_by_mac: dict[str, Any] | None = None,
    plug_energy_by_mac: dict[str, Any] | None = None,
    solar_detail_raw: dict[str, Any] | None = None,
    local_meter_solar: dict[str, Any] | None = None,
) -> EnergyTotalsSnapshot:
    """Combine metering, statistics, device APIs, and local EMS into totals."""
    gi, ge, sol = parse_metering_energy_totals(metering_src, metering_channels)

    if local_meter_solar:
        l_gi, l_ge, l_sol = parse_local_ems_energy_totals(local_meter_solar)
        gi = gi if gi is not None else l_gi
        ge = ge if ge is not None else l_ge
        sol = sol if sol is not None else l_sol

    if statistics_daily is not None:
        s_gi, s_ge, s_sol = parse_statistics_energy_categories(statistics_daily)
        gi = gi if gi is not None else s_gi
        ge = ge if ge is not None else s_ge
        sol = sol if sol is not None else s_sol

    if sol is None and solar_detail_raw:
        sol = _energy_from_dict(solar_detail_raw)

    charger_map = parse_charger_energy_totals(charger_energies_by_mac or {})
    plug_map = parse_plug_energy_by_mac(plug_energy_by_mac or {})

    return EnergyTotalsSnapshot(
        grid_import_kwh=gi,
        grid_export_kwh=ge,
        solar_production_kwh=sol,
        charger_energy_kwh_by_mac=charger_map,
        plug_energy_kwh_by_mac=plug_map,
    )
