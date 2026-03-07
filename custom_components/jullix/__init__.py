"""Jullix integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

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

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
