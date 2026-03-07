"""Data update coordinator for Jullix integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JullixApiClient
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class JullixDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that fetches Jullix data for all configured installations."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: JullixApiClient,
        install_ids: list[str],
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        local_host: str | None = None,
        use_local: bool = False,
        enable_cost: bool = False,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self._api_client = api_client
        self._install_ids = install_ids
        self._local_host = local_host
        self._use_local = use_local and local_host
        self._enable_cost = enable_cost
        self.data: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API for all installations."""
        result: dict[str, Any] = {}
        for install_id in self._install_ids:
            try:
                install_data = await self._fetch_installation_data(install_id)
                if install_data:
                    result[install_id] = install_data
            except Exception as err:
                _LOGGER.error(
                    "Error fetching data for installation %s: %s",
                    install_id,
                    err,
                    exc_info=True,
                )
                raise UpdateFailed(f"Failed to update: {err}") from err

        # Optionally merge local Jullix-Direct data into first installation
        if self._use_local and result and self._install_ids:
            try:
                from .local_client import JullixLocalClient

                local_client = JullixLocalClient(self._local_host or "")
                local_data = await local_client.get_ems_data()
                if local_data:
                    first_id = self._install_ids[0]
                    result[first_id] = _merge_local_data(
                        result.get(first_id, {}), local_data
                    )
            except Exception as exc:
                _LOGGER.debug("Local Jullix-Direct merge failed: %s", exc)

        return result

    async def _fetch_installation_data(self, install_id: str) -> dict[str, Any]:
        """Fetch all relevant data for a single installation."""
        data: dict[str, Any] = {}

        # Power summary
        try:
            summary = await self._api_client.get_power_summary(install_id)
            if summary:
                data["summary"] = summary
        except Exception as e:
            _LOGGER.debug("Power summary failed for %s: %s", install_id, e)

        # Detail endpoints
        for detail_type in ("battery", "solar", "grid", "home", "plug", "charger", "metering"):
            try:
                detail = await self._api_client.get_actual_detail(install_id, detail_type)
                if detail:
                    data[detail_type] = detail
            except Exception as e:
                _LOGGER.debug("Detail %s failed for %s: %s", detail_type, install_id, e)

        # Chargers list
        try:
            chargers = await self._api_client.get_chargers(install_id)
            if chargers:
                data["chargers"] = chargers
        except Exception as e:
            _LOGGER.debug("Chargers failed for %s: %s", install_id, e)

        # Plugs list
        try:
            plugs = await self._api_client.get_plugs(install_id)
            if plugs:
                data["plugs"] = plugs
        except Exception as e:
            _LOGGER.debug("Plugs failed for %s: %s", install_id, e)

        # Cost/savings (optional, less frequently updated)
        if self._enable_cost:
            try:
                cost = await self._api_client.get_cost_savings(install_id)
                if cost:
                    data["cost"] = cost
            except Exception as e:
                _LOGGER.debug("Cost failed for %s: %s", install_id, e)

        return data


def _merge_local_data(platform_data: dict[str, Any], local_data: dict[str, Any]) -> dict[str, Any]:
    """Merge local Jullix-Direct data into platform data. Local values override when present."""
    result = dict(platform_data)
    # Map local endpoint names to platform structure
    if "meter" in local_data and local_data["meter"]:
        result.setdefault("metering", {}).update(local_data["meter"])
    if "solar" in local_data and local_data["solar"]:
        result["solar"] = local_data["solar"]
    if "battery" in local_data and local_data["battery"]:
        result["battery"] = local_data["battery"]
    if "charger" in local_data and local_data["charger"]:
        result["charger"] = local_data["charger"]
    if "plug" in local_data and local_data["plug"]:
        result["plug"] = local_data["plug"]
    return result
