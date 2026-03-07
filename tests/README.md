# Jullix integration tests

Run the test suite from the repo root:

- **Quick / CI** (no Home Assistant): `pip install -r requirements-test-ci.txt` then `python -m pytest tests/ -v` — config flow and entity tests are skipped.
- **Full suite** (including config flow and entity tests): `pip install -r requirements-test.txt` then `python -m pytest tests/ -v`

Tests cover:

- **test_api.py** – API client (installations, chargers, plugs, set_charger_control, set_plug_control, error handling)
- **test_coordinator.py** – `_merge_local_data` for Jullix-Direct
- **test_sensor_helpers.py** – `_extract_plug_energy_total` for plug energy responses
- **test_services.py** – Service handlers (set_charger_control, run_algorithm_hourly, assign_chargersession)
- **test_switch.py** – `_is_enabled` logic for charger/plug state
- **test_config_flow.py** – Config flow steps and options (skipped unless real Home Assistant is installed)
- **test_entities.py** – Sensor/switch/number/select setup and unique_ids (skipped unless real Home Assistant is installed)
- **test_live_api.py** – Live API smoke tests (skipped unless env vars are set; see below)

Home Assistant is mocked for most tests so they run without a full HA install. Config flow and entity tests require real `homeassistant` (e.g. from `requirements-test.txt`) and are skipped when the mock is active.

## GitHub Actions

The workflow in `.github/workflows/test.yml` runs on every push and pull request to `main`/`master`:

1. **Unit tests** – Install `requirements-test-ci.txt` (no full Home Assistant); config flow and entity tests are skipped. No secrets required.
2. **Live API smoke test** – Runs real API calls when these **repository secrets** are set:

| Secret name | Description |
|-------------|-------------|
| **`JULLIX_API_TOKEN`** | Your Jullix API JWT token (from Mijn Jullix) |
| **`JULLIX_INSTALLATION_ID`** | The installation ID to test against (e.g. from the API or app) |

To add them: **Settings → Secrets and variables → Actions → New repository secret.**

If either secret is missing, the live API tests are skipped and the job still passes. Once both are set, the workflow will call the real API and fail if the token or installation is invalid.
