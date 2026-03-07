"""API client for Jullix Platform API (mijn.jullix.be)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_PATH_ACTUAL_DETAIL,
    API_PATH_ACTUAL_METERING,
    API_PATH_ALGORITHM_FORCE,
    API_PATH_ALGORITHM_OPTI,
    API_PATH_ALGORITHM_OVERVIEW,
    API_PATH_ALGORITHM_PVPREDICT,
    API_PATH_ALGORITHM_RESULTS,
    API_PATH_ALGORITHM_RUN_HOURLY,
    API_PATH_ALGORITHM_SETTINGS,
    API_PATH_ALGORITHM_USAGE,
    API_PATH_CAR_BLOCK,
    API_PATH_CHARGER_CONTROL,
    API_PATH_CHARGER_ENERGIES,
    API_PATH_CHARGER_EVENTS,
    API_PATH_CHARGER_STATUS,
    API_PATH_CHARGERS,
    API_PATH_CHARGERSESSION_ASSIGN,
    API_PATH_CHARGERSESSION_INSTALLATION,
    API_PATH_COST_HOURLY_PRICE,
    API_PATH_COST_SAVINGS,
    API_PATH_COST_TOTAL,
    API_PATH_HISTORY_PLUG_ENERGY,
    API_PATH_HISTORY_PLUG_POWER,
    API_PATH_INSTALLATION,
    API_PATH_INSTALLATIONS,
    API_PATH_PLUG_CONTROL,
    API_PATH_PLUG_ENERGY,
    API_PATH_PLUG_POWER,
    API_PATH_PLUGS,
    API_PATH_POWER_SUMMARY,
    API_PATH_STATISTICS_ENERGY_DAILY,
    API_PATH_STATISTICS_ENERGY_MONTHLY,
    API_PATH_STATISTICS_ENERGY_YEARLY,
    API_PATH_TARIFF,
    API_PATH_WEATHER_ALARM,
    API_PATH_WEATHER_FORECAST,
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
            # Use DefaultResolver to avoid aiodns compatibility issues in CI (e.g. getaddrinfo signature)
            connector = aiohttp.TCPConnector(resolver=aiohttp.resolver.DefaultResolver())
            self._session = aiohttp.ClientSession(connector=connector)

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

    async def get_plug_energy(
        self, mac: str, year: int, month: int, day: int
    ) -> dict[str, Any]:
        """Fetch plug energy for a specific day."""
        path = API_PATH_PLUG_ENERGY.format(mac=mac, year=year, month=month, day=day)
        return await self._request("GET", path)

    async def get_plug_power(
        self, mac: str, year: int, month: int, day: int
    ) -> dict[str, Any]:
        """Fetch plug power data for a specific day."""
        path = API_PATH_PLUG_POWER.format(mac=mac, year=year, month=month, day=day)
        return await self._request("GET", path)

    async def get_history_plug_energy(
        self, install_id: str, year: int, month: int, day: int
    ) -> dict[str, Any]:
        """Fetch installation-level plug energy history for a day."""
        path = API_PATH_HISTORY_PLUG_ENERGY.format(
            install_id=install_id, year=year, month=month, day=day
        )
        return await self._request("GET", path)

    async def get_history_plug_power(
        self, install_id: str, year: int, month: int, day: int
    ) -> dict[str, Any]:
        """Fetch installation-level plug power history for a day."""
        path = API_PATH_HISTORY_PLUG_POWER.format(
            install_id=install_id, year=year, month=month, day=day
        )
        return await self._request("GET", path)

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

    async def get_algorithm_opti(self, install_id: str) -> dict[str, Any]:
        """Retrieve optimized model data for an installation."""
        path = API_PATH_ALGORITHM_OPTI.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_algorithm_overview(self, install_id: str) -> dict[str, Any]:
        """Get optimization overview for an installation."""
        path = API_PATH_ALGORITHM_OVERVIEW.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_algorithm_results(self, install_id: str) -> dict[str, Any]:
        """Retrieve optimization results for an installation."""
        path = API_PATH_ALGORITHM_RESULTS.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_algorithm_usage(self, install_id: str) -> dict[str, Any]:
        """Get usage model for an installation."""
        path = API_PATH_ALGORITHM_USAGE.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_algorithm_pvpredict(self, install_id: str) -> dict[str, Any]:
        """Get solar prediction for an installation."""
        path = API_PATH_ALGORITHM_PVPREDICT.format(install_id=install_id)
        return await self._request("GET", path)

    async def run_algorithm_hourly(self, install_id: str) -> dict[str, Any]:
        """Run the hourly optimization algorithm."""
        path = API_PATH_ALGORITHM_RUN_HOURLY.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_cost_hourly_price(
        self, install_id: str, year: int, month: int, day: int
    ) -> dict[str, Any]:
        """Get hourly price for a day."""
        path = API_PATH_COST_HOURLY_PRICE.format(
            install_id=install_id, year=year, month=month, day=day
        )
        return await self._request("GET", path)

    async def get_chargersession_installation(
        self, install_id: str
    ) -> dict[str, Any]:
        """Get charge sessions for an installation."""
        path = API_PATH_CHARGERSESSION_INSTALLATION.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_car_block(self, car_id: str) -> dict[str, Any]:
        """Get block charging estimate for a car."""
        path = API_PATH_CAR_BLOCK.format(car_id=car_id)
        return await self._request("GET", path)

    async def get_tariff(self, install_id: str) -> dict[str, Any]:
        """Get active energy tariff for an installation."""
        path = API_PATH_TARIFF.format(install_id=install_id)
        return await self._request("GET", path)

    async def update_tariff(
        self, install_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Update tariff for an installation."""
        path = API_PATH_TARIFF.format(install_id=install_id)
        return await self._request("PUT", path, json=payload)

    async def assign_chargersession(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Assign a charge session."""
        return await self._request("PUT", API_PATH_CHARGERSESSION_ASSIGN, json=payload)

    async def get_weather_forecast(self, install_id: str) -> dict[str, Any]:
        """Get weather forecast for an installation."""
        path = API_PATH_WEATHER_FORECAST.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_weather_alarm(self, install_id: str) -> dict[str, Any]:
        """Get current weather alerts for an installation."""
        path = API_PATH_WEATHER_ALARM.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_statistics_energy_daily(
        self, install_id: str
    ) -> dict[str, Any]:
        """Get daily energy statistics."""
        path = API_PATH_STATISTICS_ENERGY_DAILY.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_statistics_energy_monthly(
        self, install_id: str
    ) -> dict[str, Any]:
        """Get monthly energy statistics."""
        path = API_PATH_STATISTICS_ENERGY_MONTHLY.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_statistics_energy_yearly(
        self, install_id: str
    ) -> dict[str, Any]:
        """Get yearly energy statistics."""
        path = API_PATH_STATISTICS_ENERGY_YEARLY.format(install_id=install_id)
        return await self._request("GET", path)

    async def get_charger_energies(
        self, mac: str, year: int, month: int, day: int
    ) -> dict[str, Any]:
        """Retrieve energy data for a charger for a day."""
        path = API_PATH_CHARGER_ENERGIES.format(
            mac=mac, year=year, month=month, day=day
        )
        return await self._request("GET", path)

    async def get_charger_events(self, mac: str) -> dict[str, Any]:
        """Retrieve events for a charger."""
        path = API_PATH_CHARGER_EVENTS.format(mac=mac)
        return await self._request("GET", path)
