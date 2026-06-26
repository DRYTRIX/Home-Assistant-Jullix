# Jullix integration architecture

This document describes how the custom component is structured and how data moves from the Jullix Platform API into Home Assistant entities.

## Overview

The integration is **cloud-first** (`iot_class: cloud_polling` in `manifest.json`). It uses a single **DataUpdateCoordinator** per config entry to poll the Platform API and optionally merge readings from a **Jullix-Direct** device on the LAN. Parsed state lives in **domain models** (`JullixInstallationSnapshot`); platforms (sensors, switches, and so on) read only from the coordinator.

## API layer

**Module:** [`custom_components/jullix/api.py`](../custom_components/jullix/api.py)

- **`JullixApiClient`** wraps HTTPS calls to `https://mijn.jullix.be` using the user’s JWT (`Authorization: Bearer …`).
- **Exceptions:** `JullixApiError` (general failures) and `JullixAuthError` (invalid or expired token). The config flow and coordinator use these for reauth and error reporting.
- **Retries:** Transient server errors (5xx) and rate limiting (429) are retried with backoff (`_MAX_ATTEMPTS`, `_BACKOFF_BASE_S`).
- **Endpoints** are centralized as `API_PATH_*` constants in [`const.py`](../custom_components/jullix/const.py).

## Coordinator

**Module:** [`custom_components/jullix/coordinator.py`](../custom_components/jullix/coordinator.py)

- **`JullixDataUpdateCoordinator`** subclasses Home Assistant’s `DataUpdateCoordinator`. Its data type is `dict[str, JullixInstallationSnapshot]` (one snapshot per configured installation ID).
- **Concurrency:** Fetches are limited with an asyncio semaphore (`_FETCH_CONCURRENCY = 4`) to avoid hammering the API.
- **Extended polling:** Not every API group runs on every refresh. “Extended” groups (cost, statistics, tariff, weather, algorithm, charger session, and related) run when [`run_extended_this_refresh`](../custom_components/jullix/features.py) is true—by default every 3rd refresh (`EXTENDED_POLL_INTERVAL`). See [Feature tiers](features.md). This group also fetches installation metadata (used for the device display name), the extended algorithm endpoints (settings, results, usage, PV predict), and per-charger status/events/energies (keyed by MAC in `charger_status_by_mac`, `charger_events_by_mac`, `charger_energies_by_mac`).
- **Adaptive polling:** When enabled, the coordinator can shorten the update interval while chargers are active or grid/battery power is high (`ADAPTIVE_FAST_POLL_SECONDS`, thresholds in `const.py`).
- **Jullix-Direct:** If a local host was configured and **Merge local Jullix-Direct data** is on, the coordinator instantiates **`JullixLocalClient`** and merges local EMS data with cloud snapshots (`merge_local_snapshot`). Parsed local fields live in **`LocalEmsSnapshot`** ([`models/local_ems.py`](../custom_components/jullix/models/local_ems.py)); sensors and binary sensors in [`sensors/local_ems.py`](../custom_components/jullix/sensors/local_ems.py) and [`binary_sensor.py`](../custom_components/jullix/binary_sensor.py) read from that snapshot and stay unavailable until merge succeeds.
- **Battery cumulative energy:** Per-battery **Energy charged** and **Energy discharged** sensors (`state_class: total_increasing`) read from [`models/battery.py`](../custom_components/jullix/models/battery.py). Live values come from battery detail or local EMS `/api/ems/battery`; when cloud detail omits totals, the coordinator fetches today's **`battery_energy_history`** (CORE tier) and backfills from [`API_PATH_HISTORY_BATTERY_ENERGY`](../custom_components/jullix/const.py). Entities are created in [`sensors/battery.py`](../custom_components/jullix/sensors/battery.py).
- **Events:** After a successful update, [`events.detect_and_fire_events`](../custom_components/jullix/events.py) compares successive snapshots and may fire **`jullix_event`** on meaningful transitions (charger start/stop, battery thresholds, grid heuristics).
- **Auth callback:** Optional `on_auth_error` can trigger reauthentication flow when the API returns auth failures.

