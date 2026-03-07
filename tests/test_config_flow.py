"""Tests for Jullix config flow."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("homeassistant")
# Skip when HA is mocked (not installed); flow tests need real ConfigFlow
if isinstance(sys.modules.get("homeassistant"), MagicMock):
    pytest.skip(
        "Config flow tests require real Home Assistant (install homeassistant)",
        allow_module_level=True,
    )

from custom_components.jullix.config_flow import (
    JullixConfigFlow,
    JullixOptionsFlowHandler,
    _validate_token,
)
from custom_components.jullix.const import (
    CONF_API_TOKEN,
    CONF_INSTALL_IDS,
    CONF_LOCAL_HOST,
    OPTION_ENABLE_CHARGER_CONTROL,
    OPTION_ENABLE_COST,
    OPTION_ENABLE_PLUG_CONTROL,
    OPTION_SCAN_INTERVAL,
    OPTION_USE_LOCAL,
)


def _make_flow():
    """Create a JullixConfigFlow instance (using __new__ to avoid ConfigFlow manager init)."""
    flow = JullixConfigFlow.__new__(JullixConfigFlow)
    flow.hass = MagicMock()
    flow._installations = []
    flow._api_token = None
    flow._config = {}
    # HA ConfigFlow.async_show_form and async_create_entry are sync and return a dict
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_step_installations = AsyncMock(return_value={"type": "form", "step_id": "installations"})
    flow.async_step_local = AsyncMock(return_value={"type": "form", "step_id": "local"})
    return flow


@pytest.mark.asyncio
async def test_step_user_no_input_shows_form():
    """async_step_user with no input shows user form."""
    flow = _make_flow()
    result = await flow.async_step_user(None)
    assert result["type"] == "form"
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["step_id"] == "user"
    assert "data_schema" in call_kw


@pytest.mark.asyncio
async def test_step_user_empty_token_shows_error():
    """async_step_user with empty token shows invalid_token error."""
    flow = _make_flow()
    await flow.async_step_user({CONF_API_TOKEN: "   "})
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "invalid_token"}


@pytest.mark.asyncio
async def test_step_user_no_installations_shows_error():
    """async_step_user when API returns no installations shows no_installations."""
    flow = _make_flow()
    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        side_effect=ValueError("no_installations"),
    ):
        await flow.async_step_user({CONF_API_TOKEN: "token"})
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "no_installations"}


@pytest.mark.asyncio
async def test_step_user_validation_exception_shows_cannot_connect():
    """async_step_user when validation raises generic Exception shows cannot_connect."""
    flow = _make_flow()
    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        side_effect=Exception("network error"),
    ):
        await flow.async_step_user({CONF_API_TOKEN: "token"})
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_step_user_valid_token_goes_to_installations():
    """async_step_user with valid token proceeds to installations step."""
    flow = _make_flow()
    installations = [{"id": "inst-1", "name": "Home"}]
    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        return_value=installations,
    ):
        result = await flow.async_step_user({CONF_API_TOKEN: "token"})
    flow.async_step_installations.assert_called_once()
    assert result == {"type": "form", "step_id": "installations"}


@pytest.mark.asyncio
async def test_step_installations_no_input_shows_form():
    """async_step_installations with no input shows installations form."""
    flow = _make_flow()
    flow._installations = [{"id": "i1", "name": "Inst 1"}]
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    result = await flow.async_step_installations(None)
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["step_id"] == "installations"
    assert "data_schema" in call_kw


@pytest.mark.asyncio
async def test_step_installations_with_selection_goes_to_local():
    """async_step_installations with selection proceeds to local step."""
    flow = _make_flow()
    flow._installations = [{"id": "i1", "name": "Inst 1"}]
    flow._api_token = "token"
    flow.async_step_local = AsyncMock(return_value={"type": "form", "step_id": "local"})
    result = await flow.async_step_installations({CONF_INSTALL_IDS: ["i1"]})
    flow.async_step_local.assert_called_once()
    call_args = flow.async_step_local.call_args[0][0]
    assert call_args == {CONF_API_TOKEN: "token", CONF_INSTALL_IDS: ["i1"]}


@pytest.mark.asyncio
async def test_step_local_skip_creates_entry():
    """async_step_local with empty local host creates entry without local."""
    flow = _make_flow()
    flow._config = {CONF_API_TOKEN: "token", CONF_INSTALL_IDS: ["i1"]}
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    await flow.async_step_local({CONF_LOCAL_HOST: ""})
    flow.async_create_entry.assert_called_once()
    call_args = flow.async_create_entry.call_args[1]
    assert call_args["data"][CONF_LOCAL_HOST] is None
    assert call_args["options"][OPTION_USE_LOCAL] is False
    assert call_args["options"][OPTION_SCAN_INTERVAL] == 60


@pytest.mark.asyncio
async def test_step_local_connection_failed_shows_error():
    """async_step_local when local test_connection fails shows local_connection_failed."""
    flow = _make_flow()
    flow._config = {CONF_API_TOKEN: "token", CONF_INSTALL_IDS: ["i1"]}
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    with patch(
        "custom_components.jullix.local_client.JullixLocalClient",
    ) as mock_local_class:
        mock_client = MagicMock()
        mock_client.test_connection = AsyncMock(side_effect=ConnectionError("refused"))
        mock_local_class.return_value = mock_client
        await flow.async_step_local({CONF_LOCAL_HOST: "jullix.local"})
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "local_connection_failed"}


@pytest.mark.asyncio
async def test_step_local_connection_ok_creates_entry_with_local():
    """async_step_local when local test_connection succeeds creates entry with use_local."""
    flow = _make_flow()
    flow._config = {CONF_API_TOKEN: "token", CONF_INSTALL_IDS: ["i1"]}
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    with patch(
        "custom_components.jullix.local_client.JullixLocalClient",
    ) as mock_local_class:
        mock_client = MagicMock()
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_local_class.return_value = mock_client
        await flow.async_step_local({CONF_LOCAL_HOST: "jullix.local"})
    flow.async_create_entry.assert_called_once()
    call_args = flow.async_create_entry.call_args[1]
    assert call_args["data"][CONF_LOCAL_HOST] == "jullix.local"
    assert call_args["options"][OPTION_USE_LOCAL] is True


@pytest.mark.asyncio
async def test_options_flow_init_shows_form():
    """Options flow init step shows form with current options."""
    config_entry = MagicMock()
    config_entry.options = {
        OPTION_SCAN_INTERVAL: 90,
        OPTION_ENABLE_COST: True,
        OPTION_ENABLE_CHARGER_CONTROL: True,
        OPTION_ENABLE_PLUG_CONTROL: False,
        OPTION_USE_LOCAL: True,
    }
    handler = JullixOptionsFlowHandler.__new__(JullixOptionsFlowHandler)
    handler.hass = MagicMock()
    handler.async_show_form = MagicMock(return_value={"type": "form"})
    handler.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    with patch.object(
        JullixOptionsFlowHandler, "config_entry", property(lambda self: config_entry)
    ):
        result = await handler.async_step_init(None)
    handler.async_show_form.assert_called_once()
    call_kw = handler.async_show_form.call_args[1]
    assert call_kw["step_id"] == "init"
    assert "data_schema" in call_kw


@pytest.mark.asyncio
async def test_options_flow_submit_creates_entry():
    """Options flow submit creates entry with new options."""
    config_entry = MagicMock()
    config_entry.options = {}
    handler = JullixOptionsFlowHandler.__new__(JullixOptionsFlowHandler)
    handler.hass = MagicMock()
    handler.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    user_input = {
        OPTION_SCAN_INTERVAL: 120,
        OPTION_ENABLE_COST: False,
        OPTION_ENABLE_CHARGER_CONTROL: True,
        OPTION_ENABLE_PLUG_CONTROL: True,
        OPTION_USE_LOCAL: False,
    }
    with patch.object(
        JullixOptionsFlowHandler, "config_entry", property(lambda self: config_entry)
    ):
        await handler.async_step_init(user_input)
    handler.async_create_entry.assert_called_once_with(data=user_input)


@pytest.mark.asyncio
async def test_validate_token_success():
    """_validate_token returns installations when API returns data."""
    with patch(
        "custom_components.jullix.config_flow.JullixApiClient",
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_installations = AsyncMock(
            return_value=[{"id": "i1", "name": "Home"}]
        )
        mock_client_class.return_value = mock_client
        result = await _validate_token(MagicMock(), "token")
    assert result == [{"id": "i1", "name": "Home"}]


@pytest.mark.asyncio
async def test_validate_token_empty_raises():
    """_validate_token raises ValueError when API returns empty list."""
    with patch(
        "custom_components.jullix.config_flow.JullixApiClient",
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_installations = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client
        with pytest.raises(ValueError, match="no_installations"):
            await _validate_token(MagicMock(), "token")