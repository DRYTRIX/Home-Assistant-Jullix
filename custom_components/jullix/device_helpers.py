"""Device registry helpers (hub + service devices with via_device)."""

from __future__ import annotations

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
) -> DeviceInfo:
    """Hub device for one Jullix site."""
    info: DeviceInfo = {
        "identifiers": {hub_identifier(install_id)},
        "name": f"Jullix – {install_name}",
        "manufacturer": MANUFACTURER,
        "model": model or HUB_MODEL,
    }
    if sw_version:
        info["sw_version"] = sw_version
    return info


def _via_hub(install_id: str) -> dict[str, tuple[str, str]]:
    return {"via_device": hub_identifier(install_id)}


def device_info_grid(install_id: str, _install_name: str) -> DeviceInfo:
    """Grid / import-export power grouping."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_grid")},
        "name": "Grid",
        "manufacturer": MANUFACTURER,
        "model": "Grid connection",
        **_via_hub(install_id),
    }


def device_info_solar(install_id: str, _install_name: str) -> DeviceInfo:
    """Solar production device."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_solar")},
        "name": "Solar",
        "manufacturer": MANUFACTURER,
        "model": "Solar PV",
        **_via_hub(install_id),
    }


def device_info_home_consumption(install_id: str, _install_name: str) -> DeviceInfo:
    """Home consumption device."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_home")},
        "name": "Home",
        "manufacturer": MANUFACTURER,
        "model": "Consumption",
        **_via_hub(install_id),
    }


def device_info_battery(
    install_id: str, _install_name: str, battery_index: int, multi: bool
) -> DeviceInfo:
    """One battery stack / unit."""
    name = f"Battery {battery_index + 1}" if multi else "Battery"
    return {
        "identifiers": {(DOMAIN, f"{install_id}_battery_{battery_index}")},
        "name": name,
        "manufacturer": MANUFACTURER,
        "model": "Battery",
        **_via_hub(install_id),
    }


def device_info_charger(
    install_id: str,
    _install_name: str,
    mac: str,
    display_name: str,
    *,
    model: str | None = None,
) -> DeviceInfo:
    """One EV charger."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_charger_{mac}")},
        "name": display_name,
        "manufacturer": MANUFACTURER,
        "model": model or "Charger",
        **_via_hub(install_id),
    }


def device_info_plug(
    install_id: str,
    _install_name: str,
    mac: str,
    display_name: str,
    *,
    model: str | None = None,
) -> DeviceInfo:
    """One smart plug."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_plug_{mac}")},
        "name": display_name,
        "manufacturer": MANUFACTURER,
        "model": model or "Smart plug",
        **_via_hub(install_id),
    }


def device_info_system(install_id: str, _install_name: str) -> DeviceInfo:
    """Tariff, weather, algorithm, cost, metering, statistics."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_system")},
        "name": "System",
        "manufacturer": MANUFACTURER,
        "model": "Services",
        **_via_hub(install_id),
    }


def device_info_power_overview(install_id: str, _install_name: str) -> DeviceInfo:
    """Summary / overview power lines (grid, solar, home, battery from summary API)."""
    return {
        "identifiers": {(DOMAIN, f"{install_id}_power")},
        "name": "Power",
        "manufacturer": MANUFACTURER,
        "model": "Power overview",
        **_via_hub(install_id),
    }
