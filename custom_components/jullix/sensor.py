"""Jullix sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPTION_ENABLE_COST
from .coordinator import JullixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    """Safely convert value to float."""
    if value is None:
        return default
    if isinstance(value, dict):
        # Handle nested: {"power": 100} or {"import": 50, "export": -30}
        if "power" in value:
            return _safe_float(value["power"], default)
        if "import" in value or "export" in value:
            imp = _safe_float(value.get("import"), 0) or 0
            exp = _safe_float(value.get("export"), 0) or 0
            return imp - exp
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Safely convert value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_power(value: Any) -> float | None:
    """Extract power (W) from API value - handles flat number or nested dict."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        if "power" in value:
            return _safe_float(value["power"])
        if "value" in value:
            return _safe_float(value["value"])
        # Grid may have import/export
        imp = _safe_float(value.get("import"))
        exp = _safe_float(value.get("export"))
        if imp is not None or exp is not None:
            return (imp or 0) - (exp or 0)
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Jullix sensors from a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return

    coordinator: JullixDataUpdateCoordinator = data["coordinator"]
    install_ids: list[str] = data["install_ids"]
    options = entry.options or {}
    enable_cost = options.get(OPTION_ENABLE_COST, False)

    entities: list[JullixSensor] = []
    for install_id in install_ids:
        install_data = coordinator.data.get(install_id) or {}
        install_name = _get_installation_name(install_data, install_id)

        # Power summary sensors
        summary = install_data.get("summary") or {}
        entities.extend(
            _create_summary_sensors(coordinator, install_id, install_name, summary)
        )

        # Battery sensors
        battery = install_data.get("battery") or {}
        entities.extend(
            _create_battery_sensors(coordinator, install_id, install_name, battery)
        )

        # Solar sensors
        solar = install_data.get("solar") or {}
        entities.extend(
            _create_solar_sensors(coordinator, install_id, install_name, solar)
        )

        # Grid sensors
        grid = install_data.get("grid") or {}
        entities.extend(_create_grid_sensors(coordinator, install_id, install_name, grid))

        # Home consumption sensors
        home = install_data.get("home") or {}
        entities.extend(
            _create_home_sensors(coordinator, install_id, install_name, home)
        )

        # Metering sensors
        metering = install_data.get("metering") or {}
        entities.extend(
            _create_metering_sensors(coordinator, install_id, install_name, metering)
        )

        # Charger sensors
        chargers = install_data.get("chargers") or []
        entities.extend(
            _create_charger_sensors(coordinator, install_id, install_name, chargers)
        )

        # Plug sensors
        plugs = install_data.get("plugs") or []
        entities.extend(
            _create_plug_sensors(coordinator, install_id, install_name, plugs)
        )

        # Cost sensors (when enabled in options)
        if enable_cost:
            cost = install_data.get("cost") or {}
            entities.extend(
                _create_cost_sensors(coordinator, install_id, install_name, cost)
            )

    async_add_entities(entities)


def _get_installation_name(install_data: dict[str, Any], install_id: str) -> str:
    """Get installation display name from data or fallback to ID."""
    # Installation name might come from a parent fetch; for now use install_id
    return f"Installation {install_id[:8]}"


def _create_summary_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    summary: dict[str, Any],
) -> list[JullixSensor]:
    """Create sensors from power summary data."""
    sensors: list[JullixSensor] = []
    # Summary can have various structures; common keys: grid, solar, home, battery, captar
    for key, label in (
        ("grid", "Grid power"),
        ("solar", "Solar power"),
        ("home", "Home consumption"),
        ("battery", "Battery power"),
        ("captar", "Capacity tariff"),
    ):
        val = _safe_float(summary.get(key))
        if val is not None or key in ("grid", "solar", "home", "battery"):
            sensors.append(
                JullixPowerSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    key=key,
                    unique_id=f"{install_id}_summary_{key}",
                    name=f"{install_name} {label}",
                )
            )
    return sensors


def _create_battery_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    battery: dict[str, Any],
) -> list[JullixSensor]:
    """Create battery-related sensors."""
    sensors: list[JullixSensor] = []
    # Handle array of batteries or single object
    batteries = battery if isinstance(battery, list) else [battery] if battery else []
    for i, bat in enumerate(batteries):
        if not isinstance(bat, dict):
            continue
        prefix = f"Battery {i + 1}" if len(batteries) > 1 else "Battery"
        bat_name = bat.get("name") or bat.get("localid") or prefix
        if (soc := _safe_float(bat.get("soc"))) is not None:
            sensors.append(
                JullixBatterySocSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    battery_key=i,
                    unique_id=f"{install_id}_battery_{i}_soc",
                    name=f"{install_name} {bat_name} SoC",
                )
            )
        if "power" in bat or _safe_float(bat.get("power")) is not None:
            sensors.append(
                JullixPowerSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    key="battery_power",
                    unique_id=f"{install_id}_battery_{i}_power",
                    name=f"{install_name} {bat_name} power",
                    extra_path=(i, "power"),
                )
            )
    # Single battery object (non-array)
    if not batteries and battery:
        soc = _safe_float(battery.get("soc"))
        if soc is not None:
            sensors.append(
                JullixBatterySocSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    battery_key=0,
                    unique_id=f"{install_id}_battery_0_soc",
                    name=f"{install_name} Battery SoC",
                )
            )
    return sensors


