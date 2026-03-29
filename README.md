# Jullix Home Assistant integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![GitHub Issues](https://img.shields.io/badge/Support-GitHub%20Issues-blue.svg)](https://github.com/DRYTRIX/Home-Assistant-Jullix/issues)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow.svg)](https://buymeacoffee.com/drytrix)

**Connect [Jullix](https://wiki.jullix.be/) (Innovoltus Energy Management System) to Home Assistant:** live power and energy data, battery and solar visibility, EV chargers and smart plugs, optional cost and tariff helpers, and automations via services and `jullix_event`. Data comes from the [Mijn Jullix](https://mijn.jullix.be/) Platform API, with optional **Jullix-Direct** LAN merge for faster local readings.

---

## What is this?

This integration is a config-flow–based custom component that polls Jullix in the cloud (`cloud_polling`) and exposes **sensors**, **binary sensors**, and (when enabled) **switches**, **numbers**, and **selects** for chargers and plugs. Power is normalized to **watts** for compatibility with the [Energy dashboard](https://www.home-assistant.io/docs/energy/) and standard templates. Advanced behavior (cost, statistics, tariff, weather, algorithm, charge session, events, adaptive polling) is **optional** so you can keep the entity list small.

**Further reading:** [Architecture](docs/architecture.md) · [Feature tiers](docs/features.md) · [Troubleshooting](docs/troubleshooting.md) · [Changelog](CHANGELOG.md)

---

## Features

### Core (stable)

- **Power summary:** Grid, solar, home, battery (including capacity tariff / captar where provided).
- **Detail channels:** Battery, solar strings, grid, home, plugs, chargers, metering (import/export, gas where available).
- **EV chargers:** Power and status per charger.
- **Smart plugs:** Per-plug power; installation-level **plug energy today** via history API.
- **Diagnostics:** Connection health, API latency, last successful update.
- **Discovery:** Zeroconf `_http._tcp.local.` with name `jullix*` can pre-fill the optional local host step.

### Advanced (optional or heavier API use)

- **Charger control:** Switch, max power (kW), mode select (eco / turbo / max / block), plus service `jullix.set_charger_control`.
- **Plug control:** On/off switches for smart plugs.
- **Cost and savings:** Optional sensors including **cost total this month**; hourly price and **automation helper** sensors; **Peak tariff** binary sensor (when cost path is active).
- **Energy statistics:** Optional daily, monthly, yearly statistics sensors.
- **Tariff and weather:** Tariff and forecast sensors; `jullix.update_tariff`; weather alarm.
- **Algorithm:** Optimization overview sensors; `jullix.run_algorithm_hourly`; `jullix.assign_chargersession`.
- **Energy insights:** Instantaneous % estimates from power summary (not the same as metered kWh self-consumption)—can be disabled.
- **Events:** Home Assistant event type **`jullix_event`** for charger, battery, and grid-style transitions (can be disabled).
- **Adaptive polling:** Faster ~30 s polling while charging or during strong grid/battery activity.
- **Charge session:** Session-related sensors and suggestions (extra API usage on extended polls).
- **Session history:** Last 50 session records in HA storage when enabled.
- **Jullix-Direct:** Optional local host; merge with cloud when **Prefer local** is enabled.

### Experimental

- No **user-facing** experimental flags today. Internal **`EXPERIMENTAL`** API tier in code is reserved for future unstable endpoints (see [docs/features.md](docs/features.md)).

---

## Prerequisites

- **Home Assistant** 2024.1 or newer ([`homeassistant>=2024.1.0`](requirements-test.txt) in the full test stack).
- A **Jullix account** with at least one installation.
- A **Platform API JWT** from Mijn Jullix (treat it like a password).
- **Internet** access from the Home Assistant host (or use Jullix-Direct only for merged local data—cloud polling still applies for full functionality).

---

## Installation

### HACS (recommended)

1. Install [**HACS**](https://hacs.xyz/docs/setup/download) if you have not already, then restart Home Assistant.
2. Open **HACS** → **Integrations** → open the **⋮** menu (top right) → **Custom repositories**.
3. Add repository **`https://github.com/DRYTRIX/Home-Assistant-Jullix`**, category **Integration**, then **Add**.
4. In **HACS** → **Integrations** → **Explore & Download Repositories**, search for **Jullix**, open it, and **Download**.
5. **Restart** Home Assistant.
6. Go to **Settings** → **Devices & services** → **Add integration** → **Jullix**.

If Jullix is ever listed in the default HACS catalog, you can skip the custom repository step and install directly from **Explore & Download**.

### Manual

1. Copy the [`custom_components/jullix`](custom_components/jullix) folder into your Home Assistant **`config/custom_components/`** directory.
2. Restart Home Assistant.
3. Add the integration under **Settings** → **Devices & services** → **Add integration** → **Jullix**.

---

## Setup guide

### 1. Create an API token

1. Log in to **[Mijn Jullix](https://mijn.jullix.be/)**.
2. Go to **Profiel** (Profile) → **API-tokens**.
3. Create a token and copy the **JWT** (full string, no spaces).

![API token step (placeholder — replace with your UI capture)](docs/screenshots/setup-api-token.png)

### 2. Add the integration and validate the token

1. **Settings** → **Devices & services** → **Add integration** → **Jullix**.
2. Paste the token. The flow contacts Jullix and loads your account.

### 3. Select installation(s)

Choose one or more sites to include in this config entry. You can add another config entry later for a different account if needed.

![Installation selection (placeholder)](docs/screenshots/setup-installations.png)

### 4. Optional: Jullix-Direct

Enter **`jullix.local`** or the device **IP**, or leave empty for cloud-only. If you enter a host, the flow checks reachability; you can still complete setup if local check fails and fix the network later.

### 5. Tune options

Open **Configure** on the Jullix integration card to change polling and feature toggles (see next section).

![Options (placeholder)](docs/screenshots/options-jullix.png)

---

## Configuration options

All options are under **Settings** → **Devices & services** → **Jullix** → **Configure**. Defaults favor a rich setup; disable what you do not need to reduce entities and API load.

| Option | Default | What it does |
|--------|---------|----------------|
| **Polling interval (seconds)** | 60 | How often the coordinator refreshes cloud data (allowed range 30–300). Lower is more responsive; higher reduces load. |
| **Cost and savings sensors** | Off | Adds cost/savings/monthly total, hourly price helpers, peak tariff binary, and related automation-oriented sensors when Jullix provides data. |
| **Energy statistics sensors** | Off | Daily / monthly / yearly energy statistics entities (more API data on extended polls). |
| **Charger controls** | On | Exposes charger switch, max power number, and mode select. **Security:** anyone who can use Home Assistant can start/stop charging—turn off if undesired. |
| **Smart plug switches** | On | On/off control for smart plugs. |
| **Merge local Jullix-Direct data when configured** | Off | When a local host was set at setup, merges live local EMS data with cloud data for the first configured installation. Requires the local device to be reachable. |
| **Energy insight sensors** | On | Self-consumption / solar use / grid dependency style **instantaneous** estimates from power summary. |
| **Fire Home Assistant events** | On | Enables **`jullix_event`** for charger start/stop, battery high/low, and grid heuristics. |
| **Adaptive polling** | Off | Uses a ~30 s interval while charging or during strong grid/battery power; otherwise uses your polling interval. |
| **Charge session and suggestion sensors** | On | Session-related sensors (extra calls on extended polls). |
| **Store short session log in Home Assistant storage** | Off | Retains the last 50 session records in HA storage. |

---

## Entities overview

Entity IDs typically include your **installation UUID** (for example `sensor.jullix_<uuid>_summary_solar`). Platforms used:

- **Sensor** — Power, energy, metering, diagnostics, cost, statistics, tariff, weather, algorithm, insights, charger session helpers, etc.
- **Binary sensor** — e.g. **Peak tariff** when cost helpers are enabled.
- **Switch / Number / Select** — Charger and plug control when those options are on.

Use **Settings** → **Devices & services** → **Jullix** → your **device** to browse everything for a site, or **Developer tools** → **States** and filter `jullix`.

---

## Services

Services appear under the **`jullix`** domain (**Developer tools** → **Services**). **`installation_id`** must match an installation configured in this Home Assistant instance.

| Service | Purpose |
|---------|---------|
| **`jullix.set_charger_control`** | Set charger **on/off**, **mode** (`eco`, `turbo`, `max`, `block`), and/or **max_power** (kW, 1.4–22). Requires `installation_id`, `charger_mac`. |
| **`jullix.run_algorithm_hourly`** | Triggers Jullix **hourly optimization** for an installation. |
| **`jullix.assign_chargersession`** | Assigns a charge **session** to optional **charger** and/or **car**. Requires `session_id`. |
| **`jullix.update_tariff`** | Sets the active **tariff** code (e.g. `single`, `dual`)—must match values Jullix accepts. |

Field details and selectors match [`custom_components/jullix/services.yaml`](custom_components/jullix/services.yaml).

---

## Events (`jullix_event`)

When **Fire Home Assistant events** is enabled, the integration fires **`jullix_event`** with a payload including:

- **`type`:** `charger_started`, `charger_stopped`, `battery_full`, `battery_empty`, `grid_outage`, `grid_reconnect`
- **`installation_id`:** Jullix installation UUID
- **`domain`:** `jullix`
- Extra keys may include **`charger_mac`**, **`power_w`**, **`soc`**, **`grid_import_w`** depending on the event

**Automation trigger:** Event type **`jullix_event`** (platform `event`).

---

## Example automations

### Notify when a charger starts charging

```yaml
automation:
  - alias: "Jullix charger started notify"
    trigger:
      - platform: event
        event_type: jullix_event
        event_data:
          type: charger_started
    action:
      - service: notify.persistent_notification
        data:
          title: "Charging started"
          message: "Charger {{ trigger.event.data.charger_mac }} on {{ trigger.event.data.installation_id }}"
```

### Alert on peak tariff (binary sensor)

Replace `<installation_uuid>` with your installation id (same string as in entity names).

```yaml
automation:
  - alias: "Jullix peak tariff warning"
    trigger:
      - platform: state
        entity_id: binary_sensor.jullix_<installation_uuid>_peak_tariff
        to: "on"
    action:
      - service: notify.persistent_notification
        data:
          title: "Peak tariff window"
          message: "Current hour is in a high-price period."
```

### Run hourly optimization on a schedule

```yaml
automation:
  - alias: "Jullix nightly optimization"
    trigger:
      - platform: time
        at: "23:30:00"
    action:
      - service: jullix.run_algorithm_hourly
        data:
          installation_id: "<installation_uuid>"
```

---

## Dashboard and usage

### Energy dashboard

Add Jullix **grid**, **solar**, **home**, and **battery** power sensors where appropriate in [**Energy**](https://www.home-assistant.io/docs/energy/) configuration.

![Energy dashboard example (placeholder)](docs/screenshots/energy-dashboard.png)

### Power units

Power is stored in **watts (W)**. For a kW template sensor:

```yaml
template:
  - sensor:
      - name: "Jullix solar power kW"
        unique_id: jullix_solar_power_kw
        unit_of_measurement: "kW"
        state: "{{ (states('sensor.jullix_<installation_uuid>_summary_solar') | float(0) / 1000) | round(2) }}"
        device_class: power
```

### Example Lovelace card

```yaml
type: entities
title: Jullix power
entities:
  - entity: sensor.jullix_<installation_uuid>_summary_grid
  - entity: sensor.jullix_<installation_uuid>_summary_solar
  - entity: sensor.jullix_<installation_uuid>_summary_home
  - entity: sensor.jullix_<installation_uuid>_summary_battery
```

![Entities card example (placeholder)](docs/screenshots/dashboard-entities.png)

---

## Screenshots

Placeholder images are committed so links stay valid. **Replace** them with real captures using [docs/screenshots/README.md](docs/screenshots/README.md).

| Step | Preview |
|------|---------|
| API token | ![](docs/screenshots/setup-api-token.png) |
| Installations | ![](docs/screenshots/setup-installations.png) |
| Options | ![](docs/screenshots/options-jullix.png) |
| Dashboard | ![](docs/screenshots/dashboard-entities.png) |
| Energy | ![](docs/screenshots/energy-dashboard.png) |

---

## Documentation index

| Document | Description |
|----------|-------------|
| [CHANGELOG.md](CHANGELOG.md) | Version history (Keep a Changelog). |
| [docs/architecture.md](docs/architecture.md) | API, coordinator, models, data flow. |
| [docs/features.md](docs/features.md) | Core / extended / experimental tiers and polling. |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Token, API, entities, local connection, services. |
| [docs/development.md](docs/development.md) | Project layout, new sensors, API extensions, tests. |
| [docs/releasing.md](docs/releasing.md) | Version bump, tag, GitHub Release, HACS. |
| [tests/README.md](tests/README.md) | Pytest commands and CI. |

### External links

- [Jullix Wiki](https://wiki.jullix.be/doku.php?id=nl:start)
- [Integration FAQ](https://wiki.jullix.be/doku.php?id=nl:faq:integratie)
- [Platform API docs](https://mijn.jullix.be/apidocs/)
- [HACS publish checklist](https://hacs.xyz/docs/publish/include#check-repository)

---

## Repository setup (HACS validation)

On the GitHub repository **About** section:

- **Description:** e.g. “Jullix integration for Home Assistant”.
- **Topics:** e.g. `home-assistant`, `hacs`, `integration`, `jullix`, `energy`.

---

## Support

- **[GitHub Issues](https://github.com/DRYTRIX/Home-Assistant-Jullix/issues)**
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
