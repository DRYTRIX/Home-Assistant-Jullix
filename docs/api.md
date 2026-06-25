# Platform API reference

Contributor-oriented mapping from [`const.py`](../custom_components/jullix/const.py) paths to [`JullixApiClient`](../custom_components/jullix/api.py) methods. Request and response schemas are documented on the [Mijn Jullix Platform API](https://mijn.jullix.be/apidocs/).

Fetch **tiers** (`CORE` vs `EXTENDED`) come from [`features.py`](../custom_components/jullix/features.py). Extended groups run on every 3rd coordinator refresh by default.

## Installations and live data

| Constant | Client method | Tier | Used for |
|----------|---------------|------|----------|
| `API_PATH_INSTALLATIONS` | `get_installations` | — (config flow) | Setup, token validation |
| `API_PATH_INSTALLATION` | `get_installation` | EXTENDED (`installation_meta`) | Device display name |
| `API_PATH_POWER_SUMMARY` | `get_power_summary` | CORE (`power_summary`) | Summary power sensors, insights |
| `API_PATH_ACTUAL_DETAIL` | `get_actual_detail` | CORE (`actual_details`) | Battery, solar, home detail |
| `API_PATH_ACTUAL_METERING` | `get_metering` | CORE (`actual_details`) | Dynamic metering channels |

## Chargers and plugs

| Constant | Client method | Tier | Used for |
|----------|---------------|------|----------|
| `API_PATH_CHARGERS` | `get_chargers` | CORE (`chargers_plugs`) | Charger list, power |
| `API_PATH_CHARGER_STATUS` | `get_charger_status` | CORE (`charger_control`) | Control state |
| `API_PATH_CHARGER_CONTROL` | `get_charger_control` / `set_charger_control` | CORE (`charger_control`) | Switch, number, select, service |
| `API_PATH_CHARGER_ENERGIES` | `get_charger_energies` | EXTENDED (`charger_extended`) | Charger energy today |
| `API_PATH_CHARGER_EVENTS` | `get_charger_events` | EXTENDED (`charger_extended`) | Charger events count |
| `API_PATH_PLUGS` | `get_plugs` | CORE (`chargers_plugs`) | Plug list, power |
| `API_PATH_PLUG_CONTROL` | `set_plug_control` | CORE (`charger_control`) | Plug switch, service |
| `API_PATH_PLUG_ENERGY` | `get_plug_energy` | CORE | Per-plug energy (optional path) |
| `API_PATH_PLUG_POWER` | `get_plug_power` | CORE | Per-plug power history |
| `API_PATH_HISTORY_PLUG_ENERGY` | `get_history_plug_energy` | CORE (`plug_energy_history`) | Plug energy today |
| `API_PATH_HISTORY_PLUG_POWER` | `get_history_plug_power` | — | **Not wired** in coordinator |
| `API_PATH_HISTORY_BATTERY_ENERGY` | `get_history_battery_energy` | CORE (`battery_energy_history`) | Battery energy backfill |

## Cost, statistics, sessions

| Constant | Client method | Tier | Used for |
|----------|---------------|------|----------|
| `API_PATH_COST_SAVINGS` | `get_cost_savings` | EXTENDED (`cost`) | Cost/savings sensors |
| `API_PATH_COST_TOTAL` | `get_cost_total` | EXTENDED (`cost`) | Monthly total |
| `API_PATH_COST_HOURLY_PRICE` | `get_cost_hourly_price` | EXTENDED (`cost_hourly_price`) | Hourly price helpers |
| `API_PATH_STATISTICS_ENERGY_DAILY` | `get_statistics_energy_daily` | EXTENDED (`statistics`) | Daily statistics |
| `API_PATH_STATISTICS_ENERGY_MONTHLY` | `get_statistics_energy_monthly` | EXTENDED (`statistics`) | Monthly statistics |
| `API_PATH_STATISTICS_ENERGY_YEARLY` | `get_statistics_energy_yearly` | EXTENDED (`statistics`) | Yearly statistics |
| `API_PATH_CHARGERSESSION_INSTALLATION` | `get_chargersession_installation` | EXTENDED (`chargersession`) | Session sensors |
| `API_PATH_CHARGERSESSION_ASSIGN` | `assign_chargersession` | — (service) | `jullix.assign_chargersession` |

## Tariff, weather, algorithm

| Constant | Client method | Tier | Used for |
|----------|---------------|------|----------|
| `API_PATH_TARIFF` | `get_tariff` / `update_tariff` | EXTENDED (`tariff`) | Tariff sensor, `jullix.update_tariff` |
| `API_PATH_WEATHER_FORECAST` | `get_weather_forecast` | EXTENDED (`weather`) | Weather forecast sensor |
| `API_PATH_WEATHER_ALARM` | `get_weather_alarm` | EXTENDED (`weather`) | Weather alarm sensor |
| `API_PATH_ALGORITHM_OVERVIEW` | `get_algorithm_overview` | EXTENDED (`algorithm_overview`) | Optimization sensor |
| `API_PATH_ALGORITHM_SETTINGS` | `get_algorithm_settings` | EXTENDED (`algorithm_extended`) | Extended optimizer sensors |
| `API_PATH_ALGORITHM_RESULTS` | `get_algorithm_results` | EXTENDED (`algorithm_extended`) | Extended optimizer sensors |
| `API_PATH_ALGORITHM_USAGE` | `get_algorithm_usage` | EXTENDED (`algorithm_extended`) | Extended optimizer sensors |
| `API_PATH_ALGORITHM_PVPREDICT` | `get_algorithm_pvpredict` | EXTENDED (`algorithm_extended`) | Solar prediction sensor |
| `API_PATH_ALGORITHM_OPTI` | `get_algorithm_opti` | EXTENDED | Legacy opti endpoint (if used) |
| `API_PATH_ALGORITHM_RUN_HOURLY` | `run_algorithm_hourly` | — (service) | `jullix.run_algorithm_hourly` |
| `API_PATH_ALGORITHM_FORCE` | `force_algorithm_command` | — (service) | `jullix.force_algorithm_command` |

## Reserved / not wired

| Constant | Client method | Notes |
|----------|---------------|-------|
| `API_PATH_CAR_BLOCK` | `get_car_block` | Client method exists; no coordinator fetch or entity |

## Jullix-Direct (local EMS)

Local paths are not `API_PATH_*` constants. **`JullixLocalClient`** reads `/api/ems/{meter,solar,battery,charger,plug}` on the configured host. Battery cumulative totals can override or supplement cloud data when **Merge local Jullix-Direct data** is enabled.

## Related reading

- [Architecture](architecture.md)
- [Feature tiers](features.md)
- [Development guide](development.md)
- [API fixtures](../tests/fixtures/api/)
