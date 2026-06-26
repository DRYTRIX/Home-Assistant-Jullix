# HACS default catalog checklist

Use this checklist when submitting [Home-Assistant-Jullix](https://github.com/DRYTRIX/Home-Assistant-Jullix) for inclusion in the [default HACS integration catalog](https://hacs.xyz/docs/publish/integration).

## Automated requirements

These are enforced by GitHub Actions and the `hacs/default` PR checks:

- [x] Public GitHub repository with a clear **Description** and **Topics** (`home-assistant`, `hacs`, `integration`, `jullix`, `energy`) — see [.github/REPO_SETUP.md](../.github/REPO_SETUP.md)
- [x] Valid [`hacs.json`](../hacs.json) (`category`: integration, `filename`: `jullix`)
- [x] Integration under `custom_components/jullix/` with [`manifest.json`](../custom_components/jullix/manifest.json)
- [x] HACS validation workflow ([`.github/workflows/validate.yml`](../.github/workflows/validate.yml))
- [x] Hassfest workflow ([`.github/workflows/hassfest.yaml`](../.github/workflows/hassfest.yaml))
- [x] Tagged releases (`vX.Y.Z`) matching `manifest.json` version — see [releasing.md](releasing.md)
- [x] Brand assets in [`custom_components/jullix/brand/`](../custom_components/jullix/brand/) and upstream copy in [`contrib/home-assistant-brands/jullix/`](../contrib/home-assistant-brands/jullix/)
- [x] Doc placeholder guardrail ([`scripts/check-docs-placeholders.sh`](../scripts/check-docs-placeholders.sh))

## Documentation quality (human review)

HACS maintainers manually review README and LICENSE. Verify before opening or re-requesting a `hacs/default` PR:

### LICENSE

- [ ] Standard [MIT](https://choosealicense.com/licenses/mit/) text, not paraphrased
- [ ] No bracket placeholders (`[Your Name]`, `[year]`, etc.)
- [ ] Copyright holder matches the GitHub owner or org (`DRYTRIX`)
- [ ] Year range covers first public release through the current year

### README

- [ ] Opens with a concrete value proposition tied to Jullix / Mijn Jullix (not generic integration boilerplate)
- [ ] Install steps use exact Home Assistant UI paths (**HACS → Integrations**, **Settings → Devices & services**)
- [ ] Option names match [`strings.json`](../custom_components/jullix/strings.json) `options.step.init.data` labels
- [ ] Services match [`services.yaml`](../custom_components/jullix/services.yaml)
- [ ] At least one real screenshot from a maintainer Home Assistant instance (token blurred)
- [ ] YAML examples use `sensor.jullix_…` entity ids with a realistic sample UUID, not `your_entity_here` or `<installation_uuid>`
- [ ] No unfilled template sections (empty Contributing/Support blocks, cookiecutter leftovers)

### Repository metadata (GitHub UI)

- [ ] Repository **Description** and **Topics** set per [.github/REPO_SETUP.md](../.github/REPO_SETUP.md)
- [ ] Issues enabled

### HACS 2.0 note

HACS renders the repository **README**, not [`info.md`](../info.md). Keep `info.md` aligned for consistency, but treat [README.md](../README.md) as the storefront.

## Before opening the HACS PR

1. Run through the [documentation quality](#documentation-quality-human-review) checklist above.
2. Ensure the latest **GitHub Release** (not just a tag) is published and matches `manifest.json` version.
3. Confirm `hacs/action` and Hassfest pass on `main`.
4. Open a PR at [hacs/default](https://github.com/hacs/default) adding this repository to the integration list (alphabetically sorted; follow current HACS docs for file path and JSON format).
5. Merge [home-assistant/brands](https://github.com/home-assistant/brands) PR for domain `jullix` (see [brands.md](brands.md)) so Analytics and UI branding stay consistent.

## PR reply template

When re-requesting review or responding to documentation feedback, post something like:

```text
Documentation updates for human review:

- LICENSE: MIT with Copyright (c) DRYTRIX, standard text, no placeholders
- README: trimmed to install/setup/options; product-specific paths and option labels from strings.json
- Screenshots: real HA captures in docs/screenshots/ (token blurred)
- Examples: realistic installation UUID in docs/automations.md and docs/troubleshooting.md
- CI: scripts/check-docs-placeholders.sh blocks common template leftovers

Latest release: vX.Y.Z (matches manifest.json)
HACS action + Hassfest: green on main
```

Replace `vX.Y.Z` with the actual release.

## After the PR is merged

- Update the README HACS badge from **Custom** (orange) to **Default** (blue).
- Default catalog listing improves **discoverability** in HACS. It does **not** expose a private install counter to maintainers. For aggregated install statistics, rely on [Home Assistant Usage Analytics](brands.md) after the brands merge.
