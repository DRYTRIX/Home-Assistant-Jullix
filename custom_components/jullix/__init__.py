"""Jullix integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, SOURCE_REAUTH
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import JullixApiClient
from .const import (
    CONF_API_TOKEN,
    CONF_INSTALL_IDS,
    CONF_LOCAL_HOST,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    OPTION_ENABLE_ADAPTIVE_POLLING,
    OPTION_ENABLE_CHARGER_SESSION,
    OPTION_ENABLE_COST,
    OPTION_ENABLE_EVENTS,
    OPTION_ENABLE_INSIGHTS,
    OPTION_ENABLE_SESSION_HISTORY,
    OPTION_ENABLE_STATISTICS,
    OPTION_USE_LOCAL,
)

_LOGGER = logging.getLogger(__name__)


def _configured_installation_ids(hass: HomeAssistant) -> set[str]:
    """All installation IDs across loaded Jullix config entries."""
    ids: set[str] = set()
    dom = hass.data.get(DOMAIN)
    if not isinstance(dom, dict):
        return ids
    for data in dom.values():
        if isinstance(data, dict):
            ids.update(data.get("install_ids") or [])
    return ids


def _validate_installation_id(hass: HomeAssistant, installation_id: str) -> None:
    """Raise ServiceValidationError if installation_id is not configured."""
    if installation_id not in _configured_installation_ids(hass):
        raise ServiceValidationError(
            f"No Jullix configuration includes installation_id {installation_id!r}. "
            "Use an installation ID from your Jullix account (see the integration entry)."
        )

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]

SERVICE_SET_CHARGER_CONTROL = "set_charger_control"
SERVICE_RUN_ALGORITHM_HOURLY = "run_algorithm_hourly"
SERVICE_ASSIGN_CHARGERSESSION = "assign_chargersession"
SERVICE_UPDATE_TARIFF = "update_tariff"
CHARGER_MODES = ["eco", "turbo", "max", "block"]

SCHEMA_SET_CHARGER_CONTROL = vol.Schema(
    {
        vol.Required("installation_id"): cv.string,
        vol.Required("charger_mac"): cv.string,
        vol.Optional("enabled"): cv.boolean,
        vol.Optional("mode"): vol.In(CHARGER_MODES),
        vol.Optional("max_power"): vol.All(vol.Coerce(float), vol.Range(1.4, 22.0)),
    }
)

SCHEMA_RUN_ALGORITHM_HOURLY = vol.Schema(
    {vol.Required("installation_id"): cv.string}
)

SCHEMA_ASSIGN_CHARGERSESSION = vol.Schema(
    {
        vol.Required("installation_id"): cv.string,
        vol.Required("session_id"): cv.string,
        vol.Optional("charger_mac"): cv.string,
        vol.Optional("car_id"): cv.string,
    }
)

SCHEMA_UPDATE_TARIFF = vol.Schema(
    {
        vol.Required("installation_id"): cv.string,
        vol.Required("tariff"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jullix from a config entry."""
    from .coordinator import JullixDataUpdateCoordinator
    from .session_history import SessionHistoryRecorder

    hass.data.setdefault(DOMAIN, {})

    api_token = entry.data.get(CONF_API_TOKEN)
    install_ids = entry.data.get(CONF_INSTALL_IDS, [])
    if not api_token or not install_ids:
        _LOGGER.error("Missing API token or installation IDs")
        return False

    api_client = JullixApiClient(api_token)
    options = entry.options or {}
    update_interval = options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    session_hist: SessionHistoryRecorder | None = None
    if options.get(OPTION_ENABLE_SESSION_HISTORY, False):
        session_hist = SessionHistoryRecorder(hass, entry.entry_id)
        await session_hist.async_load()

    async def _trigger_reauth() -> None:
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data=entry.data,
        )

    coordinator = JullixDataUpdateCoordinator(
        hass=hass,
        api_client=api_client,
        install_ids=install_ids,
        update_interval=update_interval,
        local_host=entry.data.get(CONF_LOCAL_HOST),
        use_local=options.get(OPTION_USE_LOCAL, False),
        enable_cost=options.get(OPTION_ENABLE_COST, False),
        enable_statistics=options.get(OPTION_ENABLE_STATISTICS, False),
        enable_insights=options.get(OPTION_ENABLE_INSIGHTS, True),
        enable_events=options.get(OPTION_ENABLE_EVENTS, True),
        enable_adaptive_polling=options.get(OPTION_ENABLE_ADAPTIVE_POLLING, False),
        enable_charger_session=options.get(OPTION_ENABLE_CHARGER_SESSION, True),
        session_history=session_hist,
        on_auth_error=_trigger_reauth,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
        "install_ids": install_ids,
        "local_host": entry.data.get(CONF_LOCAL_HOST),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_CHARGER_CONTROL):
        async def charger_control_handler(call: ServiceCall) -> None:
            await _handle_set_charger_control(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CHARGER_CONTROL,
            charger_control_handler,
            schema=SCHEMA_SET_CHARGER_CONTROL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RUN_ALGORITHM_HOURLY):
        async def run_algorithm_handler(call: ServiceCall) -> None:
            await _handle_run_algorithm_hourly(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_RUN_ALGORITHM_HOURLY,
            run_algorithm_handler,
            schema=SCHEMA_RUN_ALGORITHM_HOURLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_ASSIGN_CHARGERSESSION):
        async def assign_session_handler(call: ServiceCall) -> None:
            await _handle_assign_chargersession(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_ASSIGN_CHARGERSESSION,
            assign_session_handler,
            schema=SCHEMA_ASSIGN_CHARGERSESSION,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_TARIFF):
        async def update_tariff_handler(call: ServiceCall) -> None:
            await _handle_update_tariff(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_TARIFF,
            update_tariff_handler,
            schema=SCHEMA_UPDATE_TARIFF,
        )

    return True


