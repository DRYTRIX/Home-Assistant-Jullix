"""Jullix-Direct local API client for real-time data without internet."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import LOCAL_EMS_ENDPOINTS

_LOGGER = logging.getLogger(__name__)


class JullixLocalClient:
    """Client for Jullix-Direct local HTTP API."""

    def __init__(self, host: str) -> None:
        """Initialize the local client."""
        self._host = host.rstrip("/").replace("https://", "").replace("http://", "")
        self._base_url = f"http://{self._host}"

    async def test_connection(self) -> bool:
        """Test connection to the local Jullix device."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._base_url}/api/ems/meter",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        return True
                    raise ConnectionError(f"HTTP {resp.status}")
        except aiohttp.ClientError as err:
            raise ConnectionError(str(err)) from err

    async def get_ems_data(self) -> dict[str, Any]:
        """Fetch real-time data from all EMS endpoints."""
        result: dict[str, Any] = {}
        async with aiohttp.ClientSession() as session:
            for endpoint in LOCAL_EMS_ENDPOINTS:
                try:
                    async with session.get(
                        f"{self._base_url}/api/ems/{endpoint}",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data:
                                result[endpoint] = data
                except Exception as exc:
                    _LOGGER.debug("Local EMS %s failed: %s", endpoint, exc)
        return result
