# Jullix automations

## Find your installation ID

Services and many entity IDs need the Jullix installation UUID for your site:

- **Settings → Devices & services → Jullix → [your site]** — copy the UUID from the device page, or
- **Developer tools → States** — filter `jullix` and read the UUID from any entity id (e.g. `sensor.jullix_a1b2c3d4_e5f6_7890_abcd_ef1234567890_summary_solar`).

Examples below use `a1b2c3d4-e5f6-7890-abcd-ef1234567890` as a stand-in; replace it with your value.

## Services

All services use the `jullix` domain. `installation_id` must match a site configured in this Home Assistant instance.

| Service | Purpose |
|---------|---------|
| `jullix.set_charger_control` | Charger on/off, mode (`eco`, `turbo`, `max`, `block`), max power kW (1.4–22). Needs `charger_mac`. |
| `jullix.run_algorithm_hourly` | Trigger hourly optimization. |
| `jullix.force_algorithm_command` | Send a force command to the gateway optimizer. |
| `jullix.assign_chargersession` | Assign a session to charger and/or car. Needs `session_id`. |
| `jullix.update_tariff` | Set tariff code (e.g. `single`, `dual`). |

Field definitions and selectors: [`services.yaml`](../custom_components/jullix/services.yaml).

## `jullix_event` trigger

When **Fire Home Assistant events for charger, battery, and grid changes** is enabled in integration options, the integration emits `jullix_event` on meaningful transitions. Payload includes `type`, `installation_id`, `domain: jullix`, and sometimes `charger_mac`, `power_w`, `soc`, `grid_import_w`.

Automation trigger: platform `event`, `event_type: jullix_event`.

### Event types

| `type` | When |
|--------|------|
| `charger_started` / `charger_stopped` | Active above ~400 W / idle below ~150 W |
| `battery_full` / `battery_empty` | SoC ≥ 95% / ≤ 10% |
| `grid_outage` / `grid_reconnect` | Import below ~300 W for 2 polls with low home load / recovery |

### Example: notify when charging starts

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

### Example: peak tariff warning

Requires **Cost and savings sensors** in integration options.

```yaml
automation:
  - alias: "Jullix peak tariff warning"
    trigger:
      - platform: state
        entity_id: binary_sensor.jullix_a1b2c3d4_e5f6_7890_abcd_ef1234567890_peak_tariff
        to: "on"
    action:
      - service: notify.persistent_notification
        data:
          title: "Peak tariff window"
          message: "Current hour is in a high-price period."
```

### Example: nightly optimization

```yaml
automation:
  - alias: "Jullix nightly optimization"
    trigger:
      - platform: time
        at: "23:30:00"
    action:
      - service: jullix.run_algorithm_hourly
        data:
          installation_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### Example: charge when electricity is cheap

Use the **Current hour price** or **Cheap energy window** sensors (requires **Cost and savings sensors** in options), or combine with tariff helpers from the cost sensors.

## Blueprints

See [`blueprints/automation/jullix/notify_grid_outage.yaml`](../blueprints/automation/jullix/notify_grid_outage.yaml) for a starter grid-outage notification.

## Services vs buttons

- **Run hourly optimization** — available as a **button** on the System device and as `jullix.run_algorithm_hourly`.
- **Update tariff** — `jullix.update_tariff` service or the **Tariff** select (when cost sensors are enabled).
