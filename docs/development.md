# Development guide

## Project structure

```text
custom_components/jullix/
  __init__.py          # setup_entry, platforms, service registration
  api.py               # JullixApiClient (Platform API)
  config_flow.py       # UI setup and options
  const.py             # DOMAIN, API paths, option keys, thresholds
  coordinator.py       # JullixDataUpdateCoordinator
  features.py          # Feature tiers and extended poll scheduling
  events.py            # jullix_event firing
  binary_sensor.py
  sensor.py            # delegates to sensors/
  switch.py, number.py, select.py
  services.yaml
  strings.json, translations/
  models/              # JullixInstallationSnapshot, parsers
  sensors/             # Modular sensor factories (setup.py aggregates)
  derived/             # Tariff / hourly helpers
  session_history.py   # Optional session log storage
  local_client.py      # Jullix-Direct
tests/                 # pytest suite
docs/                  # This documentation
```

## How to add a new sensor

1. **Data source** — Add or reuse an API method in [`api.py`](../custom_components/jullix/api.py) and a path constant in [`const.py`](../custom_components/jullix/const.py) if needed.
2. **Coordinator** — Fetch the data in [`coordinator.py`](../custom_components/jullix/coordinator.py), store raw fragments on **`RawInstallFetches`** (in [`models/installation.py`](../custom_components/jullix/models/installation.py)) if you need new fields, and extend **`build_installation_snapshot`** so **`JullixInstallationSnapshot`** exposes parsed values.
3. **Entity** — Implement a sensor class (often subclassing **`JullixSensor`** in [`sensors/base.py`](../custom_components/jullix/sensors/base.py)) or add a factory in the appropriate module under **`sensors/`** (see [`sensors/cost.py`](../custom_components/jullix/sensors/cost.py) or [`sensors/energy.py`](../custom_components/jullix/sensors/energy.py)).
4. **Registration** — Wire the factory into [`sensors/setup.py`](../custom_components/jullix/sensors/setup.py) (`async_setup_entry`), gated by options if the sensor is optional.
5. **Translations** — Add `entity` / `sensor` keys to [`strings.json`](../custom_components/jullix/strings.json) and [`translations/en.json`](../custom_components/jullix/translations/en.json) (and other locales as needed).

If the sensor is tied to an **extended** API group, consider registering the fetch group in [`features.py`](../custom_components/jullix/features.py) (`FETCH_GROUP_TIER`) and only calling the API when `run_extended_this_refresh` is true in the coordinator.

## How to extend the API client

1. Add **`API_PATH_*`** in [`const.py`](../custom_components/jullix/const.py).
2. Add an **`async def`** on **`JullixApiClient`** that builds the URL, calls **`_request`** (or the existing pattern), and returns parsed JSON or typed data.
3. Handle **`JullixAuthError`** vs **`JullixApiError`** consistently with existing methods.
4. From the coordinator, call the new method and pass results into snapshot building.

## Testing

See [`tests/README.md`](../tests/README.md) for commands and CI behavior.

- **CI / quick run:** `pip install -r requirements-test-ci.txt` then `python -m pytest tests/ -v` — config flow and entity tests are skipped without full Home Assistant.
- **Full suite:** `pip install -r requirements-test.txt` then `python -m pytest tests/ -v` — includes tests that import `homeassistant`.
- **Live API:** Set `JULLIX_API_TOKEN` and `JULLIX_INSTALLATION_ID`; optional smoke tests run when both are present.

Add unit tests under `tests/` mirroring the module you change (`test_api.py`, `test_coordinator.py`, `test_services.py`, etc.).

## Architecture reference

For coordinator behavior, models, and data flow, see [Architecture](architecture.md).
