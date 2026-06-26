"""Parsed Jullix-Direct local EMS payloads for dedicated sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .util import power_value_to_watts, safe_float, unwrap_data


def _first_dict(payload: Any) -> dict[str, Any] | None:
    """Unwrap list envelope and return first dict row."""
    data = unwrap_data(payload)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def _nested_float(data: dict[str, Any], *keys: str) -> float | None:
    node: Any = data
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return safe_float(node)


def _nested_bool(data: dict[str, Any], *keys: str) -> bool | None:
    node: Any = data
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if node is None:
        return None
    return bool(node)


@dataclass(frozen=True)
class LocalEmsSnapshot:
    """Normalized local EMS fields (Jullix-Direct /api/ems/*)."""

    solar_fault: bool | None = None
    battery_voltage: float | None = None
    battery_fault: bool | None = None
    power_in_w: float | None = None
    power_out_w: float | None = None
    net_power_w: float | None = None
    energy_in_1_kwh: float | None = None
    energy_in_2_kwh: float | None = None
    energy_out_1_kwh: float | None = None
    energy_out_2_kwh: float | None = None
    voltage_l1: float | None = None
    voltage_l2: float | None = None
    voltage_l3: float | None = None
    water_m3: float | None = None
    charger_soc: float | None = None
    charger_temperature: float | None = None
    charger_max_current: float | None = None
    charger_state: str | None = None
    charger_busy: bool | None = None
    charger_three_phase: bool | None = None

    @classmethod
    def empty(cls) -> LocalEmsSnapshot:
        return cls()

    def has_meter_data(self) -> bool:
        return any(
            v is not None
            for v in (
                self.power_in_w,
                self.power_out_w,
                self.net_power_w,
                self.energy_in_1_kwh,
                self.energy_in_2_kwh,
                self.energy_out_1_kwh,
                self.energy_out_2_kwh,
                self.voltage_l1,
                self.voltage_l2,
                self.voltage_l3,
                self.water_m3,
            )
        )

    def has_charger_data(self) -> bool:
        return any(
            v is not None
            for v in (
                self.charger_soc,
                self.charger_temperature,
                self.charger_max_current,
                self.charger_state,
                self.charger_busy,
                self.charger_three_phase,
            )
        )


def parse_local_ems(local_data: dict[str, Any]) -> LocalEmsSnapshot:
    """Parse merged local EMS endpoint payloads into typed fields."""
    if not local_data:
        return LocalEmsSnapshot.empty()

    solar_fault: bool | None = None
    if local_data.get("solar") is not None:
        solar_row = _first_dict(local_data["solar"])
        if solar_row is not None:
            solar_fault = _nested_bool(solar_row, "fault")
            if solar_fault is None and "fault" in solar_row:
                solar_fault = bool(solar_row["fault"])

    battery_voltage: float | None = None
    battery_fault: bool | None = None
    if local_data.get("battery") is not None:
        battery_row = _first_dict(local_data["battery"])
        if battery_row is not None:
            battery_voltage = _nested_float(battery_row, "battery", "voltage")
            if battery_voltage is None:
                battery_voltage = safe_float(battery_row.get("voltage"))
            battery_fault = _nested_bool(battery_row, "battery", "fault")
            if battery_fault is None and "fault" in battery_row:
                battery_fault = bool(battery_row["fault"])

    power_in_w = power_out_w = None
    energy_in_1 = energy_in_2 = energy_out_1 = energy_out_2 = None
    voltage_l1 = voltage_l2 = voltage_l3 = None
    water_m3 = None
    if local_data.get("meter") is not None:
        meter = _first_dict(local_data["meter"])
        if meter is not None:
            power_in_w = power_value_to_watts(_nested_float(meter, "power", "in"))
            if power_in_w is None:
                power_in_w = power_value_to_watts(meter.get("power_in"))
            power_out_w = power_value_to_watts(_nested_float(meter, "power", "out"))
            if power_out_w is None:
                power_out_w = power_value_to_watts(meter.get("power_out"))
            energy_in_1 = _nested_float(meter, "energy", "in_1")
            energy_in_2 = _nested_float(meter, "energy", "in_2")
            energy_out_1 = _nested_float(meter, "energy", "out_1")
            energy_out_2 = _nested_float(meter, "energy", "out_2")
            voltage_l1 = _nested_float(meter, "voltage", "l1")
            voltage_l2 = _nested_float(meter, "voltage", "l2")
            voltage_l3 = _nested_float(meter, "voltage", "l3")
            water_m3 = safe_float(meter.get("water"))

    net_power_w: float | None = None
    if power_in_w is not None and power_out_w is not None:
        net_power_w = round(power_in_w - power_out_w, 0)
    elif power_in_w is not None:
        net_power_w = round(power_in_w, 0)
    elif power_out_w is not None:
        net_power_w = round(-power_out_w, 0)

    charger_soc = charger_temperature = charger_max_current = None
    charger_state: str | None = None
    charger_busy = charger_three_phase = None
    if local_data.get("charger") is not None:
        charger_row = _first_dict(local_data["charger"])
        if charger_row is not None:
            charger_soc = safe_float(charger_row.get("soc"))
            temp = safe_float(charger_row.get("temperature"))
            charger_temperature = round(temp, 1) if temp is not None else None
            charger_max_current = safe_float(charger_row.get("max_current"))
            state_val = charger_row.get("state")
            if state_val is not None:
                charger_state = str(state_val)
            if "busy" in charger_row:
                charger_busy = bool(charger_row["busy"])
            if "three_phase" in charger_row:
                charger_three_phase = bool(charger_row["three_phase"])

    return LocalEmsSnapshot(
        solar_fault=solar_fault,
        battery_voltage=battery_voltage,
        battery_fault=battery_fault,
        power_in_w=power_in_w,
        power_out_w=power_out_w,
        net_power_w=net_power_w,
        energy_in_1_kwh=energy_in_1,
        energy_in_2_kwh=energy_in_2,
        energy_out_1_kwh=energy_out_1,
        energy_out_2_kwh=energy_out_2,
        voltage_l1=voltage_l1,
        voltage_l2=voltage_l2,
        voltage_l3=voltage_l3,
        water_m3=water_m3,
        charger_soc=charger_soc,
        charger_temperature=charger_temperature,
        charger_max_current=charger_max_current,
        charger_state=charger_state,
        charger_busy=charger_busy,
        charger_three_phase=charger_three_phase,
    )
