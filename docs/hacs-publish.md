# HACS default catalog checklist

Use this checklist when submitting [Home-Assistant-Jullix](https://github.com/DRYTRIX/Home-Assistant-Jullix) for inclusion in the [default HACS integration catalog](https://hacs.xyz/docs/publish/integration).

## Repository requirements

- [x] Public GitHub repository with a clear **Description** and **Topics** (`home-assistant`, `hacs`, `integration`, `jullix`, `energy`) — see [.github/REPO_SETUP.md](../.github/REPO_SETUP.md)
- [x] Valid [`hacs.json`](../hacs.json) (`category`: integration, `filename`: `jullix`)
- [x] Integration under `custom_components/jullix/` with [`manifest.json`](../custom_components/jullix/manifest.json)
- [x] HACS validation workflow ([`.github/workflows/validate.yml`](../.github/workflows/validate.yml))
- [x] Tagged releases (`vX.Y.Z`) matching `manifest.json` version — see [releasing.md](releasing.md)
- [x] README and [`info.md`](../info.md) with install steps
- [x] Brand assets in [`custom_components/jullix/brand/`](../custom_components/jullix/brand/) and upstream copy in [`contrib/home-assistant-brands/jullix/`](../contrib/home-assistant-brands/jullix/)

## Before opening the HACS PR

1. Ensure the latest release tag is published on GitHub.
2. Confirm `hacs/action` passes on `main`.
3. Open a PR at [hacs/default](https://github.com/hacs/default) adding this repository to the integration list (follow current HACS docs for the exact file path and JSON format).
4. Merge [home-assistant/brands](https://github.com/home-assistant/brands) PR for domain `jullix` (see [brands.md](brands.md)) so Analytics and UI branding stay consistent.

## Note on install counts

Default catalog listing improves **discoverability** in HACS. It does **not** expose a private install counter to maintainers. For aggregated install statistics, rely on [Home Assistant Usage Analytics](brands.md) after the brands merge.
