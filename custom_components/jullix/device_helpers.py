"""Device registry helpers (hub + service devices with via_device_id)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

MANUFACTURER = "Jullix"
HUB_MODEL = "Energy management"


def hub_identifier(install_id: str) -> tuple[str, str]:
    """Primary device identifier for an installation."""
    return (DOMAIN, install_id)


def device_info_hub(
    install_id: str,
    install_name: str,
    *,
    model: str | None = None,
    sw_version: str | None = None,
    hass: HomeAssistant | None = None,
) -> DeviceInfo:
    """Hub device for one Jullix site."""
    del hass  # hub has no via_device_id
    info: DeviceInfo = {
        "identifiers": {hub_identifier(install_id)},
        "name": f"Jullix – {install_name}",
        "manufacturer": MANUFACTURER,
        "model": model or HUB_MODEL,
    }
    if sw_version:
        info["sw_version"] = sw_version
    return info


def register_hub_device(
    hass: HomeAssistant,
    *,
    config_entry_id: str,
    install_id: str,
    install_name: str,
    model: str | None = None,
    sw_version: str | None = None,
) -> str:
    """Ensure hub exists in the device registry; return its device id."""
    registry = dr.async_get(hass)
    info = device_info_hub(
        install_id, install_name, model=model, sw_version=sw_version
    )
    device = registry.async_get_or_create(
        config_entry_id=config_entry_id,
        identifiers=info["identifiers"],
        manufacturer=info.get("manufacturer"),
        model=info.get("model"),
        name=info.get("name"),
        sw_version=info.get("sw_version"),
    )
    return device.id


def _via_hub(hass: HomeAssistant | None, install_id: str) -> dict[str, str]:
    """Link child devices to the hub via registry device id."""
    if hass is None:
        return {}
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={hub_identifier(install_id)})
    if device is None:
        return {}
    return {"via_device_id": device.id}


def device_info_grid(
    install_id: str, _install_name: str, *, hass: HomeAssistant | None = None
) -> DeviceInfo:
    """Grid / import-export power grouping."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_grid")},
        "name": "Grid",
        "manufacturer": MANUFACTURER,
        "model": "Grid connection",
        **_via_hub(hass, install_id),
    }


def device_info_solar(
    install_id: str, _install_name: str, *, hass: HomeAssistant | None = None
) -> DeviceInfo:
    """Solar production device."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_solar")},
        "name": "Solar",
        "manufacturer": MANUFACTURER,
        "model": "Solar PV",
        **_via_hub(hass, install_id),
    }


def device_info_home_consumption(
    install_id: str, _install_name: str, *, hass: HomeAssistant | None = None
) -> DeviceInfo:
    """Home consumption device."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_home")},
        "name": "Home",
        "manufacturer": MANUFACTURER,
        "model": "Consumption",
        **_via_hub(hass, install_id),
    }


def device_info_battery(
    install_id: str,
    _install_name: str,
    battery_index: int,
    multi: bool,
    *,
    hass: HomeAssistant | None = None,
) -> DeviceInfo:
    """One battery stack / unit."""
    name = f"Battery {battery_index + 1}" if multi else "Battery"
    return {
        "identifiers": {(DOMAIN, f"{install_id}_battery_{battery_index}")},
        "name": name,
        "manufacturer": MANUFACTURER,
        "model": "Battery",
        **_via_hub(hass, install_id),
    }


def device_info_charger(
    install_id: str,
    _install_name: str,
    mac: str,
    display_name: str,
    *,
    model: str | None = None,
    hass: HomeAssistant | None = None,
) -> DeviceInfo:
    """One EV charger."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_charger_{mac}")},
        "name": display_name,
        "manufacturer": MANUFACTURER,
        "model": model or "Charger",
        **_via_hub(hass, install_id),
    }


def device_info_plug(
    install_id: str,
    _install_name: str,
    mac: str,
    display_name: str,
    *,
    model: str | None = None,
    hass: HomeAssistant | None = None,
) -> DeviceInfo:
    """One smart plug."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_plug_{mac}")},
        "name": display_name,
        "manufacturer": MANUFACTURER,
        "model": model or "Smart plug",
        **_via_hub(hass, install_id),
    }


def device_info_system(
    install_id: str, _install_name: str, *, hass: HomeAssistant | None = None
) -> DeviceInfo:
    """Tariff, weather, algorithm, cost, metering, statistics."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_system")},
        "name": "System",
        "manufacturer": MANUFACTURER,
        "model": "Services",
        **_via_hub(hass, install_id),
    }


def device_info_power_overview(
    install_id: str, _install_name: str, *, hass: HomeAssistant | None = None
) -> DeviceInfo:
    """Summary / overview power lines (grid, solar, home, battery from summary API)."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_power")},
        "name": "Power",
        "manufacturer": MANUFACTURER,
        "model": "Power overview",
        **_via_hub(hass, install_id),
    }
