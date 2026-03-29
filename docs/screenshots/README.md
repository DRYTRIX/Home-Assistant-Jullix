# Screenshots for documentation

These images are used in the [README](../../README.md) and [info.md](../../info.md). Replace the **placeholder** PNGs in this folder with real Home Assistant UI captures when you can; keep filenames stable so markdown links keep working.

## Recommended assets

| File | Purpose | How to capture |
|------|---------|----------------|
| `setup-api-token.png` | Config flow: API token step | **Settings → Devices & services → Add integration → Jullix**; blur or crop the token. |
| `setup-installations.png` | Installation multi-select | Same flow, installations step. |
| `options-jullix.png` | Integration options | **Jullix → Configure**; show polling and toggles. |
| `dashboard-entities.png` | Entity card / device view | Lovelace **Entities** card or device page for a Jullix site. |
| `energy-dashboard.png` | Energy dashboard | HA **Energy** configuration using Jullix sensors (optional). |
| `hacs-preview.png` | HACS / marketing preview | Used in `info.md`; can match `dashboard-entities.png` or a branded hero image. |

## Guidelines

- **Resolution:** roughly 1200–1600 px wide for readability on GitHub; PNG or WebP.
- **Privacy:** blur addresses, tokens, map pins, and license plates if visible.
- **Consistency:** light or dark theme is fine; pick one style for a given doc pass.

## Placeholders

The repository may ship **minimal placeholder PNGs** so links do not 404. They are not representative of the UI—replace them for production-quality docs.
