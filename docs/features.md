# Feature tiers

The integration uses **internal feature tiers** to schedule API work. This is separate from **integration options** in the UI: options decide *whether* to create certain entities; tiers decide *how often* some API groups run relative to the coordinator refresh.

## Tiers (code)

Defined in [`custom_components/jullix/features.py`](../custom_components/jullix/features.py):

| Tier | Meaning |
|------|---------|
| **CORE** | Fetched on **every** coordinator refresh. |
| **EXTENDED** | Fetched only on some refreshes (see below). |
| **EXPERIMENTAL** | Reserved for unstable endpoints; **no groups use this tier today**. |

### Extended polling interval

- Constant: **`EXTENDED_POLL_INTERVAL = 3`**
- Function: **`run_extended_this_refresh(refresh_counter)`** returns true every 3rd refresh (with counter semantics so the **first** refresh still loads extended data).

So extended API groups run roughly **one third** as often as core groups, reducing load while keeping core power and device data fresh.

## `FETCH_GROUP_TIER` registry

These string keys label API capability groups inside the coordinator (not all are 1:1 with a single HTTP call):

| Group key | Tier |
|-----------|------|
| `power_summary` | CORE |
| `actual_details` | CORE |
| `chargers_plugs` | CORE |
| `charger_control` | CORE |
| `plug_energy_history` | CORE |
| `cost` | EXTENDED |
| `cost_hourly_price` | EXTENDED |
| `chargersession` | EXTENDED |
| `statistics` | EXTENDED |
| `tariff` | EXTENDED |
| `weather` | EXTENDED |
| `algorithm_overview` | EXTENDED |

**EXPERIMENTAL:** The registry has no entries yet; future unstable endpoints can be added here without changing the user-facing options model.

## User-visible options vs tiers

Integration **options** ( **Settings → Devices & services → Jullix → Configure** ) control entities and some fetch toggles. They do not rename the internal tiers, but they align roughly as follows:

| Option | Effect relative to tiers |
|--------|---------------------------|
| **Polling interval** | Base seconds between coordinator runs (adaptive polling may shorten temporarily). |
| **Cost and savings sensors** | When off, cost-related fetches and cost entities are skipped. When on, cost groups participate on **extended** ticks. |
| **Energy statistics sensors** | When on, statistics API groups run on extended ticks and statistics entities are created. |
| **Charge session and suggestion sensors** | When on, charger session fetches run on extended ticks and related entities are created. |
| **Cost and savings** + hourly price | Enables tariff helper sensors and peak tariff binary sensor; hourly price data is tied to extended cost/tariff fetches. |

**Always-on core behavior** (subject to having data from Jullix): power summary, actual details, chargers/plugs listing, plug energy history path used for installation plug energy today, and diagnostics.

## Documentation for end users

- For setup and a feature list aimed at installers, see the [README](../README.md) **Features** section (Core / Advanced / Experimental).
- For architecture and data flow, see [Architecture](architecture.md).
