# Jullix integration tests

Run the test suite from the repo root:

- **Quick / CI** (no Home Assistant): `pip install -r requirements-test-ci.txt` then `python -m pytest tests/ -v` — config flow and entity tests are skipped.
- **Full suite** (including config flow and entity tests): `pip install -r requirements-test.txt` then `python -m pytest tests/ -v`

For contributor onboarding and how to add sensors or API methods, see [CONTRIBUTING.md](../CONTRIBUTING.md) and [docs/development.md](../docs/development.md).

## Test modules

- **test_api.py** – API client (installations, chargers, plugs, battery energy history, set_charger_control, set_plug_control, error handling)
- **test_coordinator.py** – Coordinator refresh, merges, and optional fetch behavior
- **test_sensor_helpers.py** – `_extract_plug_energy_total` for plug energy responses
- **test_services.py** – Service handlers (`set_charger_control`, `run_algorithm_hourly`, `force_algorithm_command`, `assign_chargersession`, `update_tariff`)
- **test_switch.py** – `_is_enabled` logic for charger/plug state
- **test_derived.py** – Derived helpers (tariff, statistics, session, insights)
- **test_events.py** – `jullix_event` firing helpers
- **test_models.py** – Installation snapshot and parser behavior, including battery energy charged/discharged parsing and history backfill
- **test_config_flow.py** – Config flow steps and options (skipped unless real Home Assistant is installed)
- **test_entities.py** – Platform setup and `unique_id`s (skipped unless real Home Assistant is installed)
- **test_live_api.py** – Live API smoke tests (skipped unless env vars are set; see below)

Home Assistant is mocked for most tests so they run without a full HA install. Config flow and entity tests require real `homeassistant` (e.g. from `requirements-test.txt`) and are skipped when the mock is active.

## API fixtures

JSON samples under [`fixtures/api/`](fixtures/api/) document response shapes used in unit tests:

| Fixture | Documents |
|---------|-----------|
| `power_summary.json` | `data.powers` summary envelope (`status: ok`) |
| `battery_detail.json` | Per-battery `power`, `energy_charged` / `energy_discharged`, nested `battery.soc` |
| `battery_energy_history.json` | Cloud history backfill for cumulative battery energy totals |
| `cost_hourly_price.json` | Hourly `price` array for tariff helpers |
| `chargersession.json` | Session list with `id`, `state`, `energy_kwh`, `charger_mac` |

Add new fixtures when you introduce parsers or coordinator paths that benefit from stable sample payloads.

## GitHub Actions

The workflow in `.github/workflows/test.yml` runs on every push and pull request to `main`/`master`:

1. **Unit tests** – Install `requirements-test-ci.txt` (no full Home Assistant); tests that require `homeassistant` are skipped. No secrets required. Optional **mypy** step (non-blocking).
2. **Config flow and entity tests** – Install Home Assistant and run `tests/test_config_flow.py` and `tests/test_entities.py` only.
3. **Live API smoke test** – Runs real API calls when these **repository secrets** are set:

| Secret name | Description |
|-------------|-------------|
| **`JULLIX_API_TOKEN`** | Your Jullix API JWT token (from Mijn Jullix) |
| **`JULLIX_INSTALLATION_ID`** | The installation ID to test against (e.g. from the API or app) |

To add them: **Settings → Secrets and variables → Actions → New repository secret.**

If either secret is missing, the live API tests are skipped and the job still passes. Once both are set, the workflow will call the real API and fail if the token or installation is invalid.
