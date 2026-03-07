"""Live API smoke tests (run only when JULLIX_API_TOKEN and JULLIX_INSTALLATION_ID are set).

In CI, add these GitHub secrets:
  - JULLIX_API_TOKEN: your Jullix API JWT token
  - JULLIX_INSTALLATION_ID: installation ID to test against

If either is missing, all tests in this module are skipped.
"""

from __future__ import annotations

import os

import pytest

# Skip entire module if secrets not set (e.g. fork or local run without env)
pytest.importorskip("aiohttp")
JULLIX_API_TOKEN = os.environ.get("JULLIX_API_TOKEN", "").strip()
JULLIX_INSTALLATION_ID = os.environ.get("JULLIX_INSTALLATION_ID", "").strip()
SKIP_LIVE = not JULLIX_API_TOKEN or not JULLIX_INSTALLATION_ID

pytestmark = pytest.mark.skipif(
    SKIP_LIVE,
    reason="JULLIX_API_TOKEN and JULLIX_INSTALLATION_ID must be set for live API tests",
)


@pytest.fixture
def api_client():
    """Real API client using env token."""
    from custom_components.jullix.api import JullixApiClient
    return JullixApiClient(api_token=JULLIX_API_TOKEN)


@pytest.fixture
def install_id():
    """Installation ID from env."""
    return JULLIX_INSTALLATION_ID


@pytest.mark.asyncio
async def test_get_installations_returns_list(api_client):
    """Live API: get_installations returns a non-empty list."""
    installations = await api_client.get_installations()
    assert isinstance(installations, list)
    assert len(installations) >= 1


@pytest.mark.asyncio
async def test_get_power_summary(api_client, install_id):
    """Live API: get_power_summary returns data for the installation."""
    data = await api_client.get_power_summary(install_id)
    assert data is not None


@pytest.mark.asyncio
async def test_get_chargers(api_client, install_id):
    """Live API: get_chargers returns a list (may be empty)."""
    chargers = await api_client.get_chargers(install_id)
    assert isinstance(chargers, list)


@pytest.mark.asyncio
async def test_get_plugs(api_client, install_id):
    """Live API: get_plugs returns a list (may be empty)."""
    plugs = await api_client.get_plugs(install_id)
    assert isinstance(plugs, list)


@pytest.mark.asyncio
async def test_get_actual_detail_charger(api_client, install_id):
    """Live API: get_actual_detail for charger returns data."""
    data = await api_client.get_actual_detail(install_id, "charger")
    assert data is not None


@pytest.mark.asyncio
async def test_close_session(api_client):
    """Live API: client can close without error."""
    await api_client.close()
