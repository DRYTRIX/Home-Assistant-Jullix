# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.10.2] - 2026-06-25

### Fixed

- **Integration setup** failed when loading switch, number, or select platforms because top-level platform modules imported `JullixInstallationSnapshot` from `..models` instead of `.models` (`ModuleNotFoundError: No module named 'custom_components.models'`).

## [1.10.1] - 2026-06-25

### Fixed

- **Integration setup** failed on load because `async_setup()` did not accept Home Assistant's `config` argument (`TypeError: async_setup() takes 1 positional argument but 2 were given`).

## [1.10.0] - 2026-06-25

### Added

- **Home Assistant framework:** config-entry deduplication, Repairs issues (auth/API/local EMS), device diagnostics, service unload when the last entry is removed, API client session cleanup, `quality_scale: bronze`.
- **Energy Dashboard sensors:** grid import/export kWh, solar production kWh, per-plug cumulative energy, per-charger energy total (when API provides lifetime totals); per-plug energy fetched on extended polls.
- **Button** platform — **Run hourly optimization** on the System device.
- **Tariff select** entity when cost sensors are enabled.
- **Dynamic entity discovery** for new chargers/plugs after setup (sensors, switches, selects, numbers).
- **Session history sensors** — last session energy and session ID when session history option is on.
- **Docs:** [Quality scale](docs/quality-scale.md), [Automations](docs/automations.md), grid-outage blueprint; expanded Energy Dashboard mapping in troubleshooting.

### Changed

- **Energy statistics** option defaults to on for new entries.
- **Local EMS merge** applies when the config entry has a single installation (unchanged) or to the first site in multi-site entries; consecutive local failures surface a repair issue.
- **Battery history backfill** matches slots by `localid` / device id when list lengths differ.

### Fixed

- **Charger mode** and **max power** entities read control state from the installation snapshot (not a dict on coordinator data).

## [1.9.0] - 2026-06-25

### Added

- **Battery energy sensors** — per-battery **Energy charged** and **Energy discharged** (`device_class: energy`, `state_class: total_increasing`) for Home Assistant's Energy Dashboard, sourced from Jullix-Direct EMS and cloud battery energy history ([#21](https://github.com/DRYTRIX/Home-Assistant-Jullix/issues/21)).

### Fixed

- **Local EMS battery merge** — unwrap the `{"data": [...]}` envelope from `/api/ems/battery` and do not replace cloud battery slots when local parsing yields no devices.

## [1.8.0] - 2026-06-24

### Added

- **Brand assets** in `custom_components/jullix/brand/` (HA 2026.3+ local brands) and **`contrib/home-assistant-brands/jullix/`** for upstream [home-assistant/brands](https://github.com/home-assistant/brands) PRs — see [docs/brands.md](docs/brands.md).
- **Extended API wiring:** installation metadata, per-charger status/energy/events, algorithm settings/results/usage/PV predict (extended poll).
- **Service** `jullix.force_algorithm_command` to send optimizer force commands.
- **Docs:** [HACS default catalog checklist](docs/hacs-publish.md).

### Changed

- Installation **device names** use the Jullix site name from `get_installation` when available.
- Removed unused **`OPTION_DEFAULT_INSTALL`** constant.

### Fixed

- **Options flow ("Configure")** raised a 500 Internal Server Error on Home Assistant 2025.12+ because the options flow handler was constructed with the now-removed `config_entry` constructor argument ([#21](https://github.com/DRYTRIX/Home-Assistant-Jullix/issues/21)).
- **Initial setup** could fail to finish validating the API token: the token-validation progress step returned a form result directly instead of handing off via `async_show_progress_done`, which Home Assistant's config flow manager rejects, silently breaking the flow.

## [1.7.1] - 2026-03-29

### Fixed

- **Config flow:** import **`ZeroconfServiceInfo`** from supported Home Assistant locations (and tolerate minimal environments without the **zeroconf** package).
- **Config flow / translations:** **`progress.validate_token`** uses a flat string value so the token validation step shows the correct message.

### Changed

- **Setup:** load **`JullixDataUpdateCoordinator`** and **`SessionHistoryRecorder`** only when applying a config entry (lighter module import path).
- **`derived`:** re-export **`format_hour_hint`** and **`estimate_session_cost_eur`** for reuse and tests.
- **`manifest.json`:** conventional key ordering (documentation block before **zeroconf**).

### Tests

- Stronger **homeassistant** stubs when the full core package is not installed (**`DataUpdateCoordinator`** base, **`util.dt`**, **`ServiceValidationError`**, frame helper).
- Config flow tests avoid double-scheduling the validation task; coordinator tests assign **`data`** like the real refresh path.

## [1.7.0] - 2026-03-29

### Added

- **Binary sensor** platform (for example peak tariff when the cost data path is enabled).
- Optional **`jullix_event`** firing for charger, battery, and grid-style transitions.
- Optional **session history** (last records in Home Assistant storage).
- **Modular layout:** `models/` installation snapshot, `sensors/` factories, `derived/` helpers, `features.py` for adaptive and extended polling, `runtime_state.py`, `device_helpers.py`.
- **Translations** under `translations/` (English).
- **Documentation:** [Architecture](docs/architecture.md), [Feature tiers](docs/features.md), [Development](docs/development.md), [Troubleshooting](docs/troubleshooting.md), [Releasing](docs/releasing.md), and [Screenshots](docs/screenshots/README.md).
- Tests for derived helpers, events, and models; shared **fixtures** under `tests/fixtures/`.

### Changed

- **Coordinator** and entity setup refactored around the snapshot model and optional API fetch groups.
- **Config flow** and **options** extended for events, session history, insights, adaptive polling, and related toggles.
- **README** and HACS **`info.md`** updated for the current feature set and doc links.
- **CI:** separate workflow job installs Home Assistant (`>=2024.12.0`) and runs config flow and entity tests; unit-test job keeps using `requirements-test-ci.txt`.

## [1.6.1]

### Fixed

- Tests: fix coordinator mock so all API methods are `AsyncMock`s (resolves `object MagicMock can't be used in 'await' expression` in CI).

## [1.6.0]

### Added

- Energy statistics sensors (daily / monthly / yearly, optional).
- Weather alarm sensor.
- Cost total this month (when cost sensors are enabled).
- `jullix.update_tariff` service.
- Integration option “Enable energy statistics sensors”.

### Changed

- Extended API client and coordinator tests; config flow test fixes; live API smoke tests for cost, tariff, algorithm, weather, and statistics.

## [1.5.2]

### Fixed

- Documentation: fix screenshot references (remove deleted energy placeholder; README and `info.md` use existing screenshots only).

## [1.5.1]

### Fixed

- Hassfest: remove invalid `icon` key from `manifest.json`.

### Changed

- README: add repository setup (HACS description / topics) section.

## [1.5.0]

### Added

- CI uses `requirements-test-ci.txt` for faster unit tests (config flow and entity tests skipped in CI).
- Hassfest validation workflow.
- `REPO_SETUP.md` and documentation updates.

### Changed

- Config flow test fix (options flow handler).

## [1.4.0]

### Changed

- API client: use `ThreadedResolver` for aiohttp (improved DNS compatibility).
- HACS brand icon; test updates.
