# Screenshots for documentation

These images are used in the [README](../../README.md) and [info.md](../../info.md). When updating docs, overwrite PNGs in this folder with fresh Home Assistant UI captures and keep filenames stable so markdown links keep working.

All four files below are committed and referenced from the README.

## Current assets

| File | Purpose | How to capture |
|------|---------|----------------|
| `setup-api-token.png` | Config flow: API token step | **Settings → Devices & services → Add integration → Jullix**; blur or crop the token. |
| `setup-installations.png` | Installation multi-select | Same flow, installations step. |
| `options-jullix.png` | Integration options | **Jullix → Configure**; show polling and toggles. |
| `energy-dashboard.png` | Energy dashboard | HA **Energy** configuration using Jullix sensors (include battery charged/discharged mapping when possible). |

## Guidelines

- **Resolution:** roughly 1200–1600 px wide for readability on GitHub; PNG or WebP.
- **Privacy:** blur addresses, tokens, map pins, and license plates if visible.
- **Consistency:** light or dark theme is fine; pick one style for a given doc pass.

## Updating images

1. Capture screenshots following the table above.
2. Overwrite the matching filename in this folder.
3. Confirm README and info.md still link to the same filenames.
