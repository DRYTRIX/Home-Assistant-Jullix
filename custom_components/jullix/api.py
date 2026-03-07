"""API client for Jullix Platform API (mijn.jullix.be)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_PATH_ACTUAL_DETAIL,
    API_PATH_ACTUAL_METERING,
    API_PATH_CHARGER_CONTROL,
    API_PATH_CHARGER_STATUS,
    API_PATH_CHARGERS,
    API_PATH_COST_SAVINGS,
    API_PATH_COST_TOTAL,
    API_PATH_INSTALLATION,
    API_PATH_INSTALLATIONS,
    API_PATH_PLUG_CONTROL,
    API_PATH_PLUGS,
    API_PATH_POWER_SUMMARY,
    API_PATH_ALGORITHM_FORCE,
    API_PATH_ALGORITHM_SETTINGS,
)

_LOGGER = logging.getLogger(__name__)


class JullixApiError(Exception):
    """Base exception for Jullix API errors."""

    pass


class JullixAuthError(JullixApiError):
    """Authentication error (e.g. invalid or expired token)."""

    pass


class JullixApiClient:
    """Client for the Jullix Platform API."""

    def __init__(self, api_token: str) -> None:
        """Initialize the API client."""
        self._token = api_token
        self._session: aiohttp.ClientSession | None = None

    def _headers(self) -> dict[str, str]:
        """Return request headers with auth."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Perform an API request."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

        url = f"{API_BASE_URL}{path}"
        headers = kwargs.pop("headers", {}) or {}
        headers.update(self._headers())

        try:
            async with self._session.request(
                method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=30), **kwargs
            ) as resp:
                if resp.status == 401:
                    raise JullixAuthError("Invalid or expired API token")
                if resp.status >= 400:
                    text = await resp.text()
                    raise JullixApiError(
                        f"API error {resp.status}: {text[:200] if text else resp.reason}"
                    )
                if resp.status == 204 or resp.content_length == 0:
                    return {}
                return await resp.json()
        except aiohttp.ClientError as e:
            raise JullixApiError(f"Connection error: {e}") from e

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def get_installations(self) -> list[dict[str, Any]]:
        """Fetch all installations the user has access to."""
        data = await self._request("GET", API_PATH_INSTALLATIONS)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "installations" in data:
            return data["installations"]
        if isinstance(data, dict):
            return [data]
        return []

    async def get_installation(self, install_id: str) -> dict[str, Any]:
        """Fetch a single installation by ID."""
        path = API_PATH_INSTALLATION.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_power_summary(self, install_id: str) -> dict[str, Any]:
        """Fetch power summary for an installation."""
        path = API_PATH_POWER_SUMMARY.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_actual_detail(
        self, install_id: str, detail_type: str
    ) -> dict[str, Any]:
        """Fetch actual detail (battery, solar, grid, home, plug, charger, metering)."""
        path = API_PATH_ACTUAL_DETAIL.format(
            install_id=install_id, detail_type=detail_type
        )
        return await self._request("GET", path)

    async def get_metering(self, install_id: str) -> dict[str, Any]:
        """Fetch metering data for an installation."""
        path = API_PATH_ACTUAL_METERING.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_chargers(self, install_id: str) -> list[dict[str, Any]]:
        """Fetch all chargers for an installation."""
        path = API_PATH_CHARGERS.format(install_id=install_id)
        data = await self._request("GET", path)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "chargers" in data:
            return data["chargers"]
        return []

    async def get_charger_status(self, mac: str) -> dict[str, Any]:
        """Fetch charger status by MAC."""
        path = API_PATH_CHARGER_STATUS.format(mac=mac)
        return await self._request("GET", path)

    async def get_charger_control(self, mac: str) -> dict[str, Any]:
        """Fetch charger control settings by MAC."""
        path = API_PATH_CHARGER_CONTROL.format(mac=mac)
        return await self._request("GET", path)

    async def set_charger_control(self, mac: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update charger control settings."""
        path = API_PATH_CHARGER_CONTROL.format(mac=mac)
        return await self._request("PUT", path, json=payload)

    async def get_plugs(self, install_id: str) -> list[dict[str, Any]]:
        """Fetch all plugs for an installation."""
        path = API_PATH_PLUGS.format(install_id=install_id)
        data = await self._request("GET", path)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "plugs" in data:
            return data["plugs"]
        return []

    async def set_plug_control(self, mac: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send control command to plug."""
        path = API_PATH_PLUG_CONTROL.format(mac=mac)
        return await self._request("PUT", path, json=payload)

    async def get_cost_savings(self, install_id: str) -> dict[str, Any]:
        """Fetch savings data for an installation."""
        path = API_PATH_COST_SAVINGS.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_cost_total(
        self, install_id: str, year: int, month: int
    ) -> dict[str, Any]:
        """Fetch total cost for an installation for a given month."""
        path = API_PATH_COST_TOTAL.format(
            install_id=install_id, year=year, month=month
        )
        return await self._request("GET", path)

    async def get_algorithm_settings(self, install_id: str) -> dict[str, Any]:
        """Fetch optimizer settings for an installation."""
        path = API_PATH_ALGORITHM_SETTINGS.format(install_id=install_id)
        return await self._request("GET", path)

    async def force_algorithm_command(
        self, install_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Force a command on the installation's gateway."""
        path = API_PATH_ALGORITHM_FORCE.format(install_id=install_id)
        return await self._request("POST", path, json=payload)
