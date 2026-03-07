"""Jullix switch platform for charger and plug control."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPTION_ENABLE_CHARGER_CONTROL, OPTION_ENABLE_PLUG_CONTROL
from .coordinator import JullixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Jullix switches from a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return

    coordinator: JullixDataUpdateCoordinator = data["coordinator"]
    api_client = data["api_client"]
    install_ids: list[str] = data["install_ids"]
    options = entry.options or {}

    enable_charger = options.get(OPTION_ENABLE_CHARGER_CONTROL, True)
    enable_plug = options.get(OPTION_ENABLE_PLUG_CONTROL, True)

    entities: list[SwitchEntity] = []
    for install_id in install_ids:
        install_data = coordinator.data.get(install_id) or {}
        install_name = _get_install_name(install_data, install_id)

        if enable_charger:
            chargers = install_data.get("chargers") or []
            for i, ch in enumerate(chargers):
                if not isinstance(ch, dict):
                    continue
                mac = ch.get("mac", ch.get("mac_address", str(i)))
                name = ch.get("name", ch.get("label", f"Charger {i + 1}"))
                entities.append(
                    JullixChargerSwitch(
                        coordinator=coordinator,
                        api_client=api_client,
                        install_id=install_id,
                        install_name=install_name,
                        charger_index=i,
                        charger_mac=mac,
                        unique_id=f"{install_id}_charger_{mac}_switch",
                        name=f"{install_name} {name}",
                    )
                )

        if enable_plug:
            plugs = install_data.get("plugs") or []
            for i, plug in enumerate(plugs):
                if not isinstance(plug, dict):
                    continue
                mac = plug.get("mac", plug.get("mac_address", str(i)))
                name = plug.get("name", plug.get("label", f"Plug {i + 1}"))
                entities.append(
                    JullixPlugSwitch(
                        coordinator=coordinator,
                        api_client=api_client,
                        install_id=install_id,
                        install_name=install_name,
                        plug_index=i,
                        plug_mac=mac,
                        unique_id=f"{install_id}_plug_{mac}_switch",
                        name=f"{install_name} {name}",
                    )
                )

    async_add_entities(entities)


def _get_install_name(install_data: dict[str, Any], install_id: str) -> str:
    """Get installation display name."""
    return f"Installation {install_id[:8]}"


class JullixSwitch(CoordinatorEntity[JullixDataUpdateCoordinator], SwitchEntity):
    """Base class for Jullix switches."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        api_client: Any,
        install_id: str,
        install_name: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._install_id = install_id
        self._install_name = install_name
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, install_id)},
            "name": f"Jullix {install_name}",
            "manufacturer": "Innovoltus",
            "model": "Jullix EMS",
        }


class JullixChargerSwitch(JullixSwitch):
    """Switch for charger enable/disable."""

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
        **kwargs: Any,
    ) -> None:
        """Initialize the charger switch."""
        super().__init__(
            coordinator=coordinator,
            api_client=api_client,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._charger_index = charger_index
        self._charger_mac = charger_mac

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        chargers = install_data.get("chargers") or []
        charger_detail = install_data.get("charger") or []
        is_on = False
        if isinstance(chargers, list) and len(chargers) > self._charger_index:
            ch = chargers[self._charger_index]
            if isinstance(ch, dict):
                is_on = _is_enabled(ch)
        if not is_on and isinstance(charger_detail, list) and len(charger_detail) > self._charger_index:
            ch = charger_detail[self._charger_index]
            if isinstance(ch, dict):
                is_on = _is_enabled(ch)
        self._attr_is_on = is_on
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the charger on."""
        await self._api_client.set_charger_control(self._charger_mac, {"enabled": True})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the charger off."""
        await self._api_client.set_charger_control(self._charger_mac, {"enabled": False})
        await self.coordinator.async_request_refresh()


class JullixPlugSwitch(JullixSwitch):
    """Switch for smart plug on/off."""

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        api_client: Any,
        install_id: str,
        install_name: str,
        plug_index: int,
        plug_mac: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the plug switch."""
        super().__init__(
            coordinator=coordinator,
            api_client=api_client,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._plug_index = plug_index
        self._plug_mac = plug_mac

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        plugs = install_data.get("plugs") or []
        plug_detail = install_data.get("plug") or []
        is_on = False
        if isinstance(plugs, list) and len(plugs) > self._plug_index:
            p = plugs[self._plug_index]
            if isinstance(p, dict):
                is_on = _is_enabled(p)
        if not is_on and isinstance(plug_detail, list) and len(plug_detail) > self._plug_index:
            p = plug_detail[self._plug_index]
            if isinstance(p, dict):
                is_on = _is_enabled(p)
        self._attr_is_on = is_on
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the plug on."""
        await self._api_client.set_plug_control(self._plug_mac, {"enabled": True})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the plug off."""
        await self._api_client.set_plug_control(self._plug_mac, {"enabled": False})
        await self.coordinator.async_request_refresh()


def _is_enabled(obj: dict[str, Any]) -> bool:
    """Extract enabled/on state from device dict."""
    if obj.get("enabled") is True:
        return True
    if obj.get("on") is True:
        return True
    if obj.get("state", "").lower() in ("on", "charging", "enabled"):
        return True
    if obj.get("status", "").lower() in ("on", "charging", "enabled"):
        return True
    return False
