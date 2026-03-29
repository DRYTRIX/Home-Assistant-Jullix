# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
