"""Per-installation snapshot: aggregate models + local EMS merge."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .battery import BatterySlot, parse_battery_detail
from .charger import ChargerDevice, parse_charger_control_payload, parse_chargers_list
from .costs import CostSavingsSnapshot, CostTotalSnapshot
from .plug import PlugDevice, parse_plug_energy_today, parse_plugs_list
from .summary import (
    GridDetailSnapshot,
    MeteringSnapshot,
    PowerSummarySnapshot,
    SolarHomeSnapshot,
)


@dataclass(frozen=True)
class RawInstallFetches:
    """Raw API fragments before parsing (coordinator fills this)."""

    power_summary: Any = None
    detail_battery: Any = None
    detail_solar: Any = None
    detail_grid: Any = None
    detail_home: Any = None
    detail_plug: Any = None
    detail_charger: Any = None
    detail_metering: Any = None
    chargers_response: Any = None
    charger_control_by_mac: dict[str, Any] | None = None
    plugs_response: Any = None
    plug_energy_today: Any = None
    cost_savings: Any = None
    cost_total: Any = None
    weather_alarm: Any = None
    statistics_energy_daily: Any = None
    statistics_energy_monthly: Any = None
    statistics_energy_yearly: Any = None
    algorithm_overview: Any = None
    tariff: Any = None
    weather_forecast: Any = None
    cost_hourly_price: Any = None
    chargersession_raw: Any = None


@dataclass(frozen=True)
class JullixInstallationSnapshot:
    """Normalized state for one installation (entities read this only)."""

    power_summary: PowerSummarySnapshot
    grid_detail: GridDetailSnapshot
    solar_detail: SolarHomeSnapshot
    home_detail: SolarHomeSnapshot
    metering: MeteringSnapshot
    metering_source_dict: dict[str, Any]
    battery_slots: tuple[BatterySlot, ...]
    chargers: tuple[ChargerDevice, ...]
    charger_control: dict[str, dict[str, Any]]
    charger_detail_rows: tuple[dict[str, Any], ...]
    plugs: tuple[PlugDevice, ...]
    plug_detail_rows: tuple[dict[str, Any], ...]
    plug_energy_today_raw: Any
    plug_energy_today_kwh: float | None
    cost_savings: CostSavingsSnapshot
    cost_total: CostTotalSnapshot
    weather_alarm: Any
    statistics_energy_daily: Any
    statistics_energy_monthly: Any
    statistics_energy_yearly: Any
    algorithm_overview: Any
    tariff: Any
    weather_forecast: Any
    cost_hourly_price: Any
    chargersession_raw: Any

    def installation_display_name(self, install_id: str) -> str:
        return f"Installation {install_id[:8]}"

    # --- Charger / plug power for sensors (index-based) ---

    def charger_power_watts(self, index: int) -> float | None:
        from .util import power_value_to_watts

        if 0 <= index < len(self.chargers):
            ch = self.chargers[index].raw
            val = ch.get("power", ch.get("current_power"))
            pw = power_value_to_watts(val)
            if pw is not None:
                return pw
        if 0 <= index < len(self.charger_detail_rows):
            ch = self.charger_detail_rows[index]
            val = ch.get("power", ch.get("current_power"))
            pw = power_value_to_watts(val)
            if pw is not None:
                return pw
        if len(self.chargers) == 1:
            return self.power_summary.power_watts("car")
        return None

    def plug_power_watts(self, index: int) -> float | None:
        from .util import power_value_to_watts

        if 0 <= index < len(self.plugs):
            p = self.plugs[index].raw
            val = p.get("power", p.get("current_power"))
            pw = power_value_to_watts(val)
            if pw is not None:
                return pw
        if 0 <= index < len(self.plug_detail_rows):
            p = self.plug_detail_rows[index]
            val = p.get("power", p.get("current_power"))
            return power_value_to_watts(val)
        return None

    def cost_float(self, key: str) -> float | None:
        return self.cost_savings.float_field(key)

    def chargers_as_dicts(self) -> list[dict[str, Any]]:
        return [c.as_dict() for c in self.chargers]

    def plugs_as_dicts(self) -> list[dict[str, Any]]:
        return [p.as_dict() for p in self.plugs]


def _unwrap(raw: Any) -> Any:
    if isinstance(raw, dict) and "data" in raw:
        return raw.get("data", raw)
    return raw


def _detail_list_to_rows(detail: Any) -> tuple[dict[str, Any], ...]:
    if isinstance(detail, list):
        return tuple(d for d in detail if isinstance(d, dict))
    if isinstance(detail, dict):
        return (detail,)
    return ()


def build_installation_snapshot(raw: RawInstallFetches) -> JullixInstallationSnapshot:
    """Build snapshot from coordinator raw fetch bundle."""
    ps = PowerSummarySnapshot.from_api(raw.power_summary)

    bat_detail = _unwrap(raw.detail_battery)
    battery_slots = parse_battery_detail(bat_detail)

    solar_unwrapped = _unwrap(raw.detail_solar)
    solar_detail = SolarHomeSnapshot.from_solar_api(solar_unwrapped)

    grid_unwrapped = _unwrap(raw.detail_grid)
    grid_detail = (
        GridDetailSnapshot.from_api(grid_unwrapped)
        if isinstance(grid_unwrapped, dict)
        else GridDetailSnapshot.empty()
    )

    home_unwrapped = _unwrap(raw.detail_home)
    home_detail = SolarHomeSnapshot.from_home_api(home_unwrapped)

    met_unwrapped = _unwrap(raw.detail_metering)
    metering_src: dict[str, Any] = (
        dict(met_unwrapped) if isinstance(met_unwrapped, dict) else {}
    )
    metering = MeteringSnapshot.from_api(metering_src)

    plug_rows_raw = _unwrap(raw.detail_plug)
    plug_detail_rows = _detail_list_to_rows(plug_rows_raw)

    charger_rows_raw = _unwrap(raw.detail_charger)
    charger_detail_rows = _detail_list_to_rows(charger_rows_raw)

    chargers = parse_chargers_list(raw.chargers_response)

    ctrl_in = raw.charger_control_by_mac or {}
    charger_control: dict[str, dict[str, Any]] = {}
    for mac, payload in ctrl_in.items():
        parsed = parse_charger_control_payload(payload)
        if parsed:
            charger_control[str(mac)] = parsed

    plugs = parse_plugs_list(raw.plugs_response)

    plug_raw, plug_kwh = parse_plug_energy_today(raw.plug_energy_today)

    cost_savings = CostSavingsSnapshot.from_api(raw.cost_savings)
    cost_total = CostTotalSnapshot.from_api(raw.cost_total)

    w_alarm = _unwrap(raw.weather_alarm)
    stats_d = _unwrap(raw.statistics_energy_daily)
    stats_m = _unwrap(raw.statistics_energy_monthly)
    stats_y = _unwrap(raw.statistics_energy_yearly)
    algo = _unwrap(raw.algorithm_overview)
    tariff = _unwrap(raw.tariff)
    weather_f = _unwrap(raw.weather_forecast)
    hourly = _unwrap(raw.cost_hourly_price)
    cs_raw = _unwrap(raw.chargersession_raw)

    return JullixInstallationSnapshot(
        power_summary=ps,
        grid_detail=grid_detail,
        solar_detail=solar_detail,
        home_detail=home_detail,
        metering=metering,
        metering_source_dict=metering_src,
        battery_slots=battery_slots,
        chargers=chargers,
        charger_control=charger_control,
        charger_detail_rows=charger_detail_rows,
        plugs=plugs,
        plug_detail_rows=plug_detail_rows,
        plug_energy_today_raw=plug_raw,
        plug_energy_today_kwh=plug_kwh,
        cost_savings=cost_savings,
        cost_total=cost_total,
        weather_alarm=w_alarm,
        statistics_energy_daily=stats_d,
        statistics_energy_monthly=stats_m,
        statistics_energy_yearly=stats_y,
        algorithm_overview=algo,
        tariff=tariff,
        weather_forecast=weather_f,
        cost_hourly_price=hourly,
        chargersession_raw=cs_raw,
    )


def merge_local_snapshot(
    platform: JullixInstallationSnapshot,
    local_data: dict[str, Any],
) -> JullixInstallationSnapshot:
    """Merge Jullix-Direct local EMS payloads into platform snapshot."""
    if not local_data:
        return platform

    metering_src = dict(platform.metering_source_dict)
    if local_data.get("meter"):
        metering_src.update(local_data["meter"])
    metering = MeteringSnapshot.from_api(metering_src)

    solar = platform.solar_detail
    if local_data.get("solar"):
        solar = SolarHomeSnapshot.from_solar_api(local_data["solar"])

    battery_slots = platform.battery_slots
    if local_data.get("battery"):
        battery_slots = parse_battery_detail(local_data["battery"])

    charger_detail_rows = platform.charger_detail_rows
    if local_data.get("charger"):
        loc = local_data["charger"]
        if isinstance(loc, list) and loc:
            charger_detail_rows = tuple(d for d in loc if isinstance(d, dict))
        elif isinstance(loc, dict):
            charger_detail_rows = (loc,)

    plug_detail_rows = platform.plug_detail_rows
    if local_data.get("plug"):
        loc = local_data["plug"]
        if isinstance(loc, list) and loc:
            plug_detail_rows = tuple(d for d in loc if isinstance(d, dict))
        elif isinstance(loc, dict):
            plug_detail_rows = (loc,)

    return replace(
        platform,
        metering=metering,
        metering_source_dict=metering_src,
        solar_detail=solar,
        battery_slots=battery_slots,
        charger_detail_rows=charger_detail_rows,
        plug_detail_rows=plug_detail_rows,
    )
