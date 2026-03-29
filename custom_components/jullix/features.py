"""Internal feature tiers for fetch scheduling (not user-facing flags)."""

from __future__ import annotations

from enum import Enum, auto


class FeatureTier(Enum):
    """Stability tier for API capability groups."""

    CORE = auto()
    EXTENDED = auto()
    EXPERIMENTAL = auto()


# Poll extended groups every Nth coordinator refresh (CORE runs every refresh).
EXTENDED_POLL_INTERVAL = 3

# Internal registry: which API groups belong to which tier (for docs / future gating).
FETCH_GROUP_TIER: dict[str, FeatureTier] = {
    "power_summary": FeatureTier.CORE,
    "actual_details": FeatureTier.CORE,
    "chargers_plugs": FeatureTier.CORE,
    "charger_control": FeatureTier.CORE,
    "plug_energy_history": FeatureTier.CORE,
    "cost": FeatureTier.EXTENDED,
    "cost_hourly_price": FeatureTier.EXTENDED,
    "chargersession": FeatureTier.EXTENDED,
    "statistics": FeatureTier.EXTENDED,
    "tariff": FeatureTier.EXTENDED,
    "weather": FeatureTier.EXTENDED,
    "algorithm_overview": FeatureTier.EXTENDED,
    # Reserved for unstable endpoints:
    # "example": FeatureTier.EXPERIMENTAL,
}


def run_extended_this_refresh(refresh_counter: int) -> bool:
    """True when cost/statistics/tariff/weather/algorithm fetches should run.

    Counter starts at 1 on first refresh so the first poll always loads extended data.
    """
    return refresh_counter % EXTENDED_POLL_INTERVAL == 1
