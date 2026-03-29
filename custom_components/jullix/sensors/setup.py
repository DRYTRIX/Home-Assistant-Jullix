"""Sensor platform setup (aggregates entity factories)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import (
    OPTION_ENABLE_CHARGER_SESSION,
    OPTION_ENABLE_COST,
    OPTION_ENABLE_INSIGHTS,
    OPTION_ENABLE_STATISTICS,
)
from ..coordinator import JullixDataUpdateCoordinator
from .automation_helpers import create_automation_helper_entities
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
        entities.extend(create_battery_entities(coordinator, install_id, install_name))
        entities.extend(create_solar_home_entities(coordinator, install_id, install_name))
        entities.extend(create_grid_entities(coordinator, install_id, install_name))
        entities.extend(create_metering_entities(coordinator, install_id, install_name))
        entities.extend(create_charger_entities(coordinator, install_id, install_name))
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

        if wa := maybe_weather_alarm_entity(coordinator, install_id, install_name):
            entities.append(wa)

        if enable_statistics:
            entities.extend(create_statistics_entities(coordinator, install_id, install_name))

        if te := maybe_tariff_entity(coordinator, install_id, install_name):
            entities.append(te)

        if ae := maybe_algorithm_entity(coordinator, install_id, install_name):
            entities.append(ae)

        if wf := maybe_weather_forecast_entity(coordinator, install_id, install_name):
            entities.append(wf)

    async_add_entities(entities)
