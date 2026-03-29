"""Jullix switch platform for charger and plug control."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPTION_ENABLE_CHARGER_CONTROL, OPTION_ENABLE_PLUG_CONTROL
from .device_helpers import device_info_charger, device_info_plug, device_info_hub
from .coordinator import JullixDataUpdateCoordinator
from .sensors.base import get_installation_snapshot

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
        snap = get_installation_snapshot(coordinator, install_id)
        install_name = snap.installation_display_name(install_id)

        if enable_charger:
            for i, ch in enumerate(snap.chargers):
                model = ch.raw.get("model") or ch.raw.get("type")
                if model is not None:
                    model = str(model)
                ch_dev = device_info_charger(
                    install_id,
                    install_name,
                    ch.mac,
                    ch.display_name,
                    model=model,
                )
                entities.append(
                    JullixChargerSwitch(
                        coordinator=coordinator,
                        api_client=api_client,
                        install_id=install_id,
                        install_name=install_name,
                        charger_index=i,
                        charger_mac=ch.mac,
                        unique_id=f"{install_id}_charger_{ch.mac}_switch",
                        name="Charging",
                        device_info=ch_dev,
                        translation_key="charger_charging",
                    )
                )

        if enable_plug:
            for i, plug in enumerate(snap.plugs):
                model = plug.raw.get("model") or plug.raw.get("type")
                if model is not None:
                    model = str(model)
                plug_dev = device_info_plug(
                    install_id,
                    install_name,
                    plug.mac,
                    plug.display_name,
                    model=model,
                )
                entities.append(
                    JullixPlugSwitch(
                        coordinator=coordinator,
                        api_client=api_client,
                        install_id=install_id,
                        install_name=install_name,
                        plug_index=i,
                        plug_mac=plug.mac,
                        unique_id=f"{install_id}_plug_{plug.mac}_switch",
                        name="Switch",
                        device_info=plug_dev,
                        translation_key="plug_switch",
                    )
                )

    async_add_entities(entities)


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
        *,
        device_info: DeviceInfo | None = None,
        translation_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._install_id = install_id
        self._install_name = install_name
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        if translation_key is not None:
            self._attr_translation_key = translation_key
        self._attr_device_info = device_info or device_info_hub(
            install_id, install_name
        )


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
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        is_on = False
        if self._charger_index < len(snap.chargers):
            is_on = _is_enabled(snap.chargers[self._charger_index].raw)
        if (
            not is_on
            and self._charger_index < len(snap.charger_detail_rows)
        ):
            is_on = _is_enabled(snap.charger_detail_rows[self._charger_index])
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
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        is_on = False
        if self._plug_index < len(snap.plugs):
            is_on = _is_enabled(snap.plugs[self._plug_index].raw)
        if not is_on and self._plug_index < len(snap.plug_detail_rows):
            is_on = _is_enabled(snap.plug_detail_rows[self._plug_index])
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
    """Extract enabled/on state from device dict (API uses 'active' for chargers)."""
    if obj.get("active") is True:
        return True
    if obj.get("enabled") is True:
        return True
    if obj.get("on") is True:
        return True
    if obj.get("state", "").lower() in ("on", "charging", "enabled"):
        return True
    if obj.get("status", "").lower() in ("on", "charging", "enabled"):
        return True
    if obj.get("plug_state") is True:
        return True
    return False
