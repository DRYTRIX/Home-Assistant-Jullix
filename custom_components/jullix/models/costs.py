"""Cost and savings payloads."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .util import safe_float, unwrap_data

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CostSavingsSnapshot:
    """Parsed cost/savings endpoint (flexible keys for sensors)."""

    raw: dict[str, Any]

    @classmethod
    def empty(cls) -> CostSavingsSnapshot:
        return cls(raw={})

    @classmethod
    def from_api(cls, raw: Any) -> CostSavingsSnapshot:
        try:
            data = unwrap_data(raw)
            if isinstance(data, dict):
                return cls(raw=dict(data))
            if raw is not None and isinstance(raw, dict):
                return cls(raw=dict(raw))
        except (TypeError, ValueError) as e:
            _LOGGER.debug("Cost savings parse failed: %s", e)
        return cls.empty()

    def float_field(self, key: str) -> float | None:
        val = self.raw.get(key)
        if isinstance(val, dict):
            val = val.get("value", val.get("amount"))
        return safe_float(val)


@dataclass(frozen=True)
class CostTotalSnapshot:
    """Monthly total cost payload."""

    raw: Any
    total: float | None

    @classmethod
    def empty(cls) -> CostTotalSnapshot:
        return cls(raw=None, total=None)

    @classmethod
    def from_api(cls, raw: Any) -> CostTotalSnapshot:
        try:
            data = unwrap_data(raw)
            total: float | None = None
            if isinstance(data, (int, float)):
                total = float(data)
            elif isinstance(data, dict):
                total = safe_float(
                    data.get("total", data.get("value", data.get("amount")))
                )
            return cls(raw=data, total=total)
        except (TypeError, ValueError) as e:
            _LOGGER.debug("Cost total parse failed: %s", e)
            return cls.empty()
