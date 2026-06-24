# Brand images and Home Assistant Analytics

Jullix ships brand assets in two places:

1. **Integration bundle (HA 2026.3+)** — [`custom_components/jullix/brand/`](../custom_components/jullix/brand/) (`icon.png`, `logo.png`). These are served via the Home Assistant brands proxy when the integration is loaded.
2. **Upstream brands repo (Analytics + CDN)** — Copy-ready files in [`contrib/home-assistant-brands/jullix/`](../contrib/home-assistant-brands/jullix/) for a PR to [home-assistant/brands](https://github.com/home-assistant/brands).

## Submit to home-assistant/brands

Public install counts in [Home Assistant Analytics](https://analytics.home-assistant.io/) require the integration domain to appear in `custom_integrations.json`. That listing depends on a merged brands entry and opt-in **Usage analytics** on user instances.

1. Fork [home-assistant/brands](https://github.com/home-assistant/brands).
2. Copy `contrib/home-assistant-brands/jullix/*` into `custom_integrations/jullix/` in your fork.
3. Open a PR with title e.g. `Add Jullix custom integration brand`.
4. After merge, wait until `jullix` shows up at `https://analytics.home-assistant.io/custom_integrations.json`.

Domain must match [`manifest.json`](../custom_components/jullix/manifest.json): `jullix`.

## Install count badges (after Analytics lists `jullix`)

When the domain is listed, you can add a Shields badge to the README using the public JSON feed, for example:

```markdown
![Home Assistant installs](https://img.shields.io/endpoint?url=https://vaskivskyi.github.io/ha-custom-analytics/badges/jullix/total.json)
```

Alternatively, use the [Analytics Insights](https://www.home-assistant.io/integrations/analytics_insights/) integration on your own Home Assistant instance.

**Note:** Counts are aggregated, opt-in only, and under-report installations that disable analytics or never load the integration.

## Regenerating assets

Brand PNGs were generated from the Jullix portal favicon. To refresh:

```bash
curl -sL "https://mijn.jullix.be/favicon.ico" -o /tmp/jullix-favicon.ico
# Then run the Pillow resize script in the integration repo (see git history) or replace files manually.
```

Replace `docs/screenshots/*.png` with real UI captures when available; placeholders do not affect brands or analytics.
