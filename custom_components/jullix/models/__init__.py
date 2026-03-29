"""Domain models for Jullix installation state."""

from .battery import BatterySlot, parse_battery_detail
from .charger import ChargerDevice, parse_charger_control_payload, parse_chargers_list
from .costs import CostSavingsSnapshot, CostTotalSnapshot
from .installation import (
    JullixInstallationSnapshot,
    RawInstallFetches,
    build_installation_snapshot,
    merge_local_snapshot,
)
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
    "ChargerDevice",
    "CostSavingsSnapshot",
    "CostTotalSnapshot",
    "GridDetailSnapshot",
    "JullixInstallationSnapshot",
    "merge_local_snapshot",
    "MeteringSnapshot",
    "parse_battery_detail",
    "parse_charger_control_payload",
    "parse_chargers_list",
    "parse_plug_energy_today",
    "parse_plugs_list",
    "PlugDevice",
    "PowerSummarySnapshot",
    "RawInstallFetches",
    "SolarHomeSnapshot",
]
