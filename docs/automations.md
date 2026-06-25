# Jullix automations

## `jullix_event` trigger

When **Fire Home Assistant events** is enabled in integration options, the integration emits `jullix_event` on meaningful transitions.

### Event types

| `type` | When |
|--------|------|
| `charger_started` | Charger power crosses the active threshold |
| `charger_stopped` | Charger becomes idle |
| `battery_full` | Battery SoC reaches the configured high threshold |
| `battery_empty` | Battery SoC reaches the configured low threshold |
| `grid_outage` | Grid import/export heuristic indicates outage |
| `grid_reconnect` | Grid returns after outage heuristic |

### Example: notify when charging starts

```yaml
automation:
  - alias: "Jullix charger started"
    trigger:
      - platform: event
        event_type: jullix_event
        event_data:
          type: charger_started
    action:
      - service: notify.notify
        data:
          message: "EV charging started on {{ trigger.event.data.installation_id }}"
```

### Example: charge when electricity is cheap

Use the **Current hour price** or **Cheap energy window** sensors (requires **Cost and savings sensors** in options), or the blueprint below.

## Blueprints

See [`blueprints/automation/jullix/notify_grid_outage.yaml`](../blueprints/automation/jullix/notify_grid_outage.yaml) for a starter grid-outage notification.

## Services vs buttons

- **Run hourly optimization** — available as a **button** on the System device and as `jullix.run_algorithm_hourly`.
- **Update tariff** — `jullix.update_tariff` service or the **Tariff** select (when cost sensors are enabled).
