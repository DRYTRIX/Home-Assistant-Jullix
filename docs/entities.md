# Entities reference

Entity IDs include the Jullix **installation UUID**, for example `sensor.jullix_<uuid>_summary_solar`. Browse devices under **Settings → Devices & services → Jullix**, or filter **Developer tools → States** for `jullix`.

Display names come from [`strings.json`](../custom_components/jullix/strings.json) `translation_key` values unless noted.

## Summary and power

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Power summary | Grid import, solar production, home consumption, battery power (`summary_*`) | No |
| Grid detail | Grid power, capacity tariff (captar) | No |
| Solar / home detail | Detail solar power, detail home power | No |

## Battery

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Per battery | State of charge, power, voltage | No (when API or local EMS returns a battery slot) |
| Per battery energy | Energy charged, Energy discharged (`total_increasing` kWh) | No (when cumulative totals are available from detail, local EMS, or cloud history backfill) |

Battery **power** is instantaneous (W). **Energy charged** / **Energy discharged** are cumulative kWh for the [Energy Dashboard](troubleshooting.md#battery-energy-for-the-energy-dashboard).

## Metering

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Dynamic channels | `Meter {channel_id}` per metering channel from the API | No (created when the channel has a numeric value) |

Metering entities use **hardcoded names** (`Meter {id}`) rather than `translation_key`, because channel IDs come from Jullix at runtime. `unique_id` pattern: `{install_id}_metering_{channel_id}`.

## Chargers and plugs

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Charger power | Per-charger power | No |
| Charger control | Charging switch, max power number, mode select | **Charger controls** option |
| Charger extended | Status, energy today, events count | No option; created only when extended poll returns data |
| Plug power | Per-plug power | No |
| Plug energy today | Installation-level plug energy today | No |
| Plug control | Plug on/off switch | **Smart plug switches** option |

## Cost, statistics, and insights

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Cost / savings | Cost, savings, cost total this month | **Cost and savings sensors** |
| Automation helpers | Recommended charge time, cheap energy window, current hour price | **Cost and savings sensors** (with hourly price data) |
| Peak tariff | Binary sensor | **Cost and savings sensors** |
| Statistics | Daily / monthly / yearly energy statistics | **Energy statistics sensors** |
| Rolling statistic | Energy rolling 7 days (`statistics_energy_7d`) | **Energy statistics sensors** (entity lives in insights module but requires the statistics option) |
| Insights | Self-consumption, solar utilization, grid dependency (% estimates) | **Energy insight sensors** |

## Tariff, weather, algorithm

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Tariff / weather | Tariff, weather forecast, weather alarm | Tariff/weather fetches follow extended poll; entities created when data exists |
| Algorithm | Optimization overview | Extended poll |
| Algorithm extended | Settings, results, usage, solar prediction | No option; created when extended poll returns data |

## Charge session and diagnostics

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Session helpers | Session id, session energy, cost estimate, charging suggestion | **Charge session and suggestion sensors** |
| Diagnostics | Connection health, API latency, last successful update | No |

## Local EMS (Jullix-Direct)

Registered when a **local gateway host** was set during setup (`local_host` in the config entry). Values update when **Merge local Jullix-Direct data when configured** is enabled and the gateway is reachable. Entities are **unavailable** until local EMS data is merged.

| Category | Examples | Gated by option? |
|----------|----------|------------------|
| Grid meter detail | Grid power in/out, net power, energy import/export T1/T2, voltage L1/L2/L3 | Local host configured |
| Water | Water usage (m³) | Local host configured |
| Charger (local) | EV battery SOC, charger temperature, max current, charger state | Local host configured |
| Binary | EV charger occupied, EV three phase active, battery fault, solar fault | Local host configured |

These mirror the local-only entity set from community integrations that poll `/api/ems/*` directly. Cloud summary and detail sensors remain available independently.

## Platforms beyond sensors

| Platform | Examples | Gated by option? |
|----------|----------|------------------|
| Binary sensor | Peak tariff | **Cost and savings sensors** |
| Binary sensor (local) | EV occupied, three phase, battery/solar fault | Local gateway host configured |
| Button | Run hourly optimization | No (one per installation) |
| Select | Tariff | **Cost and savings sensors** |
| Switch / number / select | Charger and plug controls | Charger / plug control options |

## Related reading

- [README entities overview](../README.md#entities)
- [Configuration options](../README.md#options)
- [Troubleshooting — missing entities](troubleshooting.md#missing-entities)
- [Architecture](architecture.md)
