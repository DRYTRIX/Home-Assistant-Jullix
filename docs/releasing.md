# Release process

This project follows [Semantic Versioning](https://semver.org/) and documents changes in [`CHANGELOG.md`](../CHANGELOG.md) using [Keep a Changelog](https://keepachangelog.com/) conventions.

## Steps for maintainers

1. **Finalize `CHANGELOG.md`**
   - Move items from **`[Unreleased]`** into a new section **`[X.Y.Z]`** with the version you are about to ship.
   - Add release date (ISO `YYYY-MM-DD`) next to the version heading if you want dated history.

2. **Bump version in manifest**
   - Set **`version`** in [`custom_components/jullix/manifest.json`](../custom_components/jullix/manifest.json) to **`X.Y.Z`** (must match the release).

3. **Commit**
   - Commit message example: `Release 1.6.2` (include changelog + manifest in the same commit).

4. **Tag**
   - Create an annotated or lightweight Git tag: `vX.Y.Z` (HACS and GitHub releases commonly use this prefix).
   - Example: `git tag v1.6.2 && git push origin v1.6.2`

5. **GitHub Release**
   - On GitHub: **Releases → Draft a new release**, choose tag `vX.Y.Z`, title `vX.Y.Z` or `Jullix X.Y.Z`.
   - Paste the **`CHANGELOG.md`** section for that version into the release description (users and HACS consumers see this).

6. **HACS**
   - Default HACS tracks the repository; new tags are picked up as updates after users refresh HACS or wait for the periodic check.
   - No separate HACS store upload is required for custom repositories.

## Pre-release checklist

- [ ] `CHANGELOG.md` updated; no stray empty `[Unreleased]` sections unless intentionally empty.
- [ ] `manifest.json` `version` matches the tag (without `v` prefix in the file).
- [ ] CI green on the release branch (`Test` workflow).
- [ ] Optional: run full pytest locally with `requirements-test.txt`.

## Version semantics (short)

- **MAJOR** — Breaking changes for users (rare for integrations; e.g. removed entities or required HA version jump with migration).
- **MINOR** — New features, new entities, or meaningful behavior additions.
- **PATCH** — Bug fixes, docs-only releases that affect packaging, small corrections.
