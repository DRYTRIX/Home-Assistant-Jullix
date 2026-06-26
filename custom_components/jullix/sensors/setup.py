"""Sensor platform setup (aggregates entity factories)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import (
    DOMAIN,
    OPTION_ENABLE_CHARGER_SESSION,
    OPTION_ENABLE_COST,
    OPTION_ENABLE_INSIGHTS,
    OPTION_ENABLE_SESSION_HISTORY,
    OPTION_ENABLE_STATISTICS,
)
from ..coordinator import JullixDataUpdateCoordinator
from .algorithm_extended import create_algorithm_extended_entities
from .automation_helpers import create_automation_helper_entities
from .charger_extended import create_charger_extended_entities
from .base import JullixSensor, get_installation_snapshot
from .battery import create_battery_entities
from .charger import create_charger_entities
from .charger_intel import create_charger_intel_entities
from .cost import create_cost_entities
from .diagnostic import create_diagnostic_entities
from .energy import (
    create_metering_entities,
    create_plug_entities,
    create_solar_home_entities,
    create_statistics_entities,
    create_summary_power_entities,
    maybe_algorithm_entity,
    maybe_plug_energy_today_entity,
    maybe_tariff_entity,
    maybe_weather_alarm_entity,
    maybe_weather_forecast_entity,
)
from .grid import create_grid_entities
from .insights import create_insight_entities
from .local_ems import create_local_ems_entities
from .session_history import create_session_history_entities
from ..models import JullixInstallationSnapshot


def create_discovered_sensor_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    snap: JullixInstallationSnapshot,
) -> list[JullixSensor]:
    """Entity factory for dynamically discovered chargers/plugs."""
    install_name = snap.installation_display_name(install_id)
    entities: list[JullixSensor] = []
    entities.extend(
        create_charger_entities(
            coordinator, install_id, install_name, snap=snap
        )
    )
    entities.extend(
        create_charger_extended_entities(
            coordinator, install_id, install_name, snap=snap
        )
    )
    entities.extend(
        create_plug_entities(coordinator, install_id, install_name, snap=snap)
    )
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Jullix sensors from a config entry."""
    from ..const import DOMAIN

    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return

    coordinator: JullixDataUpdateCoordinator = data["coordinator"]
    install_ids: list[str] = data["install_ids"]
    options = entry.options or {}
    enable_cost = options.get(OPTION_ENABLE_COST, False)
    enable_statistics = options.get(OPTION_ENABLE_STATISTICS, False)
    enable_insights = options.get(OPTION_ENABLE_INSIGHTS, True)
    enable_charger_session = options.get(OPTION_ENABLE_CHARGER_SESSION, True)
    enable_session_history = options.get(OPTION_ENABLE_SESSION_HISTORY, False)
    session_hist = data.get("session_history")
    entity_discovery = data.get("entity_discovery")
    local_host = data.get("local_host")

    entities: list[JullixSensor] = []
    for install_id in install_ids:
        snap = get_installation_snapshot(coordinator, install_id)
        install_name = snap.installation_display_name(install_id)

        entities.extend(create_diagnostic_entities(coordinator, install_id, install_name))

        if enable_insights:
            entities.extend(
                create_insight_entities(
                    coordinator,
                    install_id,
                    install_name,
                    enable_statistics_roll=enable_statistics,
                )
            )

        entities.extend(create_summary_power_entities(coordinator, install_id, install_name))
        entities.extend(
            create_battery_entities(
                coordinator, install_id, install_name, local_host=local_host
            )
        )
        entities.extend(create_solar_home_entities(coordinator, install_id, install_name))
        entities.extend(create_grid_entities(coordinator, install_id, install_name))
        entities.extend(create_metering_entities(coordinator, install_id, install_name))
        entities.extend(create_charger_entities(coordinator, install_id, install_name))
        entities.extend(
            create_charger_extended_entities(coordinator, install_id, install_name)
        )
        entities.extend(create_plug_entities(coordinator, install_id, install_name))

        if pe := maybe_plug_energy_today_entity(coordinator, install_id, install_name):
            entities.append(pe)

        if enable_cost:
            entities.extend(create_cost_entities(coordinator, install_id, install_name))
            entities.extend(
                create_automation_helper_entities(coordinator, install_id, install_name)
            )

        if enable_charger_session:
            entities.extend(
                create_charger_intel_entities(coordinator, install_id, install_name)
            )

        if enable_session_history:
            entities.extend(
                create_session_history_entities(
                    coordinator, install_id, install_name, session_hist
                )
            )

        if wa := maybe_weather_alarm_entity(coordinator, install_id, install_name):
            entities.append(wa)

        if enable_statistics:
            entities.extend(create_statistics_entities(coordinator, install_id, install_name))

        if te := maybe_tariff_entity(coordinator, install_id, install_name):
            entities.append(te)

        if ae := maybe_algorithm_entity(coordinator, install_id, install_name):
            entities.append(ae)

        entities.extend(
            create_algorithm_extended_entities(coordinator, install_id, install_name)
        )

        if wf := maybe_weather_forecast_entity(coordinator, install_id, install_name):
            entities.append(wf)

        if local_host:
            entities.extend(
                create_local_ems_entities(coordinator, install_id, install_name)
            )

    if entity_discovery:
        entity_discovery.register_platform(
            "sensor",
            lambda iid, snap: create_discovered_sensor_entities(
                coordinator, iid, snap
            ),
            async_add_entities,
        )

    async_add_entities(entities)
