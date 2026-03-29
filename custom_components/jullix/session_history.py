"""Optional persistent JSON log of charge session snapshots (Home Assistant Store)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1


class SessionHistoryRecorder:
    """Keep last N session records on disk under config/.storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry_id}.session_history")
        self._data: dict[str, Any] = {"sessions": []}

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        if isinstance(loaded, dict) and isinstance(loaded.get("sessions"), list):
            self._data = loaded
        else:
            self._data = {"sessions": []}

    async def maybe_append(
        self,
        install_id: str,
        session_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        """Append if session_id is new vs last recorded for this installation."""
        if not session_id:
            return
        sessions: list[dict[str, Any]] = list(self._data.get("sessions", []))
        last_for = next(
            (
                s.get("session_id")
                for s in reversed(sessions)
                if s.get("installation_id") == install_id
            ),
            None,
        )
        if last_for == session_id:
            return
        row = {"installation_id": install_id, "session_id": session_id, **payload}
        sessions.append(row)
        self._data["sessions"] = sessions[-50:]
        await self._store.async_save(self._data)
        _LOGGER.debug("Session history appended install=%s session=%s", install_id, session_id)
