"""Domain models for Jullix installation state."""

from .battery import (
    BatterySlot,
    backfill_battery_slot_energy,
    parse_battery_detail,
    parse_battery_energy_history,
)
from .charger import ChargerDevice, parse_charger_control_payload, parse_chargers_list
from .costs import CostSavingsSnapshot, CostTotalSnapshot
from .energy_totals import EnergyTotalsSnapshot, build_energy_totals
from .installation import (
    JullixInstallationSnapshot,
    RawInstallFetches,
    build_installation_snapshot,
    merge_local_snapshot,
)
from .local_ems import LocalEmsSnapshot, parse_local_ems
from .plug import PlugDevice, parse_plug_energy_today, parse_plugs_list
from .summary import (
    GridDetailSnapshot,
    MeteringSnapshot,
    PowerSummarySnapshot,
    SolarHomeSnapshot,
)

__all__ = [
    "BatterySlot",
    "build_installation_snapshot",
    "build_energy_totals",
    "ChargerDevice",
    "CostSavingsSnapshot",
    "CostTotalSnapshot",
    "EnergyTotalsSnapshot",
    "GridDetailSnapshot",
    "JullixInstallationSnapshot",
    "LocalEmsSnapshot",
    "merge_local_snapshot",
    "MeteringSnapshot",
    "backfill_battery_slot_energy",
    "parse_battery_energy_history",
    "parse_local_ems",
    "parse_charger_control_payload",
    "parse_chargers_list",
    "parse_plug_energy_today",
    "parse_plugs_list",
    "PlugDevice",
    "PowerSummarySnapshot",
    "RawInstallFetches",
    "SolarHomeSnapshot",
]
