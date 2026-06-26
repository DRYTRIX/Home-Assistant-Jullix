# Jullix integration documentation

Docs for the [Home Assistant Jullix integration](https://github.com/DRYTRIX/Home-Assistant-Jullix). New users: start with the [README](../README.md) (install, setup, options).

**HACS 2.0+** renders the repository [README](../README.md) in the store UI, not [`info.md`](../info.md). Keep both in sync when changing install steps or screenshots.

## Install and use

| Document | Description |
|----------|-------------|
| [README](../README.md) | Installation, setup, options (HACS storefront) |
| [info.md](../info.md) | Short summary (legacy HACS card; README is primary) |
| [entities.md](entities.md) | Entity categories, naming patterns, option gating |
| [automations.md](automations.md) | Services, `jullix_event`, example automations |
| [troubleshooting.md](troubleshooting.md) | Token errors, missing entities, Energy Dashboard, Jullix-Direct |
| [screenshots/README.md](screenshots/README.md) | UI capture guide for README images |

## Understand the integration

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | API client, coordinator, models, data flow |
| [features.md](features.md) | CORE / EXTENDED / EXPERIMENTAL fetch tiers and polling |
| [api.md](api.md) | Platform API path → client method mapping (contributors) |
| [CHANGELOG](../CHANGELOG.md) | Version history |

## Contribute

| Document | Description |
|----------|-------------|
| [CONTRIBUTING](../CONTRIBUTING.md) | Environment setup, tests, PR workflow |
| [development.md](development.md) | Project layout, add a sensor, extend the API |
| [tests/README](../tests/README.md) | Pytest commands, CI jobs, API fixtures |

## Maintain

| Document | Description |
|----------|-------------|
| [releasing.md](releasing.md) | Version bump, tag, GitHub Release, HACS |
| [hacs-publish.md](hacs-publish.md) | HACS default catalog checklist |
| [brands.md](brands.md) | Brand assets and Home Assistant Analytics |
| [REPO_SETUP](../.github/REPO_SETUP.md) | GitHub repository metadata for HACS validation |

## External resources

- [Jullix Wiki](https://wiki.jullix.be/doku.php?id=nl:start) (Dutch)
- [Integration FAQ](https://wiki.jullix.be/doku.php?id=nl:faq:integratie) (Dutch)
- [Platform API docs](https://mijn.jullix.be/apidocs/)
