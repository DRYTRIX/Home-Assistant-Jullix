"""Jullix sensor platform (entry re-exports sensors package)."""

from __future__ import annotations

from .sensors import async_setup_entry

__all__ = ["async_setup_entry"]
