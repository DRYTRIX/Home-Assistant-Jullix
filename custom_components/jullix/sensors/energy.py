"""Summary power, solar/home detail, metering, plugs, statistics, weather, tariff."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower

from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import (
    device_info_home_consumption,
    device_info_plug,
    device_info_power_overview,
    device_info_solar,
    device_info_system,
)
from ..models.util import extract_plug_energy_total_kwh, extract_statistics_total_kwh, safe_float
from .base import JullixSensor, get_installation_snapshot

_SUMMARY_LINES: dict[str, tuple[str, str]] = {
    "grid": ("Grid import", "summary_grid_import"),
    "solar": ("Solar production", "summary_solar_production"),
    "home": ("Home consumption", "summary_home_consumption"),
    "battery": ("Battery power", "summary_battery_power"),
}


def _metering_channel_is_energy(channel: dict[str, Any]) -> bool:
    """Infer whether a metering channel is cumulative energy (kWh) vs power (W)."""
    unit = str(channel.get("unit", "")).lower().replace(" ", "")
    if "kwh" in unit or "mwh" in unit:
        return True
    if unit.endswith("wh") and "kw" not in unit:
        return True
    power_v = channel.get("power")
    energy_v = channel.get("energy")
    if energy_v is not None and power_v is None:
        return True
    if "kw" in unit and "h" not in unit:
        return False
    if unit in ("w", "watt", "watts", "kw"):
        return False
    return False


def create_summary_power_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    """Summary line powers (grid/solar/home/battery from summary endpoint)."""
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    power_dev = device_info_power_overview(install_id, install_name)
    for key in ("grid", "solar", "home", "battery"):
        label, tkey = _SUMMARY_LINES[key]
        val = snap.power_summary.power_watts(key)
        if val is not None or key in ("grid", "solar", "home", "battery"):
            entities.append(
                JullixSummaryLinePowerSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    key=key,
                    unique_id=f"{install_id}_summary_{key}",
                    name=label,
                    device_info=power_dev,
                    translation_key=tkey,
                )
            )
    return entities


def create_solar_home_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    if snap.solar_detail.power_watts() is not None:
        entities.append(
            JullixSolarHomePowerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                source="solar",
                unique_id=f"{install_id}_solar_power",
                name="Solar power",
                device_info=device_info_solar(install_id, install_name),
                translation_key="detail_solar_power",
            )
        )
    if snap.home_detail.power_watts() is not None:
        entities.append(
            JullixSolarHomePowerSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                source="home",
                unique_id=f"{install_id}_home_power",
                name="Consumption power",
                device_info=device_info_home_consumption(install_id, install_name),
                translation_key="detail_home_power",
            )
        )
    return entities


def create_metering_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    sys_dev = device_info_system(install_id, install_name)
    for i, ch in enumerate(snap.metering.channels):
        ch_id = ch.get("id", ch.get("channel_id", str(i)))
        val = ch.get("value", ch.get("power", ch.get("energy")))
        if safe_float(val) is not None:
            entities.append(
                JullixMeteringSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    channel_index=i,
                    unique_id=f"{install_id}_metering_{ch_id}",
                    name=f"Meter {ch_id}",
                    device_info=sys_dev,
                    is_energy_channel=_metering_channel_is_energy(ch),
                )
            )
    return entities


def create_plug_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    for plug in snap.plugs:
        model = plug.raw.get("model") or plug.raw.get("type")
        if model is not None:
            model = str(model)
        plug_dev = device_info_plug(
            install_id,
            install_name,
            plug.mac,
            plug.display_name,
            model=model,
        )
        entities.append(
            JullixPlugSensor(
                coordinator=coordinator,
                install_id=install_id,
                install_name=install_name,
                plug_index=plug.index,
                plug_mac=plug.mac,
                unique_id=f"{install_id}_plug_{plug.mac}",
                name="Power",
                device_info=plug_dev,
                translation_key="plug_power",
            )
        )
    return entities


def maybe_plug_energy_today_entity(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> JullixSensor | None:
    snap = get_installation_snapshot(coordinator, install_id)
    if not snap.plugs and snap.plug_energy_today_raw is None:
        return None
    return JullixPlugEnergyTodaySensor(
        coordinator=coordinator,
        install_id=install_id,
        install_name=install_name,
        unique_id=f"{install_id}_plug_energy_today",
        name="Plug energy today",
        device_info=device_info_system(install_id, install_name),
        translation_key="plug_energy_today",
    )


def create_statistics_entities(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> list[JullixSensor]:
    snap = get_installation_snapshot(coordinator, install_id)
    entities: list[JullixSensor] = []
    sys_dev = device_info_system(install_id, install_name)
    stat_specs = (
        ("statistics_energy_daily", "Energy daily", "statistics_energy_daily"),
        ("statistics_energy_monthly", "Energy monthly", "statistics_energy_monthly"),
        ("statistics_energy_yearly", "Energy yearly", "statistics_energy_yearly"),
    )
    for key, label, tkey in stat_specs:
        raw = getattr(snap, key, None)
        if raw is not None:
            entities.append(
                JullixStatisticsSensor(
                    coordinator=coordinator,
                    install_id=install_id,
                    install_name=install_name,
                    data_key=key,
                    unique_id=f"{install_id}_{key}",
                    name=label,
                    device_info=sys_dev,
                    translation_key=tkey,
                )
            )
    return entities


def maybe_weather_alarm_entity(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> JullixSensor | None:
    snap = get_installation_snapshot(coordinator, install_id)
    if snap.weather_alarm is None:
        return None
    sys_dev = device_info_system(install_id, install_name)
    return JullixWeatherAlarmSensor(
        coordinator=coordinator,
        install_id=install_id,
        install_name=install_name,
        unique_id=f"{install_id}_weather_alarm",
        name="Weather alarm",
        device_info=sys_dev,
        translation_key="weather_alarm",
    )


def maybe_tariff_entity(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> JullixSensor | None:
    snap = get_installation_snapshot(coordinator, install_id)
    if snap.tariff is None:
        return None
    sys_dev = device_info_system(install_id, install_name)
    return JullixTariffSensor(
        coordinator=coordinator,
        install_id=install_id,
        install_name=install_name,
        unique_id=f"{install_id}_tariff",
        name="Tariff",
        device_info=sys_dev,
        translation_key="tariff",
    )


def maybe_algorithm_entity(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> JullixSensor | None:
    snap = get_installation_snapshot(coordinator, install_id)
    if snap.algorithm_overview is None:
        return None
    sys_dev = device_info_system(install_id, install_name)
    return JullixAlgorithmOverviewSensor(
        coordinator=coordinator,
        install_id=install_id,
        install_name=install_name,
        unique_id=f"{install_id}_algorithm_overview",
        name="Optimization",
        device_info=sys_dev,
        translation_key="optimization",
    )


def maybe_weather_forecast_entity(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
    install_name: str,
) -> JullixSensor | None:
    snap = get_installation_snapshot(coordinator, install_id)
    if snap.weather_forecast is None:
        return None
    sys_dev = device_info_system(install_id, install_name)
    return JullixWeatherForecastSensor(
        coordinator=coordinator,
        install_id=install_id,
        install_name=install_name,
        unique_id=f"{install_id}_weather_forecast",
        name="Weather",
        device_info=sys_dev,
        translation_key="weather_forecast",
    )


class JullixSummaryLinePowerSensor(JullixSensor):
    """One summary powers.* line (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

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
        super().__init__(
            coordinator,
            install_id,
            install_name,
            unique_id,
            name,
            **kwargs,
        )
        self._key = key

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        self._attr_native_value = snap.power_summary.power_watts(self._key)


class JullixSolarHomePowerSensor(JullixSensor):
    """Solar or home detail power (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        source: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator,
            install_id,
            install_name,
            unique_id,
            name,
            **kwargs,
        )
        self._source = source

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        if self._source == "solar":
            self._attr_native_value = snap.solar_detail.power_watts()
        else:
            self._attr_native_value = snap.home_detail.power_watts()


class JullixMeteringSensor(JullixSensor):
    """Metering channel."""

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        channel_index: int,
        unique_id: str,
        name: str,
        *,
        is_energy_channel: bool,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator,
            install_id,
            install_name,
            unique_id,
            name,
            **kwargs,
        )
        self._channel_index = channel_index
        if is_energy_channel:
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_suggested_display_precision = 2
        else:
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 2

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        self._attr_native_value = snap.metering.channel_value(self._channel_index)


class JullixPlugSensor(JullixSensor):
    """Smart plug power (W)."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

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
        super().__init__(
            coordinator,
            install_id,
            install_name,
            unique_id,
            name,
            **kwargs,
        )
        self._plug_index = plug_index
        self._plug_mac = plug_mac

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        self._attr_native_value = snap.plug_power_watts(self._plug_index)


class JullixPlugEnergyTodaySensor(JullixSensor):
    """Installation plug energy today (kWh)."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        kwh = snap.plug_energy_today_kwh
        if kwh is None:
            kwh = extract_plug_energy_total_kwh(snap.plug_energy_today_raw)
        self._attr_native_value = kwh


class JullixTariffSensor(JullixSensor):
    """Active tariff name."""

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        tariff = snap.tariff
        if isinstance(tariff, dict):
            self._attr_native_value = tariff.get(
                "name", tariff.get("tariff_name", str(tariff))
            )
        elif tariff is not None:
            self._attr_native_value = str(tariff)
        else:
            self._attr_native_value = None


class JullixAlgorithmOverviewSensor(JullixSensor):
    """Optimization overview state."""

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        overview = snap.algorithm_overview
        if isinstance(overview, dict):
            self._attr_native_value = overview.get(
                "status", overview.get("state", str(overview))
            )
        elif overview is not None:
            self._attr_native_value = str(overview)
        else:
            self._attr_native_value = None


class JullixWeatherForecastSensor(JullixSensor):
    """Weather forecast summary."""

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        weather = snap.weather_forecast
        if isinstance(weather, dict):
            self._attr_native_value = weather.get(
                "condition",
                weather.get("description", weather.get("summary", str(weather))),
            )
        elif weather is not None:
            self._attr_native_value = str(weather)
        else:
            self._attr_native_value = None


class JullixWeatherAlarmSensor(JullixSensor):
    """Weather alarm on/off + attributes."""

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        alarm = snap.weather_alarm
        if isinstance(alarm, list) and len(alarm) > 0:
            self._attr_native_value = "on"
            self._attr_extra_state_attributes = {"alerts": alarm}
        elif isinstance(alarm, dict) and alarm:
            self._attr_native_value = "on"
            self._attr_extra_state_attributes = alarm
        elif alarm:
            self._attr_native_value = str(alarm)
            self._attr_extra_state_attributes = {}
        else:
            self._attr_native_value = "off"
            self._attr_extra_state_attributes = {}


class JullixStatisticsSensor(JullixSensor):
    """Energy statistics aggregates."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        data_key: str,
        unique_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            coordinator,
            install_id,
            install_name,
            unique_id,
            name,
            **kwargs,
        )
        self._data_key = data_key

    def _update_from_snapshot(self) -> None:
        snap = get_installation_snapshot(self.coordinator, self._install_id)
        raw = getattr(snap, self._data_key, None)
        self._attr_native_value = extract_statistics_total_kwh(raw)
