"""Jullix select platform for charger mode."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPTION_ENABLE_CHARGER_CONTROL, OPTION_ENABLE_COST
from .device_helpers import device_info_charger, device_info_system
from .coordinator import JullixDataUpdateCoordinator
from .sensors.base import get_installation_snapshot
from .models import JullixInstallationSnapshot

_LOGGER = logging.getLogger(__name__)

CHARGER_MODES = ["eco", "turbo", "max", "block"]
TARIFF_OPTIONS = ["single", "dual"]


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
    enable_cost = options.get(OPTION_ENABLE_COST, False)
    entity_discovery = data.get("entity_discovery")

    entities: list[SelectEntity] = []
    for install_id in install_ids:
        snap = get_installation_snapshot(coordinator, install_id)
        install_name = snap.installation_display_name(install_id)

        if enable_cost and snap.tariff is not None:
            entities.append(
                JullixTariffSelect(
                    coordinator=coordinator,
                    api_client=api_client,
                    install_id=install_id,
                    install_name=install_name,
                    unique_id=f"{install_id}_tariff_select",
                    name="Tariff",
                    device_info=device_info_system(install_id, install_name),
                    translation_key="tariff_select",
                )
            )

        if not enable_charger:
            continue

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
                JullixChargerModeSelect(
                    coordinator=coordinator,
                    api_client=api_client,
                    install_id=install_id,
                    install_name=install_name,
                    charger_index=i,
                    charger_mac=ch.mac,
                    unique_id=f"{install_id}_charger_{ch.mac}_mode",
                    name="Mode",
                    device_info=ch_dev,
                    translation_key="charger_mode",
                )
            )

    if entity_discovery:
        entity_discovery.register_platform(
            "select",
            lambda iid, snap: _discovered_select_entities(
                coordinator, api_client, iid, snap, enable_charger
            ),
            async_add_entities,
        )

    async_add_entities(entities)


def _discovered_select_entities(
    coordinator: JullixDataUpdateCoordinator,
    api_client: Any,
    install_id: str,
    snap: JullixInstallationSnapshot,
    enable_charger: bool,
) -> list[SelectEntity]:
    if not enable_charger:
        return []
    install_name = snap.installation_display_name(install_id)
    entities: list[SelectEntity] = []
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
            JullixChargerModeSelect(
                coordinator=coordinator,
                api_client=api_client,
                install_id=install_id,
                install_name=install_name,
                charger_index=i,
                charger_mac=ch.mac,
                unique_id=f"{install_id}_charger_{ch.mac}_mode",
                name="Mode",
                device_info=ch_dev,
                translation_key="charger_mode",
            )
        )
    return entities


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
        *,
        device_info: DeviceInfo | None = None,
        translation_key: str | None = None,
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
        if translation_key is not None:
            self._attr_translation_key = translation_key
        if device_info is None:
            raise ValueError("device_info is required for JullixChargerModeSelect")
        self._attr_device_info = device_info

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ctrl = snap.charger_control.get(self._charger_mac)
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
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ctrl = snap.charger_control.get(self._charger_mac)
        config: dict[str, Any] = {}
        if isinstance(ctrl, dict):
            config = dict(ctrl.get("config", ctrl) or {})
        config["mode"] = option
        payload: dict[str, Any] = {"config": config}
        await self._api_client.set_charger_control(self._charger_mac, payload)
        await self.coordinator.async_request_refresh()


class JullixTariffSelect(CoordinatorEntity[JullixDataUpdateCoordinator], SelectEntity):
    """Select entity for active energy tariff."""

    _attr_options = TARIFF_OPTIONS
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
        device_info: DeviceInfo,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._api_client = api_client
        self._install_id = install_id
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        self._attr_device_info = device_info
        self._attr_translation_key = translation_key

    @callback
    def _handle_coordinator_update(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        tariff = snap.tariff
        current = None
        if isinstance(tariff, dict):
            current = tariff.get("tariff", tariff.get("name", tariff.get("type")))
        elif tariff is not None:
            current = str(tariff)
        if current and str(current).lower() in TARIFF_OPTIONS:
            self._attr_current_option = str(current).lower()
        else:
            self._attr_current_option = None
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        await self._api_client.update_tariff(
            self._install_id, {"tariff": option}
        )
        await self.coordinator.async_request_refresh()
