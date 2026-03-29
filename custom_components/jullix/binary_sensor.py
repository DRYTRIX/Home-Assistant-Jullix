"""Binary sensors for tariff and automation."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import JullixDataUpdateCoordinator
from .derived import parse_hourly_tariff
from .device_helpers import device_info_system
from .sensors.base import get_installation_snapshot


async def async_setup_entry(
    hass: Any,
    entry: Any,
    async_add_entities: Any,
) -> None:
    from .const import OPTION_ENABLE_COST

    dom = hass.data[DOMAIN].get(entry.entry_id)
    if not dom:
        return
    coordinator: JullixDataUpdateCoordinator = dom["coordinator"]
    install_ids: list[str] = dom["install_ids"]
    options = entry.options or {}
    if not options.get(OPTION_ENABLE_COST, False):
        return

    entities: list[BinarySensorEntity] = []
    for iid in install_ids:
        snap = get_installation_snapshot(coordinator, iid)
        name = snap.installation_display_name(iid)
        entities.append(
            JullixPeakTariffBinarySensor(
                coordinator=coordinator,
                install_id=iid,
                install_name=name,
            )
        )
    async_add_entities(entities)


class JullixPeakTariffBinarySensor(
    CoordinatorEntity[JullixDataUpdateCoordinator], BinarySensorEntity
):
    """On when current hour price is near the daily maximum."""

    _attr_has_entity_name = True
    _attr_name = "Peak tariff"
    _attr_translation_key = "peak_tariff"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._install_id = install_id
        self._attr_unique_id = f"{DOMAIN}_{install_id}_peak_tariff"
        self._attr_device_info = device_info_system(install_id, install_name)

    @callback
    def _handle_coordinator_update(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        ins = parse_hourly_tariff(
            snap.cost_hourly_price,
            reference_local=dt_util.now(),
        )
        self._attr_is_on = ins.is_peak_now if ins else None
        super()._handle_coordinator_update()
