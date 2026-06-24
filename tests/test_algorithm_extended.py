"""Tests for Jullix extended-algorithm sensor value parsing.

algorithm_extended.py imports homeassistant.helpers.device_registry at module
scope, which isn't stubbed by the lightweight conftest HA mock (same as every
other platform module), so it can't be imported here. Mirror its pure helper
instead, same approach as test_switch.py::_is_enabled.
"""

from __future__ import annotations

from typing import Any

from custom_components.jullix.models.util import unwrap_data


def _dict_summary(payload: Any, *keys: str) -> str | None:
    """Mirror of algorithm_extended._dict_summary."""
    data = unwrap_data(payload)
    if isinstance(data, dict):
        for key in keys:
            val = data.get(key)
            if val is not None:
                return str(val)
        if len(data) == 1:
            return str(next(iter(data.values())))
    elif payload is not None:
        return str(payload)
    return None


def test_dict_summary_none_returns_none():
    """None payload yields None."""
    assert _dict_summary(None, "status") is None


def test_dict_summary_matches_first_key():
    """First matching key in priority order wins."""
    assert _dict_summary({"state": "idle", "status": "ok"}, "status", "state") == "ok"


def test_dict_summary_unwraps_data_envelope():
    """API {data: {...}} envelope is unwrapped before key lookup."""
    assert _dict_summary({"data": {"mode": "auto"}}, "status", "mode") == "auto"


def test_dict_summary_falls_back_to_single_value():
    """A single-key dict with no matching key returns that lone value."""
    assert _dict_summary({"data": {"foo": "bar"}}, "status", "state") == "bar"


def test_dict_summary_multi_key_no_match_returns_none():
    """A multi-key dict with no matching key returns None (ambiguous)."""
    assert _dict_summary({"a": 1, "b": 2}, "status") is None


def test_dict_summary_empty_dict_returns_none():
    """An empty dict returns None."""
    assert _dict_summary({}, "status") is None


def test_dict_summary_non_dict_payload_stringifies_original():
    """A non-dict payload (e.g. a bare list) is stringified as-is."""
    assert _dict_summary([1, 2, 3], "status") == "[1, 2, 3]"
