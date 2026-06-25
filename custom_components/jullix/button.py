"""Jullix button platform for common integration actions."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JullixDataUpdateCoordinator
from .device_helpers import device_info_system

SERVICE_RUN_ALGORITHM = "run_algorithm_hourly"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Jullix buttons from a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return

    coordinator: JullixDataUpdateCoordinator = data["coordinator"]
    install_ids: list[str] = data["install_ids"]

    entities: list[ButtonEntity] = []
    for install_id in install_ids:
        snap = coordinator.data.get(install_id)
        install_name = (
            snap.installation_display_name(install_id)
            if snap
            else f"Installation {install_id[:8]}"
        )
        sys_dev = device_info_system(install_id, install_name)
        entities.append(
            JullixRunAlgorithmButton(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                unique_id=f"{install_id}_run_algorithm_hourly",
                name="Run hourly optimization",
                device_info=sys_dev,
                translation_key="run_algorithm_hourly",
            )
        )

    async_add_entities(entities)


class JullixRunAlgorithmButton(CoordinatorEntity[JullixDataUpdateCoordinator], ButtonEntity):
    """Trigger the Jullix hourly optimization algorithm."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        unique_id: str,
        name: str,
        device_info: DeviceInfo,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._install_id = install_id
        self._install_name = install_name
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        self._attr_device_info = device_info
        self._attr_translation_key = translation_key

    async def async_press(self) -> None:
        """Call the run_algorithm_hourly service for this installation."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_RUN_ALGORITHM,
            {"installation_id": self._install_id},
            blocking=True,
        )
