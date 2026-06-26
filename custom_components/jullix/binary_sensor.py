"""Binary sensors for tariff, local EMS, and automation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import JullixDataUpdateCoordinator
from .derived import parse_hourly_tariff
from .device_helpers import (
    device_info_battery,
    device_info_charger,
    device_info_solar,
    device_info_system,
)
from .models import JullixInstallationSnapshot
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
    local_host = dom.get("local_host")

    entities: list[BinarySensorEntity] = []

    if options.get(OPTION_ENABLE_COST, False):
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

    if local_host:
        for iid in install_ids:
            snap = get_installation_snapshot(coordinator, iid)
            name = snap.installation_display_name(iid)
            entities.extend(
                create_local_ems_binary_entities(
                    coordinator=coordinator,
                    install_id=iid,
                    install_name=name,
                    snap=snap,
                )
            )

    if entities:
        async_add_entities(entities)


def create_local_ems_binary_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    *,
    snap: Any,
) -> list[BinarySensorEntity]:
    """Local EMS occupancy, three-phase, and fault binary sensors."""
    multi_battery = len(snap.battery_slots) > 1
    battery_dev = device_info_battery(install_id, install_name, 0, multi_battery)
    solar_dev = device_info_solar(install_id, install_name)

    if snap.chargers:
        ch = snap.chargers[0]
        model = ch.raw.get("model") or ch.raw.get("type")
        charger_dev = device_info_charger(
            install_id,
            install_name,
            ch.mac,
            ch.display_name,
            model=str(model) if model is not None else None,
        )
    elif snap.charger_detail_rows:
        charger_dev = device_info_charger(
            install_id,
            install_name,
            "local_0",
            "Charger",
        )
    else:
        charger_dev = device_info_system(install_id, install_name)

    specs: list[
        tuple[
            str,
            str,
            str,
            BinarySensorDeviceClass | None,
            Any,
            Callable[[JullixInstallationSnapshot], bool | None],
        ]
    ] = [
        (
            f"{install_id}_local_ev_occupied",
            "EV charger occupied",
            "local_ev_charger_occupied",
            BinarySensorDeviceClass.OCCUPANCY,
            charger_dev,
            lambda s: s.local_ems.charger_busy,
        ),
        (
            f"{install_id}_local_ev_three_phase",
            "EV three phase active",
            "local_ev_three_phase_active",
            BinarySensorDeviceClass.POWER,
            charger_dev,
            lambda s: s.local_ems.charger_three_phase,
        ),
        (
            f"{install_id}_local_battery_fault",
            "Battery fault",
            "local_battery_fault",
            BinarySensorDeviceClass.PROBLEM,
            battery_dev,
            _battery_fault_value,
        ),
        (
            f"{install_id}_local_solar_fault",
            "Solar fault",
            "local_solar_fault",
            BinarySensorDeviceClass.PROBLEM,
            solar_dev,
            _solar_fault_value,
        ),
    ]

    return [
        JullixLocalEmsBinarySensor(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            translation_key=tkey,
            device_info=dev,
            device_class=dclass,
            value_fn=value_fn,
        )
        for unique_id, name, tkey, dclass, dev, value_fn in specs
    ]


def _battery_fault_value(snap: JullixInstallationSnapshot) -> bool | None:
    if snap.battery_slots and snap.battery_slots[0].fault is not None:
        return snap.battery_slots[0].fault
    return snap.local_ems.battery_fault


def _solar_fault_value(snap: JullixInstallationSnapshot) -> bool | None:
    if snap.local_ems.solar_fault is not None:
        return snap.local_ems.solar_fault
    raw = snap.solar_detail.raw
    if isinstance(raw, dict) and "fault" in raw:
        return bool(raw["fault"])
    return None


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


class JullixLocalEmsBinarySensor(
    CoordinatorEntity[JullixDataUpdateCoordinator], BinarySensorEntity
):
    """Local EMS boolean field."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        unique_id: str,
        name: str,
        *,
        translation_key: str,
        device_info: Any,
        device_class: BinarySensorDeviceClass | None,
        value_fn: Callable[[JullixInstallationSnapshot], bool | None],
    ) -> None:
        super().__init__(coordinator)
        self._install_id = install_id
        self._value_fn = value_fn
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        self._attr_translation_key = translation_key
        self._attr_device_info = device_info
        if device_class is not None:
            self._attr_device_class = device_class

    @callback
    def _handle_coordinator_update(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        try:
            val = self._value_fn(snap)
            self._attr_is_on = val if val is not None else None
        except (TypeError, KeyError):
            self._attr_is_on = None
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        try:
            return self._value_fn(snap) is not None
        except (TypeError, KeyError):
            return False
