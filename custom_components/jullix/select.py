"""Jullix select platform for charger mode."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPTION_ENABLE_CHARGER_CONTROL
from .coordinator import JullixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CHARGER_MODES = ["eco", "turbo", "max", "block"]


def _get_install_name(install_data: dict[str, Any], install_id: str) -> str:
    """Get installation display name."""
    return f"Installation {install_id[:8]}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Jullix select entities from a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return

    coordinator: JullixDataUpdateCoordinator = data["coordinator"]
    api_client = data["api_client"]
    install_ids: list[str] = data["install_ids"]
    options = entry.options or {}
    enable_charger = options.get(OPTION_ENABLE_CHARGER_CONTROL, True)

    entities: list[SelectEntity] = []
    for install_id in install_ids:
        install_data = coordinator.data.get(install_id) or {}
        install_name = _get_install_name(install_data, install_id)

        if not enable_charger:
            continue

        chargers = install_data.get("chargers") or []
        for i, ch in enumerate(chargers):
            if not isinstance(ch, dict):
                continue
            mac = ch.get("id", ch.get("device_id", ch.get("mac", ch.get("mac_address", str(i)))))
            name = ch.get("name", ch.get("description", ch.get("label", f"Charger {i + 1}")))
            entities.append(
                JullixChargerModeSelect(
                    coordinator=coordinator,
                    api_client=api_client,
                    install_id=install_id,
                    install_name=install_name,
                    charger_index=i,
                    charger_mac=mac,
                    unique_id=f"{install_id}_charger_{mac}_mode",
                    name=f"{install_name} {name} mode",
                )
            )

    async_add_entities(entities)


class JullixChargerModeSelect(
    CoordinatorEntity[JullixDataUpdateCoordinator], SelectEntity
):
    """Select entity for charger mode (eco, turbo, max, block)."""

    _attr_options = CHARGER_MODES
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        api_client: Any,
        install_id: str,
        install_name: str,
        charger_index: int,
        charger_mac: str,
        unique_id: str,
        name: str,
    ) -> None:
        """Initialize the charger mode select."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._install_id = install_id
        self._install_name = install_name
        self._charger_index = charger_index
        self._charger_mac = charger_mac
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, install_id)},
            "name": f"Jullix {install_name}",
            "manufacturer": "Innovoltus",
            "model": "Jullix EMS",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        controls = install_data.get("charger_control") or {}
        ctrl = controls.get(self._charger_mac)
        current = None
        if isinstance(ctrl, dict):
            config = ctrl.get("config", ctrl)
            if isinstance(config, dict):
                current = config.get("mode")
        if current and str(current).lower() in CHARGER_MODES:
            self._attr_current_option = str(current).lower()
        else:
            self._attr_current_option = None
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        """Set charger mode."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        controls = install_data.get("charger_control") or {}
        ctrl = controls.get(self._charger_mac)
        config: dict[str, Any] = {}
        if isinstance(ctrl, dict):
            config = dict(ctrl.get("config", ctrl) or {})
        config["mode"] = option
        payload: dict[str, Any] = {"config": config}
        await self._api_client.set_charger_control(self._charger_mac, payload)
        await self.coordinator.async_request_refresh()