def _create_solar_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    solar: dict[str, Any],
) -> list[JullixSensor]:
    """Create solar-related sensors."""
    sensors: list[JullixSensor] = []
    power = _safe_float(solar.get("power"))
    if power is not None:
        sensors.append(
            JullixPowerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                key="solar",
                unique_id=f"{install_id}_solar_power",
                name=f"{install_name} Solar power",
                extra_path=None,
                data_source="solar",
            )
        )
    return sensors


def _create_grid_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    grid: dict[str, Any],
) -> list[JullixSensor]:
    """Create grid-related sensors."""
    sensors: list[JullixSensor] = []
    power = _safe_float(grid.get("power"))
    if power is not None:
        sensors.append(
            JullixPowerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                key="grid",
                unique_id=f"{install_id}_grid_power",
                name=f"{install_name} Grid power",
                extra_path=None,
                data_source="grid",
            )
        )
    return sensors


def _create_home_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    home: dict[str, Any],
) -> list[JullixSensor]:
    """Create home consumption sensors."""
    sensors: list[JullixSensor] = []
    power = _safe_float(home.get("power"))
    if power is not None:
        sensors.append(
            JullixPowerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                key="home",
                unique_id=f"{install_id}_home_power",
                name=f"{install_name} Home consumption",
                extra_path=None,
                data_source="home",
            )
        )
    return sensors


def _create_metering_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    metering: dict[str, Any],
) -> list[JullixSensor]:
    """Create metering sensors (electricity, gas, etc.)."""
    sensors: list[JullixSensor] = []
    # Metering can be dict of channels or list of channel objects
    channels = metering.get("channels", metering) if isinstance(metering, dict) else []
    if isinstance(channels, dict):
        channels = [{"id": k, "value": v} for k, v in channels.items()]
    if not isinstance(channels, list):
        channels = [metering] if metering else []
    for i, ch in enumerate(channels):
        if not isinstance(ch, dict):
            continue
        ch_id = ch.get("id", ch.get("channel_id", str(i)))
        val = ch.get("value", ch.get("power", ch.get("energy")))
        if _safe_float(val) is not None:
            sensors.append(
                JullixMeteringSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    channel_key=i,
                    unique_id=f"{install_id}_metering_{ch_id}",
                    name=f"{install_name} Meter {ch_id}",
                )
            )
    return sensors


def _create_charger_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    chargers: list[dict[str, Any]],
) -> list[JullixSensor]:
    """Create charger status and power sensors."""
    sensors: list[JullixSensor] = []
    for i, ch in enumerate(chargers):
        if not isinstance(ch, dict):
            continue
        mac = ch.get("mac", ch.get("mac_address", str(i)))
        name = ch.get("name", ch.get("label", f"Charger {i + 1}"))
        sensors.append(
            JullixChargerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                charger_index=i,
                charger_mac=mac,
                unique_id=f"{install_id}_charger_{mac}",
                name=f"{install_name} {name}",
            )
        )
    return sensors


def _create_plug_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    plugs: list[dict[str, Any]],
) -> list[JullixSensor]:
    """Create plug power sensors."""
    sensors: list[JullixSensor] = []
    for i, plug in enumerate(plugs):
        if not isinstance(plug, dict):
            continue
        mac = plug.get("mac", plug.get("mac_address", str(i)))
        name = plug.get("name", plug.get("label", f"Plug {i + 1}"))
        sensors.append(
            JullixPlugSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                plug_index=i,
                plug_mac=mac,
                unique_id=f"{install_id}_plug_{mac}",
                name=f"{install_name} {name}",
            )
        )
    return sensors


def _create_cost_sensors(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
    cost: dict[str, Any],
) -> list[JullixSensor]:
    """Create cost/savings sensors."""
    sensors: list[JullixSensor] = []
    for key, label in (
        ("savings", "Savings"),
        ("total", "Total cost"),
        ("total_cost", "Total cost"),
    ):
        val = cost.get(key)
        if _safe_float(val) is not None or (isinstance(val, dict) and "value" in val):
            sensors.append(
                JullixCostSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    key=key,
                    unique_id=f"{install_id}_cost_{key}",
                    name=f"{install_name} {label}",
                )
            )
    return sensors


