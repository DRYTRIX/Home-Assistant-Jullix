# Contributing to HACS-Jullix

## Development setup

1. Clone the repo and open it in your editor.
2. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   # or: .venv\Scripts\activate  # Windows
   ```
3. Install test dependencies:
   ```bash
   pip install -r requirements-test.txt
   ```

## Running tests

From the repo root:

```bash
python -m pytest tests/ -v --tb=short
```

- **Unit tests** (API, coordinator, sensor helpers, services, switch helpers) run with mocked Home Assistant. No secrets required.
- **Config flow** and **entity platform** tests are skipped when Home Assistant is not installed; install `homeassistant>=2024.1.0` (e.g. via `requirements-test.txt`) to run them.
- **Live API tests** (`tests/test_live_api.py`) are skipped unless environment variables are set (see below).

### Live API tests (optional)

To run the live API smoke tests locally or in CI:

1. Set `JULLIX_API_TOKEN` to your Jullix API JWT (from Mijn Jullix → Profiel → API-tokens).
2. Set `JULLIX_INSTALLATION_ID` to an installation ID you have access to.

Example (Linux/macOS):

```bash
export JULLIX_API_TOKEN="your-jwt"
export JULLIX_INSTALLATION_ID="your-install-id"
python -m pytest tests/test_live_api.py -v
```

In GitHub Actions, add these as repository secrets (**Settings → Secrets and variables → Actions**) so the workflow can run the live API job when desired.

## Code style

- Use the same style as the existing code (Black-style formatting, type hints where helpful).
- Optional: run `mypy custom_components/jullix --ignore-missing-imports` to check types (see `.github/workflows/test.yml`).

## Submitting changes

Open a pull request against `main`. The CI workflow will run unit tests (and live API tests if secrets are configured).
