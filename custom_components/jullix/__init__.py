"""Jullix integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .api import JullixApiClient
from .const import (
    CONF_API_TOKEN,
    CONF_INSTALL_IDS,
    CONF_LOCAL_HOST,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    OPTION_ENABLE_COST,
    OPTION_USE_LOCAL,
)
from .coordinator import JullixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]

SERVICE_SET_CHARGER_CONTROL = "set_charger_control"
SERVICE_RUN_ALGORITHM_HOURLY = "run_algorithm_hourly"
SERVICE_ASSIGN_CHARGERSESSION = "assign_chargersession"
CHARGER_MODES = ["eco", "turbo", "max", "block"]

SCHEMA_SET_CHARGER_CONTROL = vol.Schema(
    {
        vol.Required("installation_id"): cv.string,
        vol.Required("charger_mac"): cv.string,
        vol.Optional("enabled"): cv.boolean,
        vol.Optional("mode"): vol.In(CHARGER_MODES),
        vol.Optional("max_power"): vol.All(vol.Coerce(float), vol.Range(1.4, 22.0)),
    }
)

SCHEMA_RUN_ALGORITHM_HOURLY = vol.Schema(
    {vol.Required("installation_id"): cv.string}
)

SCHEMA_ASSIGN_CHARGERSESSION = vol.Schema(
    {
        vol.Required("installation_id"): cv.string,
        vol.Required("session_id"): cv.string,
        vol.Optional("charger_mac"): cv.string,
        vol.Optional("car_id"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jullix from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api_token = entry.data.get(CONF_API_TOKEN)
    install_ids = entry.data.get(CONF_INSTALL_IDS, [])
    if not api_token or not install_ids:
        _LOGGER.error("Missing API token or installation IDs")
        return False

    api_client = JullixApiClient(api_token)
    options = entry.options or {}
    update_interval = options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = JullixDataUpdateCoordinator(
        hass=hass,
        api_client=api_client,
        install_ids=install_ids,
        update_interval=update_interval,
        local_host=entry.data.get(CONF_LOCAL_HOST),
        use_local=options.get(OPTION_USE_LOCAL, False),
        enable_cost=options.get(OPTION_ENABLE_COST, False),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
        "install_ids": install_ids,
        "local_host": entry.data.get(CONF_LOCAL_HOST),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_CHARGER_CONTROL):
        async def charger_control_handler(call: ServiceCall) -> None:
            await _handle_set_charger_control(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CHARGER_CONTROL,
            charger_control_handler,
            schema=SCHEMA_SET_CHARGER_CONTROL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RUN_ALGORITHM_HOURLY):
        async def run_algorithm_handler(call: ServiceCall) -> None:
            await _handle_run_algorithm_hourly(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_RUN_ALGORITHM_HOURLY,
            run_algorithm_handler,
            schema=SCHEMA_RUN_ALGORITHM_HOURLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_ASSIGN_CHARGERSESSION):
        async def assign_session_handler(call: ServiceCall) -> None:
            await _handle_assign_chargersession(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_ASSIGN_CHARGERSESSION,
            assign_session_handler,
            schema=SCHEMA_ASSIGN_CHARGERSESSION,
        )

    return True


async def _handle_set_charger_control(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle set_charger_control service call."""
    installation_id = call.data["installation_id"]
    charger_mac = call.data["charger_mac"]
    enabled = call.data.get("enabled")
    mode = call.data.get("mode")
    max_power = call.data.get("max_power")

    payload: dict[str, Any] = {}
    if enabled is not None:
        payload["enabled"] = enabled
    if mode is not None or max_power is not None:
        config: dict[str, Any] = {}
        if mode is not None:
            config["mode"] = mode
        if max_power is not None:
            config["max_power"] = max_power
        if config:
            config.setdefault("mode", "eco")
            payload["config"] = config

    if not payload:
        _LOGGER.warning("set_charger_control called with no options")
        return

    dom = hass.data.get(DOMAIN)
    if not dom:
        _LOGGER.warning("Jullix integration not loaded")
        return
    for entry_id, data in dom.items():
        if not isinstance(data, dict):
            continue
        install_ids = data.get("install_ids") or []
        if installation_id not in install_ids:
            continue
        api_client = data.get("api_client")
        if api_client:
            await api_client.set_charger_control(charger_mac, payload)
            coordinator = data.get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
            return

    _LOGGER.warning(
        "No Jullix config entry found for installation_id %s",
        installation_id,
    )


async def _handle_run_algorithm_hourly(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle run_algorithm_hourly service call."""
    installation_id = call.data["installation_id"]
    dom = hass.data.get(DOMAIN)
    if not dom:
        _LOGGER.warning("Jullix integration not loaded")
        return
    for _entry_id, data in dom.items():
        if not isinstance(data, dict):
            continue
        if installation_id not in (data.get("install_ids") or []):
            continue
        api_client = data.get("api_client")
        if api_client:
            await api_client.run_algorithm_hourly(installation_id)
            if coordinator := data.get("coordinator"):
                await coordinator.async_request_refresh()
            return
    _LOGGER.warning(
        "No Jullix config entry found for installation_id %s",
        installation_id,
    )


async def _handle_assign_chargersession(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle assign_chargersession service call."""
    installation_id = call.data["installation_id"]
    session_id = call.data["session_id"]
    payload: dict[str, Any] = {"session_id": session_id}
    if "charger_mac" in call.data:
        payload["charger_mac"] = call.data["charger_mac"]
    if "car_id" in call.data:
        payload["car_id"] = call.data["car_id"]
    dom = hass.data.get(DOMAIN)
    if not dom:
        _LOGGER.warning("Jullix integration not loaded")
        return
    for _entry_id, data in dom.items():
        if not isinstance(data, dict):
            continue
        if installation_id not in (data.get("install_ids") or []):
            continue
        api_client = data.get("api_client")
        if api_client:
            await api_client.assign_chargersession(payload)
            if coordinator := data.get("coordinator"):
                await coordinator.async_request_refresh()
            return
    _LOGGER.warning(
        "No Jullix config entry found for installation_id %s",
        installation_id,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