class JullixSensor(CoordinatorEntity[JullixDataUpdateCoordinator], SensorEntity):
    """Base class for Jullix sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._install_id = install_id
        self._install_name = install_name
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, install_id)},
            "name": f"Jullix {install_name}",
            "manufacturer": "Innovoltus",
            "model": "Jullix EMS",
        }


class JullixPowerSensor(JullixSensor):
    """Sensor for power values (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        key: str,
        unique_id: str,
        name: str,
        extra_path: tuple[int, str] | None = None,
        data_source: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the power sensor."""
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._key = key
        self._extra_path = extra_path
        self._data_source = data_source or "summary"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        if self._data_source == "summary":
            data = install_data.get("summary") or {}
            val = data.get(self._key)
        elif self._data_source in ("solar", "grid", "home"):
            data = install_data.get(self._data_source) or {}
            val = data.get("power")
        elif self._extra_path:
            batteries = install_data.get("battery") or []
            if isinstance(batteries, list) and len(batteries) > self._extra_path[0]:
                val = batteries[self._extra_path[0]].get(self._extra_path[1])
            else:
                val = None
        else:
            val = (install_data.get("summary") or {}).get(self._key)
        self._attr_native_value = _extract_power(val) if self._data_source == "summary" or self._key in ("grid", "solar", "home", "battery", "captar") else _safe_float(val)
        super()._handle_coordinator_update()


class JullixBatterySocSensor(JullixSensor):
    """Sensor for battery state of charge (%)."""

    _attr_native_unit_of_measurement = "%"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        battery_key: int,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the battery SoC sensor."""
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._battery_key = battery_key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        battery = install_data.get("battery")
        if isinstance(battery, list) and len(battery) > self._battery_key:
            val = battery[self._battery_key].get("soc")
        elif isinstance(battery, dict):
            val = battery.get("soc")
        else:
            val = None
        self._attr_native_value = _safe_float(val)
        super()._handle_coordinator_update()


class JullixCostSensor(JullixSensor):
    """Sensor for cost and savings values."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        key: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the cost sensor."""
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._key = key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        cost = install_data.get("cost") or {}
        val = cost.get(self._key)
        if isinstance(val, dict):
            val = val.get("value", val.get("amount"))
        self._attr_native_value = _safe_float(val)
        super()._handle_coordinator_update()


class JullixMeteringSensor(JullixSensor):
    """Sensor for metering values (energy, gas, etc.)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        channel_key: int,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the metering sensor."""
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._channel_key = channel_key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        metering = install_data.get("metering") or {}
        channels = metering.get("channels", metering) if isinstance(metering, dict) else []
        if isinstance(channels, dict):
            channels = [{"id": k, "value": v} for k, v in channels.items()]
        if not isinstance(channels, list):
            channels = [metering] if metering else []
        val = None
        if isinstance(channels, list) and len(channels) > self._channel_key:
            ch = channels[self._channel_key]
            if isinstance(ch, dict):
                val = ch.get("value", ch.get("power", ch.get("energy")))
        self._attr_native_value = _safe_float(val)
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        super()._handle_coordinator_update()


class JullixChargerSensor(JullixSensor):
    """Sensor for charger power/status."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        charger_index: int,
        charger_mac: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the charger sensor."""
        super().__init__(
            coordinator=coordinator,
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
        install_data = self.coordinator.data.get(self._install_id) or {}
        chargers = install_data.get("chargers") or []
        charger_detail = install_data.get("charger") or []
        val = None
        if isinstance(chargers, list) and len(chargers) > self._charger_index:
            ch = chargers[self._charger_index]
            if isinstance(ch, dict):
                val = ch.get("power", ch.get("current_power"))
        if val is None and isinstance(charger_detail, list) and len(charger_detail) > self._charger_index:
            ch = charger_detail[self._charger_index]
            if isinstance(ch, dict):
                val = ch.get("power", ch.get("current_power"))
        self._attr_native_value = _safe_float(val)
        super()._handle_coordinator_update()


class JullixPlugSensor(JullixSensor):
    """Sensor for smart plug power."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        plug_index: int,
        plug_mac: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the plug sensor."""
        super().__init__(
            coordinator=coordinator,
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
        install_data = self.coordinator.data.get(self._install_id) or {}
        plugs = install_data.get("plugs") or []
        plug_detail = install_data.get("plug") or []
        val = None
        if isinstance(plugs, list) and len(plugs) > self._plug_index:
            p = plugs[self._plug_index]
            if isinstance(p, dict):
                val = p.get("power", p.get("current_power"))
        if val is None and isinstance(plug_detail, list) and len(plug_detail) > self._plug_index:
            p = plug_detail[self._plug_index]
            if isinstance(p, dict):
                val = p.get("power", p.get("current_power"))
        self._attr_native_value = _safe_float(val)
        super()._handle_coordinator_update()


class JullixCostSensor(JullixSensor):
    """Sensor for cost and savings values."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        key: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the cost sensor."""
        super().__init__(
            coordinator=coordinator,
            install_id=install_id,
            install_name=install_name,
            unique_id=unique_id,
            name=name,
            **kwargs,
        )
        self._key = key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        install_data = self.coordinator.data.get(self._install_id) or {}
        cost = install_data.get("cost") or {}
        val = cost.get(self._key)
        if isinstance(val, dict):
            val = val.get("value", val.get("amount"))
        self._attr_native_value = _safe_float(val)
        super()._handle_coordinator_update()
