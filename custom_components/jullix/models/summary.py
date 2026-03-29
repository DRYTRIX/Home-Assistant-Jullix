"""Power summary and grid / solar / home detail snapshots."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .util import power_value_to_watts, safe_float, unwrap_data

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PowerSummarySnapshot:
    """Normalized power summary (summary endpoint)."""

    powers: dict[str, Any]
    extra: dict[str, Any]

    @classmethod
    def empty(cls) -> PowerSummarySnapshot:
        return cls(powers={}, extra={})

    @classmethod
    def from_api(cls, raw: Any) -> PowerSummarySnapshot:
        """Parse power summary payload (envelope or inner data dict)."""
        try:
            data = unwrap_data(raw)
            if not isinstance(data, dict):
                return cls.empty()
            powers = data.get("powers", data)
            if not isinstance(powers, dict):
                powers = {}
            extra = {k: v for k, v in data.items() if k != "powers"}
            return cls(powers=dict(powers), extra=extra)
        except (TypeError, ValueError) as e:
            _LOGGER.debug("Power summary parse failed: %s", e)
            return cls.empty()

    def power_watts(self, key: str) -> float | None:
        """Watts for a summary key (grid, solar, home, battery, …)."""
        if not isinstance(self.powers, dict):
            return None
        return power_value_to_watts(self.powers.get(key))

    def summary_value_raw(self, key: str) -> Any:
        """Raw value from powers or top-level summary."""
        if isinstance(self.powers, dict) and key in self.powers:
            return self.powers.get(key)
        return self.extra.get(key) if key in self.extra else None


@dataclass(frozen=True)
class GridDetailSnapshot:
    """Grid detail endpoint (power, capacity tariff, …)."""

    raw: dict[str, Any]

    @classmethod
    def empty(cls) -> GridDetailSnapshot:
        return cls(raw={})

    @classmethod
    def from_api(cls, detail: Any) -> GridDetailSnapshot:
        if not isinstance(detail, dict):
            return cls.empty()
        return cls(raw=dict(detail))

    def power_watts(self) -> float | None:
        return power_value_to_watts(self.raw.get("power"))

    def captar_actual_raw(self) -> Any:
        return self.raw.get("captar_actual")


@dataclass(frozen=True)
class SolarHomeSnapshot:
    """Solar or home consumption detail (single device dict)."""

    raw: dict[str, Any]

    @classmethod
    def empty(cls) -> SolarHomeSnapshot:
        return cls(raw={})

    @classmethod
    def from_solar_api(cls, detail: Any) -> SolarHomeSnapshot:
        """API may return a list; first dict is used."""
        if isinstance(detail, list) and detail and isinstance(detail[0], dict):
            return cls(raw=dict(detail[0]))
        if isinstance(detail, dict):
            return cls(raw=dict(detail))
        return cls.empty()

    @classmethod
    def from_home_api(cls, detail: Any) -> SolarHomeSnapshot:
        if isinstance(detail, dict):
            return cls(raw=dict(detail))
        return cls.empty()

    def power_watts(self) -> float | None:
        return power_value_to_watts(self.raw.get("power"))


@dataclass(frozen=True)
class MeteringSnapshot:
    """Metering channels for display sensors."""

    channels: tuple[dict[str, Any], ...]

    @classmethod
    def empty(cls) -> MeteringSnapshot:
        return cls(channels=())

    @classmethod
    def from_api(cls, detail: Any) -> MeteringSnapshot:
        if not isinstance(detail, dict):
            return cls.empty()
        channels = detail.get("channels", detail)
        if isinstance(channels, dict):
            ch_list = [{"id": k, "value": v} for k, v in channels.items()]
        elif isinstance(channels, list):
            ch_list = [c for c in channels if isinstance(c, dict)]
        else:
            ch_list = [detail] if detail else []
        return cls(channels=tuple(ch_list))

    def channel_value(self, index: int) -> float | None:
        if 0 <= index < len(self.channels):
            ch = self.channels[index]
            val = ch.get("value", ch.get("power", ch.get("energy")))
            return safe_float(val)
        return None
