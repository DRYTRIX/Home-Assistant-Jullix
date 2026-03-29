"""Data update coordinator for Jullix integration."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Coroutine
from dataclasses import replace
from datetime import date, timedelta
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import JullixApiClient, JullixAuthError
from .const import (
    ADAPTIVE_ACTIVE_BATTERY_ABS_W,
    ADAPTIVE_ACTIVE_GRID_ABS_W,
    ADAPTIVE_FAST_POLL_SECONDS,
    CHARGER_ACTIVE_POWER_W,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .events import detect_and_fire_events, edge_state_from_snapshot
from .features import run_extended_this_refresh
from .models import (
    JullixInstallationSnapshot,
    RawInstallFetches,
    build_installation_snapshot,
    merge_local_snapshot,
)
from .models.charger import parse_chargers_list
from .runtime_state import InstallEdgeState, InstallRuntimeMetrics

_LOGGER = logging.getLogger(__name__)

_DETAIL_TYPES = ("battery", "solar", "grid", "home", "plug", "charger", "metering")
_FETCH_CONCURRENCY = 4


class JullixDataUpdateCoordinator(DataUpdateCoordinator[dict[str, JullixInstallationSnapshot]]):
    """Coordinator that fetches Jullix data for all configured installations."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: JullixApiClient,
        install_ids: list[str],
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        local_host: str | None = None,
        use_local: bool = False,
        enable_cost: bool = False,
        enable_statistics: bool = False,
        enable_insights: bool = True,
        enable_events: bool = True,
        enable_adaptive_polling: bool = False,
        enable_charger_session: bool = True,
        session_history: Any = None,
        on_auth_error: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self._api_client = api_client
        self._install_ids = install_ids
        self._local_host = local_host
        self._use_local = use_local and local_host
        self._enable_cost = enable_cost
        self._enable_statistics = enable_statistics
        self._enable_insights = enable_insights
        self._enable_events = enable_events
        self._enable_adaptive_polling = enable_adaptive_polling
        self._enable_charger_session = enable_charger_session
        self._session_history = session_history
        self._on_auth_error = on_auth_error
        self._base_update_interval_seconds = int(update_interval)
        self.data: dict[str, JullixInstallationSnapshot] = {}
        self.last_installation_errors: dict[str, Exception] = {}
        self.install_metrics: dict[str, InstallRuntimeMetrics] = {}
        self._edge_state: dict[str, InstallEdgeState] = {}
        self._local_client = None
        self._sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
        self._refresh_seq = 0
        self._last_good: dict[str, JullixInstallationSnapshot] = {}
        if self._use_local and local_host:
            from .local_client import JullixLocalClient

            self._local_client = JullixLocalClient(local_host)

    async def _limited(self, coro: Coroutine[Any, Any, Any]) -> Any:
        async with self._sem:
            return await coro

    async def _async_update_data(self) -> dict[str, JullixInstallationSnapshot]:
        """Fetch data from the API for all installations."""
        self._refresh_seq += 1
        extended = run_extended_this_refresh(self._refresh_seq)
        _LOGGER.debug(
            "Coordinator refresh seq=%s extended_groups=%s",
            self._refresh_seq,
            extended,
        )

        result: dict[str, JullixInstallationSnapshot] = {}
        self.last_installation_errors.clear()

        for install_id in self._install_ids:
            t0 = time.perf_counter()
            fetch_err: Exception | None = None
            fresh_ok = False
            try:
                snap = await self._build_snapshot_for_install(install_id, extended)
                if self._local_client and self._install_ids and install_id == self._install_ids[0]:
                    try:
                        local_data = await self._local_client.get_ems_data()
                        if local_data:
                            snap = merge_local_snapshot(snap, local_data)
                    except Exception as exc:
                        _LOGGER.debug("Local Jullix-Direct merge failed: %s", exc)

                prev = self._last_good.get(install_id)
                if prev and not extended:
                    snap = self._preserve_extended_fields(snap, prev)

                result[install_id] = snap
                self._last_good[install_id] = snap
                fresh_ok = True
                dt_ms = (time.perf_counter() - t0) * 1000
                _LOGGER.debug(
                    "Installation %s snapshot ok in %.0f ms",
                    install_id,
                    dt_ms,
                )
                m = self.install_metrics.setdefault(install_id, InstallRuntimeMetrics())
                m.last_latency_ms = dt_ms
                m.last_success_at = dt_util.utcnow()
            except JullixAuthError as err:
                fetch_err = err
                self.last_installation_errors[install_id] = err
                if self._on_auth_error:
                    self.hass.async_create_task(self._on_auth_error())
                _LOGGER.warning("Auth error for installation %s: %s", install_id, err)
                if prev := self._last_good.get(install_id):
                    result[install_id] = prev
            except Exception as err:
                fetch_err = err
                self.last_installation_errors[install_id] = err
                _LOGGER.warning(
                    "Error fetching installation %s: %s",
                    install_id,
                    err,
                    exc_info=_LOGGER.isEnabledFor(logging.DEBUG),
                )
                if prev := self._last_good.get(install_id):
                    result[install_id] = prev

            if install_id in result:
                snap_final = result[install_id]
                prev_e = self._edge_state.get(install_id)
                err_e = fetch_err if not fresh_ok else None
                if self._enable_events:
                    self._edge_state[install_id] = detect_and_fire_events(
                        self.hass,
                        install_id,
                        snap_final,
                        prev_e,
                        err_e,
                    )
                elif err_e is None:
                    self._edge_state[install_id] = edge_state_from_snapshot(
                        snap_final, prev=prev_e
                    )

        if not result and self._install_ids:
            last_err = self.last_installation_errors.get(
                self._install_ids[0], Exception("No data")
            )
            _LOGGER.error(
                "All installations failed to update: %s",
                self.last_installation_errors,
            )
            raise UpdateFailed(f"Failed to update: {last_err}") from last_err

        if self._enable_adaptive_polling:
            self._apply_adaptive_update_interval(result)

        if self._session_history and self._enable_charger_session:
            from .derived.charger_session import parse_chargersession

            for iid, snap in result.items():
                ins = parse_chargersession(snap.chargersession_raw)
                if ins and ins.session_id:
                    self.hass.async_create_task(
                        self._session_history.maybe_append(
                            iid,
                            ins.session_id,
                            {
                                "energy_kwh": ins.energy_kwh,
                                "charger_mac": ins.charger_mac,
                                "state": ins.state,
                            },
                        )
                    )

        return result

    def _apply_adaptive_update_interval(
        self,
        result: dict[str, JullixInstallationSnapshot],
    ) -> None:
        """Shorten polling while chargers/grid/battery are active; otherwise use user interval."""
        base = max(MIN_SCAN_INTERVAL, self._base_update_interval_seconds)
        active = False
        for snap in result.values():
            for ch in snap.chargers:
                pw = snap.charger_power_watts(ch.index)
                if pw is not None and pw >= CHARGER_ACTIVE_POWER_W:
                    active = True
                    break
            gw = snap.power_summary.power_watts("grid")
            if gw is not None and abs(gw) >= ADAPTIVE_ACTIVE_GRID_ABS_W:
                active = True
            for slot in snap.battery_slots:
                bpw = slot.power_watts
                if bpw is not None and abs(bpw) >= ADAPTIVE_ACTIVE_BATTERY_ABS_W:
                    active = True
            if active:
                break
        fast = max(MIN_SCAN_INTERVAL, min(ADAPTIVE_FAST_POLL_SECONDS, base))
        seconds = fast if active else base
        new_delta = timedelta(seconds=seconds)
        if self.update_interval != new_delta:
            self.update_interval = new_delta
            _LOGGER.debug(
                "Adaptive polling: interval=%ss active=%s",
                seconds,
                active,
            )

    def _preserve_extended_fields(
        self,
        snap: JullixInstallationSnapshot,
        prev: JullixInstallationSnapshot,
    ) -> JullixInstallationSnapshot:
        """Reuse extended-tier fields from previous snapshot between extended polls."""
        return replace(
            snap,
            cost_savings=prev.cost_savings,
            cost_total=prev.cost_total,
            weather_alarm=prev.weather_alarm,
            statistics_energy_daily=prev.statistics_energy_daily,
            statistics_energy_monthly=prev.statistics_energy_monthly,
            statistics_energy_yearly=prev.statistics_energy_yearly,
            algorithm_overview=prev.algorithm_overview,
            tariff=prev.tariff,
            weather_forecast=prev.weather_forecast,
            cost_hourly_price=prev.cost_hourly_price,
            chargersession_raw=prev.chargersession_raw,
        )

    async def _build_snapshot_for_install(
        self,
        install_id: str,
        extended: bool,
    ) -> JullixInstallationSnapshot:
        raw = await self._fetch_raw_bundle(install_id, extended)
        return build_installation_snapshot(raw)

    async def _fetch_raw_bundle(
        self,
        install_id: str,
        extended: bool,
    ) -> RawInstallFetches:
        """Parallel core fetches; extended group when scheduled."""
        today = date.today()

        detail_coros = [
            self._limited(self._api_client.get_actual_detail(install_id, dt))
            for dt in _DETAIL_TYPES
        ]
        core_coros = [
            self._limited(self._api_client.get_power_summary(install_id)),
            *detail_coros,
            self._limited(self._api_client.get_chargers(install_id)),
            self._limited(self._api_client.get_plugs(install_id)),
            self._limited(
                self._api_client.get_history_plug_energy(
                    install_id, today.year, today.month, today.day
                )
            ),
        ]
        labels = ["power_summary", *_DETAIL_TYPES, "chargers", "plugs", "plug_energy"]

        core_results = await asyncio.gather(*core_coros, return_exceptions=True)
        fetch: dict[str, Any] = {}
        for label, res in zip(labels, core_results):
            if isinstance(res, Exception):
                _LOGGER.debug(
                    "Fetch %s failed for %s: %s",
                    label,
                    install_id,
                    res,
                )
                fetch[label] = None
            else:
                fetch[label] = res

        chargers_raw = fetch["chargers"]
        charger_control: dict[str, Any] = {}
        if chargers_raw is not None:
            devices = parse_chargers_list(chargers_raw)
            if devices:
                ctrl_tasks = [
                    self._limited(self._api_client.get_charger_control(d.mac))
                    for d in devices
                ]
                ctrl_results = await asyncio.gather(*ctrl_tasks, return_exceptions=True)
                for d, ctrl_res in zip(devices, ctrl_results):
                    if isinstance(ctrl_res, Exception):
                        _LOGGER.debug(
                            "Charger control failed mac=%s install=%s: %s",
                            d.mac,
                            install_id,
                            ctrl_res,
                        )
                    elif ctrl_res:
                        charger_control[d.mac] = ctrl_res

        cost_savings = None
        cost_total = None
        stats_d = stats_m = stats_y = None
        weather_alarm = weather_forecast = None
        algo = tariff = None
        cost_hourly = None
        chargersession_raw = None

        if extended:
            ext_coros: list[Any] = [
                self._limited(self._api_client.get_weather_alarm(install_id)),
                self._limited(self._api_client.get_weather_forecast(install_id)),
                self._limited(self._api_client.get_algorithm_overview(install_id)),
                self._limited(self._api_client.get_tariff(install_id)),
            ]
            ext_labels = ["weather_alarm", "weather_forecast", "algorithm", "tariff"]
            if self._enable_cost:
                ext_coros.extend(
                    [
                        self._limited(self._api_client.get_cost_savings(install_id)),
                        self._limited(
                            self._api_client.get_cost_total(
                                install_id, today.year, today.month
                            )
                        ),
                    ]
                )
                ext_labels.extend(["cost_savings", "cost_total"])
                ext_coros.append(
                    self._limited(
                        self._api_client.get_cost_hourly_price(
                            install_id, today.year, today.month, today.day
                        )
                    )
                )
                ext_labels.append("cost_hourly")
            if self._enable_charger_session:
                ext_coros.append(
                    self._limited(
                        self._api_client.get_chargersession_installation(install_id)
                    )
                )
                ext_labels.append("chargersession")
            if self._enable_statistics:
                ext_coros.extend(
                    [
                        self._limited(
                            self._api_client.get_statistics_energy_daily(install_id)
                        ),
                        self._limited(
                            self._api_client.get_statistics_energy_monthly(install_id)
                        ),
                        self._limited(
                            self._api_client.get_statistics_energy_yearly(install_id)
                        ),
                    ]
                )
                ext_labels.extend(["stats_d", "stats_m", "stats_y"])

            ext_results = await asyncio.gather(*ext_coros, return_exceptions=True)
            ext_map = dict(zip(ext_labels, ext_results))
            for key, res in ext_map.items():
                if isinstance(res, Exception):
                    _LOGGER.debug(
                        "Extended fetch %s failed for %s: %s",
                        key,
                        install_id,
                        res,
                    )
                    continue
                if key == "weather_alarm":
                    weather_alarm = res
                elif key == "weather_forecast":
                    weather_forecast = res
                elif key == "algorithm":
                    algo = res
                elif key == "tariff":
                    tariff = res
                elif key == "cost_savings":
                    cost_savings = res
                elif key == "cost_total":
                    cost_total = res
                elif key == "stats_d":
                    stats_d = res
                elif key == "stats_m":
                    stats_m = res
                elif key == "stats_y":
                    stats_y = res

        return RawInstallFetches(
            power_summary=fetch.get("power_summary"),
            detail_battery=fetch.get("battery"),
            detail_solar=fetch.get("solar"),
            detail_grid=fetch.get("grid"),
            detail_home=fetch.get("home"),
            detail_plug=fetch.get("plug"),
            detail_charger=fetch.get("charger"),
            detail_metering=fetch.get("metering"),
            chargers_response=chargers_raw,
            charger_control_by_mac=charger_control,
            plugs_response=fetch.get("plugs"),
            plug_energy_today=fetch.get("plug_energy"),
            cost_savings=cost_savings,
            cost_total=cost_total,
            weather_alarm=weather_alarm,
            statistics_energy_daily=stats_d,
            statistics_energy_monthly=stats_m,
            statistics_energy_yearly=stats_y,
            algorithm_overview=algo,
            tariff=tariff,
            weather_forecast=weather_forecast,
            cost_hourly_price=cost_hourly,
            chargersession_raw=chargersession_raw,
        )

    async def async_shutdown(self) -> None:
        """Release resources (e.g. local client session). Call on config entry unload."""
        if self._local_client:
            await self._local_client.close()
            self._local_client = None
