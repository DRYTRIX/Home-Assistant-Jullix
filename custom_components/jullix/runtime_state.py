"""Coordinator-owned mutable metrics and edge-detection state (not in snapshots)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InstallRuntimeMetrics:
    """Per-installation refresh health (updated on successful API snapshot build)."""

    last_latency_ms: float | None = None
    last_success_at: datetime | None = None


@dataclass
class InstallEdgeState:
    """Previous values for transition events (per installation)."""

    charger_power_by_mac: dict[str, float] = field(default_factory=dict)
    battery_soc: float | None = None
    grid_import_w: float | None = None
    grid_low_streak: int = 0
    in_grid_outage: bool = False