async def _handle_set_charger_control(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle set_charger_control service call."""
    installation_id = call.data["installation_id"]
    _validate_installation_id(hass, installation_id)
    charger_mac = call.data["charger_mac"]
    enabled = call.data.get("enabled")
    mode = call.data.get("mode")
    max_power = call.data.get("max_power")

    payload: dict[str, Any] = {}
    if enabled is not None:
        payload["enabled"] = enabled
    if mode is not None or max_power is not None:
        config: dict[str, Any] = {}
        if mode is not None:
            config["mode"] = mode
        if max_power is not None:
            config["max_power"] = max_power
        if config:
            config.setdefault("mode", "eco")
            payload["config"] = config

    if not payload:
        raise HomeAssistantError(
            "set_charger_control requires at least one of: enabled, mode, max_power"
        )

    dom = hass.data.get(DOMAIN)
    if not dom:
        raise HomeAssistantError("Jullix integration is not loaded")
    for _entry_id, data in dom.items():
        if not isinstance(data, dict):
            continue
        install_ids = data.get("install_ids") or []
        if installation_id not in install_ids:
            continue
        api_client = data.get("api_client")
        if api_client:
            await api_client.set_charger_control(charger_mac, payload)
            coordinator = data.get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
            return

    raise HomeAssistantError(
        f"No Jullix config entry found for installation_id {installation_id}"
    )


async def _handle_run_algorithm_hourly(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle run_algorithm_hourly service call."""
    installation_id = call.data["installation_id"]
    _validate_installation_id(hass, installation_id)
    dom = hass.data.get(DOMAIN)
    if not dom:
        raise HomeAssistantError("Jullix integration is not loaded")
    for _entry_id, data in dom.items():
        if not isinstance(data, dict):
            continue
        if installation_id not in (data.get("install_ids") or []):
            continue
        api_client = data.get("api_client")
        if api_client:
            await api_client.run_algorithm_hourly(installation_id)
            if coordinator := data.get("coordinator"):
                await coordinator.async_request_refresh()
            return
    raise HomeAssistantError(
        f"No Jullix config entry found for installation_id {installation_id}"
    )


async def _handle_assign_chargersession(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle assign_chargersession service call."""
    installation_id = call.data["installation_id"]
    _validate_installation_id(hass, installation_id)
    session_id = call.data["session_id"]
    payload: dict[str, Any] = {"session_id": session_id}
    if "charger_mac" in call.data:
        payload["charger_mac"] = call.data["charger_mac"]
    if "car_id" in call.data:
        payload["car_id"] = call.data["car_id"]
    dom = hass.data.get(DOMAIN)
    if not dom:
        raise HomeAssistantError("Jullix integration is not loaded")
    for _entry_id, data in dom.items():
        if not isinstance(data, dict):
            continue
        if installation_id not in (data.get("install_ids") or []):
            continue
        api_client = data.get("api_client")
        if api_client:
            await api_client.assign_chargersession(payload)
            if coordinator := data.get("coordinator"):
                await coordinator.async_request_refresh()
            return
    raise HomeAssistantError(
        f"No Jullix config entry found for installation_id {installation_id}"
    )


async def _handle_update_tariff(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle update_tariff service call."""
    installation_id = call.data["installation_id"]
    _validate_installation_id(hass, installation_id)
    payload = {"tariff": call.data["tariff"]}
    dom = hass.data.get(DOMAIN)
    if not dom:
        raise HomeAssistantError("Jullix integration is not loaded")
    for _entry_id, data in dom.items():
        if not isinstance(data, dict):
            continue
        if installation_id not in (data.get("install_ids") or []):
            continue
        api_client = data.get("api_client")
        if api_client:
            await api_client.update_tariff(installation_id, payload)
            if coordinator := data.get("coordinator"):
                await coordinator.async_request_refresh()
            return
    raise HomeAssistantError(
        f"No Jullix config entry found for installation_id {installation_id}"
    )


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the config entry (no sensitive data)."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    options = dict(entry.options) if entry.options else {}
    local_host = entry.data.get(CONF_LOCAL_HOST)
    use_local_opt = bool(options.get(OPTION_USE_LOCAL, False))

    if not isinstance(entry_data, dict):
        return {
            "config_entry_id": entry.entry_id,
            "loaded": False,
            "connection_mode": "unknown",
            "api_status": "unknown",
            "options_effective": {**options, "local_host_configured": bool(local_host)},
        }

    if local_host and use_local_opt:
        connection_mode = "cloud_with_local_merge"
    elif local_host:
        connection_mode = "cloud_local_configured"
    else:
        connection_mode = "cloud"

    coordinator = entry_data.get("coordinator")
    last_errors = (
        dict(getattr(coordinator, "last_installation_errors", {}))
        if coordinator
        else {}
    )
    last_ok = bool(getattr(coordinator, "last_update_success", False))
    api_status = "ok" if last_ok and not last_errors else "degraded" if last_ok else "error"

    result: dict[str, Any] = {
        "config_entry_id": entry.entry_id,
        "installation_ids": list(entry_data.get("install_ids", [])),
        "local_host_configured": bool(entry_data.get("local_host")),
        "connection_mode": connection_mode,
        "api_status": api_status,
        "options": options,
        "options_effective": {**options, "local_host_configured": bool(local_host)},
    }

    if coordinator:
        inst_summary: dict[str, Any] = {}
        installations_resolved: list[dict[str, str]] = []
        data = getattr(coordinator, "data", None) or {}
        for iid, snap in data.items():
            if hasattr(snap, "chargers"):
                inst_summary[iid] = {
                    "chargers": len(snap.chargers),
                    "plugs": len(snap.plugs),
                    "battery_units": len(snap.battery_slots),
                }
            if hasattr(snap, "installation_display_name"):
                installations_resolved.append(
                    {
                        "installation_id": iid,
                        "display_name": snap.installation_display_name(iid),
                    }
                )
        result["coordinator"] = {
            "last_update_success": coordinator.last_update_success,
            "last_update_time": (
                coordinator.last_update_time.isoformat()
                if coordinator.last_update_time
                else None
            ),
            "last_installation_errors": {k: str(v) for k, v in last_errors.items()},
            "installation_snapshot_summary": inst_summary,
        }
        result["installations_resolved"] = installations_resolved

    return result


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if isinstance(entry_data, dict):
            coordinator = entry_data.get("coordinator")
            if coordinator and hasattr(coordinator, "async_shutdown"):
                await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
