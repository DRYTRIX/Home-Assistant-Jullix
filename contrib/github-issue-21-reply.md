Suggested reply for [issue #21](https://github.com/DRYTRIX/Home-Assistant-Jullix/issues/21) (battery energy follow-up):

---

Thanks for confirming v1.8.0 fixed the Configure / 500 error.

The missing **battery charged**, **battery discharged**, and cumulative energy sensors for the Energy Dashboard are addressed in the next release:

- **Energy charged** and **Energy discharged** sensors (`kWh`, `total_increasing`) are created per battery when Jullix exposes `energy_charged` / `energy_discharged`.
- **Local Jullix-Direct:** enable **Merge local Jullix-Direct data when configured** in integration options (and set a local host during setup). The local `/api/ems/battery` endpoint provides these totals.
- **Cloud-only:** today's battery energy history is fetched from the platform API as a fallback.

After upgrading, open **Settings → Dashboards → Energy** and map the new battery energy sensors to battery input/output.

**Battery power** (instantaneous) was already available via summary and per-battery Power sensors; the new entities are the cumulative kWh totals needed for the Energy Dashboard.

---
