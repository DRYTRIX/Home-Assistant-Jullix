# Jullix

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow.svg)](https://buymeacoffee.com/drytrix)

Integration for the [Jullix](https://wiki.jullix.be/) Energy Management System (Innovoltus). Bring solar, battery, grid, EV chargers, and smart plugs into Home Assistant with real-time power monitoring and optional device control.

## Features

- **Real-time power**: Grid, solar, home consumption, battery, capacity tariff (captar)
- **Battery**: State of charge (SoC) and power per battery
- **Metering**: Electricity import/export, gas consumption
- **EV chargers**: Status and power; full control (switch, max power number, mode select, optional service)
- **Smart plugs**: Power and plug energy today; on/off control
- **Cost & savings**: Optional cost, savings, and cost total this month sensors
- **Energy statistics**: Optional daily, monthly, yearly energy statistics sensors
- **Weather alarm**: Sensor for active weather alerts
- **Algorithm, tariff, weather**: Optimization overview, tariff, and weather forecast sensors; services for run-hourly, assign charge session, and update tariff
- **Binary sensors**: For example peak tariff when cost sensors are enabled
- **Automation events**: Optional `jullix_event` for charger, battery, and grid-style transitions
- **Session history**: Optional storage of recent charge sessions in Home Assistant
- **Jullix-Direct**: Local real-time data merged with cloud when configured

## Installation

1. In **HACS** → **Integrations** → **⋮** → **Custom repositories**, add `https://github.com/DRYTRIX/Home-Assistant-Jullix` (category **Integration**) if the integration is not in the default catalog
2. **Explore & Download** → search **Jullix** → **Download**, then restart Home Assistant
3. **Settings** → **Devices & services** → **Add integration** → **Jullix**
4. Enter your API token from [Mijn Jullix](https://mijn.jullix.be/) (Profiel → API-tokens) and select your installation(s)

![Jullix HACS preview](docs/screenshots/hacs-preview.png)

More images and captions: [docs/screenshots](docs/screenshots/README.md).

## Documentation

For full setup, configuration options, dashboard examples, architecture, and troubleshooting, see the [README](https://github.com/DRYTRIX/Home-Assistant-Jullix) and the [docs](https://github.com/DRYTRIX/Home-Assistant-Jullix/tree/main/docs) folder on GitHub.
