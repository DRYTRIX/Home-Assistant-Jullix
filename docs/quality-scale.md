# Home Assistant quality scale (bronze)

The integration declares `"quality_scale": "bronze"` in `manifest.json`. Progress toward silver/gold is tracked here.

## Bronze checklist

| Rule | Status |
|------|--------|
| Config flow | Done |
| Unique config entry ID / deduplication | Done (`entry_unique_id`, overlap abort) |
| Reauthentication | Done |
| Repairs issues (auth, API, local EMS) | Done |
| Config entry diagnostics | Done |
| Device diagnostics | Done |
| Entity naming (`has_entity_name`, `translation_key`) | Done |
| Service registration and unload on last entry | Done |
| Zeroconf discovery | Done |
| Coordinator + `CoordinatorEntity` | Done |
| API client session cleanup on unload | Done |

## Next (silver)

- Dynamic entity discovery hardening (tests, unavailable state for removed devices)
- Broader live API validation for cumulative kWh endpoints
- Additional repair fix flows where HA version supports them
