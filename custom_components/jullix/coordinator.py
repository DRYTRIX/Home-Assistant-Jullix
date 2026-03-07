"""Data update coordinator for Jullix integration."""

from __future__ import annotations

import logging
from datetime import date, timedelta
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

        # Power summary: API returns { "data": { "powers", "extra", ... }, "status": "ok" }
        try:
            raw = await self._api_client.get_power_summary(install_id)
            if raw:
                data["summary"] = raw.get("data", raw)
        except Exception as e:
            _LOGGER.debug("Power summary failed for %s: %s", install_id, e)

        # Detail endpoints: API returns { "data": <array or object>, "status": "ok" }
        for detail_type in ("battery", "solar", "grid", "home", "plug", "charger", "metering"):
            try:
                raw = await self._api_client.get_actual_detail(install_id, detail_type)
                if not raw:
                    continue
                detail = raw.get("data", raw)
                if detail_type == "battery" and isinstance(detail, list):
                    # Normalize: each item has "battery": { "soc", ... } and root "power"
                    data["battery"] = [
                        {
                            "soc": (item.get("battery") or {}).get("soc"),
                            "power": item.get("power"),
                            "name": item.get("name"),
                            "localid": item.get("localid"),
                            "id": item.get("id"),
                        }
                        for item in detail
                        if isinstance(item, dict)
                    ]
                elif detail_type == "solar" and isinstance(detail, list):
                    # Use first device; sensor expects dict with power
                    data["solar"] = detail[0] if detail and isinstance(detail[0], dict) else {}
                elif detail_type == "grid" and isinstance(detail, dict):
                    data["grid"] = detail
                elif detail_type == "home" and isinstance(detail, dict):
                    data["home"] = detail
                elif detail_type == "metering" and isinstance(detail, dict):
                    data["metering"] = detail
                elif detail_type in ("plug", "charger") and isinstance(detail, list):
                    data[detail_type] = detail
                else:
                    data[detail_type] = detail
            except Exception as e:
                _LOGGER.debug("Detail %s failed for %s: %s", detail_type, install_id, e)

        # Chargers list and per-charger control/status
        try:
            chargers = await self._api_client.get_chargers(install_id)
            if chargers:
                data["chargers"] = chargers
                data["charger_control"] = {}
                for ch in chargers:
                    if not isinstance(ch, dict):
                        continue
                    mac = ch.get("id", ch.get("device_id", ch.get("mac", ch.get("mac_address"))))
                    if not mac:
                        continue
                    try:
                        ctrl = await self._api_client.get_charger_control(mac)
                        if ctrl:
                            data["charger_control"][mac] = ctrl.get("data", ctrl)
                    except Exception as ce:
                        _LOGGER.debug("Charger control failed for %s: %s", mac, ce)
        except Exception as e:
            _LOGGER.debug("Chargers failed for %s: %s", install_id, e)

        # Plugs list and installation-level plug energy (today)
        try:
            plugs = await self._api_client.get_plugs(install_id)
            if plugs:
                data["plugs"] = plugs
                try:
                    today = date.today()
                    plug_energy = await self._api_client.get_history_plug_energy(
                        install_id, today.year, today.month, today.day
                    )
                    if plug_energy:
                        data["plug_energy_today"] = plug_energy.get("data", plug_energy)
                except Exception as pe:
                    _LOGGER.debug("Plug energy history failed for %s: %s", install_id, pe)
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

        # Algorithm overview (optimization state)
        try:
            overview = await self._api_client.get_algorithm_overview(install_id)
            if overview:
                data["algorithm_overview"] = overview.get("data", overview)
        except Exception as e:
            _LOGGER.debug("Algorithm overview failed for %s: %s", install_id, e)

        # Tariff
        try:
            tariff = await self._api_client.get_tariff(install_id)
            if tariff:
                data["tariff"] = tariff.get("data", tariff)
        except Exception as e:
            _LOGGER.debug("Tariff failed for %s: %s", install_id, e)

        # Weather forecast
        try:
            weather = await self._api_client.get_weather_forecast(install_id)
            if weather:
                data["weather_forecast"] = weather.get("data", weather)
        except Exception as e:
            _LOGGER.debug("Weather forecast failed for %s: %s", install_id, e)

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