## Models

**Package:** [`custom_components/jullix/models/`](../custom_components/jullix/models/)

| Module | Role |
|--------|------|
| `installation.py` | **`JullixInstallationSnapshot`**: normalized per-installation state entities consume. **`RawInstallFetches`**: raw JSON fragments before parsing. **`build_installation_snapshot`**, **`merge_local_snapshot`**. |
| `summary.py` | Power summary, grid/solar/home detail snapshots (`PowerSummarySnapshot`, `GridDetailSnapshot`, `SolarHomeSnapshot`). |
| `battery.py` | **`BatterySlot`** and battery detail parsing. |
| `local_ems.py` | **`LocalEmsSnapshot`**: grid meter, water, and local charger fields from Jullix-Direct `/api/ems/*`. |
| `charger.py` | **`ChargerDevice`**, charger list and control payload parsing. |
| `plug.py` | **`PlugDevice`**, plug list and plug energy parsing. |
| `costs.py` | Cost/savings and monthly total snapshots. |
| `util.py` | Shared parsing helpers. |

Entities should treat **`JullixInstallationSnapshot`** as the only structured source of truth for installation state.

## Entities (platforms)

**Entry point:** [`custom_components/jullix/__init__.py`](../custom_components/jullix/__init__.py) registers:

- `BINARY_SENSOR` — peak tariff when cost helpers are enabled; local EMS occupancy/fault flags when a gateway host is configured
- `BUTTON` — **Run hourly optimization** per installation (calls `jullix.run_algorithm_hourly`)
- `SENSOR` — bulk of the integration, including [`sensors/local_ems.py`](../custom_components/jullix/sensors/local_ems.py) when a local host is set
- `SWITCH`, `NUMBER`, `SELECT` — chargers and plugs when control options are enabled; **Tariff** select when cost sensors are on

**Sensors** are split by domain under [`custom_components/jullix/sensors/`](../custom_components/jullix/sensors/); [`sensors/setup.py`](../custom_components/jullix/sensors/setup.py) aggregates `create_*_entities` factories based on config entry options (cost, statistics, insights, charger session, etc.). [`sensors/algorithm_extended.py`](../custom_components/jullix/sensors/algorithm_extended.py) and [`sensors/charger_extended.py`](../custom_components/jullix/sensors/charger_extended.py) are unconditional (not option-gated): each entity is only created when the corresponding extended-poll data is actually present on the snapshot.

**Derived tariff logic** (cheap window, peak hour, `is_peak_now`) lives under [`derived/`](../custom_components/jullix/derived/) and feeds tariff-related sensors and the peak binary sensor.

**Services** are registered in `__init__.py` with voluptuous schemas; descriptions for the UI come from [`services.yaml`](../custom_components/jullix/services.yaml) and [`strings.json`](../custom_components/jullix/strings.json). This includes `jullix.force_algorithm_command` for sending optimizer force commands.

## Data flow

```mermaid
flowchart LR
  subgraph sources [Data sources]
    CloudAPI[mijn_jullix_API]
    LocalOpt[Jullix_Direct_optional]
  end
  Coordinator[JullixDataUpdateCoordinator]
  Models[build_installation_snapshot]
  Entities[HA_platforms]
  CloudAPI --> Coordinator
  LocalOpt --> Coordinator
  Coordinator --> Models
  Models --> Entities
```

1. The coordinator requests cloud endpoints (and optionally local endpoints), filling **`RawInstallFetches`**.
2. **`build_installation_snapshot`** (and **`merge_local_snapshot`** if applicable) produce **`JullixInstallationSnapshot`** per installation.
3. Platforms update entities from the coordinator’s `data` on each successful refresh.

## Related reading

- [Feature tiers and polling](features.md)
- [Entities reference](entities.md)
- [Platform API mapping](api.md)
- [Troubleshooting](troubleshooting.md)
- [Development guide](development.md)
