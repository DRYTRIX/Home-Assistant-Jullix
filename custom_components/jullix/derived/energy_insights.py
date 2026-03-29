"""Instantaneous energy insight ratios from power summary (proxy, not metered kWh)."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import JullixInstallationSnapshot


@dataclass(frozen=True)
class EnergyInsightRatios:
    """Percentages derived from summary powers (0–100) or None if undefined."""

    self_consumption_pct: float | None
    solar_utilization_pct: float | None
    grid_dependency_pct: float | None


def compute_energy_insight_ratios(
    snap: JullixInstallationSnapshot,
) -> EnergyInsightRatios:
    """Compute proxy ratios from summary grid / solar / home (watts).

    Self-consumption / solar utilization: share of solar production not exported
    to the grid: (solar - max(0, -grid)) / solar * 100 when solar > 0.
    Grid dependency: grid import relative to home load: max(0, grid) / home * 100
    when home > 0.
    """
    solar_w = snap.power_summary.power_watts("solar")
    grid_w = snap.power_summary.power_watts("grid")
    home_w = snap.power_summary.power_watts("home")

    self_pct: float | None = None
    util_pct: float | None = None

    if solar_w is not None and solar_w > 0:
        export_w = 0.0
        if grid_w is not None and grid_w < 0:
            export_w = -grid_w
        solar_kept = max(0.0, solar_w - export_w)
        ratio = min(1.0, solar_kept / solar_w)
        self_pct = round(ratio * 100.0, 1)
        util_pct = self_pct

    grid_dep: float | None = None
    if home_w is not None and home_w > 0 and grid_w is not None:
        imp = max(0.0, grid_w)
        grid_dep = round(min(100.0, (imp / home_w) * 100.0), 1)

    return EnergyInsightRatios(
        self_consumption_pct=self_pct,
        solar_utilization_pct=util_pct,
        grid_dependency_pct=grid_dep,
    )
