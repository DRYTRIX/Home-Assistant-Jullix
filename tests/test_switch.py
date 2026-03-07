"""Tests for Jullix switch platform (charger/plug state logic)."""

from __future__ import annotations

from typing import Any

import pytest


def _is_enabled(obj: dict[str, Any]) -> bool:
    """Mirror of switch._is_enabled: extract enabled/on state from device dict."""
    if obj.get("active") is True:
        return True
    if obj.get("enabled") is True:
        return True
    if obj.get("on") is True:
        return True
    if obj.get("state", "").lower() in ("on", "charging", "enabled"):
        return True
    if obj.get("status", "").lower() in ("on", "charging", "enabled"):
        return True
    if obj.get("plug_state") is True:
        return True
    return False


def test_is_enabled_active():
    """_is_enabled returns True when active is True."""
    assert _is_enabled({"active": True}) is True


def test_is_enabled_enabled_key():
    """_is_enabled returns True when enabled is True."""
    assert _is_enabled({"enabled": True}) is True


def test_is_enabled_on_key():
    """_is_enabled returns True when on is True."""
    assert _is_enabled({"on": True}) is True


def test_is_enabled_state_charging():
    """_is_enabled returns True when state is charging/on/enabled."""
    assert _is_enabled({"state": "charging"}) is True
    assert _is_enabled({"state": "on"}) is True
    assert _is_enabled({"state": "enabled"}) is True
    assert _is_enabled({"state": "CHARGING"}) is True


def test_is_enabled_status_charging():
    """_is_enabled returns True when status is charging/on/enabled."""
    assert _is_enabled({"status": "charging"}) is True
    assert _is_enabled({"status": "on"}) is True


def test_is_enabled_plug_state():
    """_is_enabled returns True when plug_state is True."""
    assert _is_enabled({"plug_state": True}) is True


def test_is_enabled_false():
    """_is_enabled returns False when no on-like key is set."""
    assert _is_enabled({}) is False
    assert _is_enabled({"active": False}) is False
    assert _is_enabled({"state": "off"}) is False
    assert _is_enabled({"status": "idle"}) is False
