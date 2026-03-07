# Jullix Home Assistant Integration

A complete HACS integration for [Jullix](https://wiki.jullix.be/) (Innovoltus Energy Management System), bringing solar, battery, grid, chargers, and smart plugs into Home Assistant.

## Features

- **Real-time power data**: Grid, solar, home consumption, battery charge/discharge, capacity tariff (captar)
- **Battery monitoring**: State of charge (SoC), power per battery
- **Solar production**: Per-string and aggregate power
- **Metering**: Electricity import/export, gas consumption
- **EV chargers**: Power and status per charger; optional on/off control
- **Smart plugs**: Power per plug; optional on/off control
- **Cost & savings**: Optional cost and savings sensors (when enabled in options)
- **Jullix-Direct**: Optional local connection for real-time data without internet

## Installation

### Via HACS (recommended)

1. Open **HACS** → **Integrations** → **Explore & Download Integrations**
2. Search for **Jullix** and install
3. Restart Home Assistant
4. Go to **Settings** → **Devices & services** → **Add integration** → **Jullix**

### Manual

1. Copy the `custom_components/jullix` folder into your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration via **Settings** → **Devices & services**

## Configuration

### API Token

1. Log in to [Mijn Jullix](https://mijn.jullix.be/)
2. Go to **Profiel** (Profile) → **API-tokens**
3. Create a token and copy the JWT
4. Paste the token in the integration setup

### Setup Steps

1. **API Token**: Enter your JWT from Mijn Jullix
2. **Installations**: Select which installation(s) to add
3. **Jullix-Direct (optional)**: Enter `jullix.local` or the IP of your local Jullix device for real-time data without internet. Leave empty to skip.

### Options

After setup, click **Configure** on the Jullix integration to adjust:

- **Update interval**: 30–300 seconds (default: 60)
- **Enable cost & savings sensors**: Show cost and savings data
- **Enable charger control**: Allow turning chargers on/off from Home Assistant
- **Enable plug control**: Allow turning smart plugs on/off
- **Prefer local Jullix-Direct**: Use local device for real-time data when configured

## Dashboard Suggestions

Use standard Home Assistant cards:

- **Energy dashboard**: Add Jullix power sensors (grid, solar, home, battery) to the Energy dashboard
- **Entity cards**: Group sensors by installation
- **History graph**: Use `sensor.jullix_*` entities for power history

Example Lovelace card for power overview:

```yaml
type: entities
title: Jullix Power
entities:
  - entity: sensor.jullix_xxx_summary_grid
  - entity: sensor.jullix_xxx_summary_solar
  - entity: sensor.jullix_xxx_summary_home
  - entity: sensor.jullix_xxx_summary_battery
```

## Documentation

- [Jullix Wiki](https://wiki.jullix.be/doku.php?id=nl:start)
- [Integration FAQ](https://wiki.jullix.be/doku.php?id=nl:faq:integratie)
- [Platform API](https://mijn.jullix.be/apidocs/)

## Requirements

- Home Assistant 2024.1 or newer
- Jullix account with API token
- Internet connection (or local Jullix-Direct for real-time data)

## Support

- [GitHub Issues](https://github.com/dries/HACS-Jullix/issues)
