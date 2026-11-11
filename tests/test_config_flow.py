"""Tests for Jullix config flow."""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("homeassistant")
if isinstance(sys.modules.get("homeassistant"), MagicMock):
    pytest.skip(
        "Config flow tests require real Home Assistant (install homeassistant)",
        allow_module_level=True,
    )

from homeassistant.data_entry_flow import FlowResultType

from custom_components.jullix.config_flow import (
    FlowTokenError,
    JullixConfigFlow,
    JullixOptionsFlowHandler,
    _validate_token,
    local_host_already_configured,
)
from custom_components.jullix.const import (
    CONF_API_TOKEN,
    CONF_INSTALL_IDS,
    CONF_LOCAL_HOST,
    OPTION_ENABLE_ADAPTIVE_POLLING,
    OPTION_ENABLE_CHARGER_CONTROL,
    OPTION_ENABLE_CHARGER_SESSION,
    OPTION_ENABLE_COST,
    OPTION_ENABLE_EVENTS,
    OPTION_ENABLE_INSIGHTS,
    OPTION_ENABLE_PLUG_CONTROL,
    OPTION_ENABLE_SESSION_HISTORY,
    OPTION_ENABLE_STATISTICS,
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
    flow._pending_token = None
    flow._token_flow_error = None
    flow._validate_task = None
    flow._discovered_host = None
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_abort = MagicMock(return_value={"type": "abort"})
    flow.async_show_progress = MagicMock(
        return_value={"type": FlowResultType.SHOW_PROGRESS, "progress_action": "x"}
    )
    # Record the coroutine only; tests await it directly (avoid double schedule vs asyncio.create_task).
    # Return a done task so async_step_validate_token can proceed past the in-flight check.
    done_task = MagicMock()
    done_task.done.return_value = True

    def _create_task(coro):
        return done_task

    flow.hass.async_create_task = MagicMock(side_effect=_create_task)
    return flow


async def _run_user_step_with_mocked_validation(flow, installations, side_effect=None):
    """Submit user step; run progress task; return validate_token step result."""
    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        side_effect=side_effect,
        return_value=installations,
    ):
        result = await flow.async_step_user({CONF_API_TOKEN: "token"})
        assert result.get("type") == FlowResultType.SHOW_PROGRESS
        flow.hass.async_create_task.assert_called_once()
        task = flow.hass.async_create_task.call_args[0][0]
        await task
        return await flow.async_step_validate_token(None)


async def _advance_progress_done(flow, result):
    """Follow a show_progress_done hand-off the way FlowManager would: call the
    next step with user_input=None."""
    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    return await getattr(flow, f"async_step_{result['step_id']}")(None)


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
    """Token validation with no installations shows no_installations."""
    flow = _make_flow()
    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        side_effect=FlowTokenError("no_installations"),
    ):
        result = await flow.async_step_user({CONF_API_TOKEN: "token"})
        assert result.get("type") == FlowResultType.SHOW_PROGRESS
        task = flow.hass.async_create_task.call_args[0][0]
        await task
        validate_result = await flow.async_step_validate_token(None)
        assert validate_result["type"] == FlowResultType.SHOW_PROGRESS_DONE
        assert validate_result["step_id"] == "user"
        await _advance_progress_done(flow, validate_result)
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "no_installations"}


@pytest.mark.asyncio
async def test_step_user_invalid_auth_shows_error():
    """Jullix auth failure maps to invalid_auth."""
    flow = _make_flow()
    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        side_effect=FlowTokenError("invalid_auth"),
    ):
        await flow.async_step_user({CONF_API_TOKEN: "bad"})
        task = flow.hass.async_create_task.call_args[0][0]
        await task
        validate_result = await flow.async_step_validate_token(None)
        await _advance_progress_done(flow, validate_result)
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_step_user_validation_shows_cannot_connect():
    """FlowTokenError cannot_connect shows on form."""
    flow = _make_flow()
    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        side_effect=FlowTokenError("cannot_connect"),
    ):
        await flow.async_step_user({CONF_API_TOKEN: "token"})
        task = flow.hass.async_create_task.call_args[0][0]
        await task
        validate_result = await flow.async_step_validate_token(None)
        await _advance_progress_done(flow, validate_result)
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_step_user_valid_token_multiple_goes_to_installations():
    """Multiple installations show installations picker after validation."""
    flow = _make_flow()
    installations = [
        {"id": "inst-1", "name": "Home"},
        {"id": "inst-2", "name": "Office"},
    ]
    result = await _run_user_step_with_mocked_validation(flow, installations)
    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == "installations"
    await _advance_progress_done(flow, result)
    flow.async_show_form.assert_called_once()
    assert flow.async_show_form.call_args[1]["step_id"] == "installations"
    assert flow.async_show_form.call_args[1]["description_placeholders"] == {
        "count": "2"
    }


@pytest.mark.asyncio
async def test_step_user_single_install_skips_to_local():
    """Single installation skips picker and opens local step."""
    flow = _make_flow()
    installations = [{"id": "inst-1", "name": "Home"}]
    result = await _run_user_step_with_mocked_validation(flow, installations)
    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == "local"
    assert flow._config == {
        CONF_API_TOKEN: flow._api_token,
        CONF_INSTALL_IDS: ["inst-1"],
    }
    await _advance_progress_done(flow, result)
    kw = flow.async_show_form.call_args[1]
    assert kw["step_id"] == "local"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("token_flow_error", "installations", "expected_next_step_id"),
    [
        ("invalid_auth", [], "user"),
        (None, [], "user"),  # completed with empty list -> no_installations
        (None, [{"id": ""}], "user"),
        (None, [{"id": "inst-1", "name": "Home"}], "local"),
        (None, [{"id": "inst-1"}, {"id": "inst-2"}], "installations"),
    ],
)
async def test_async_step_validate_token_never_returns_form(
    token_flow_error, installations, expected_next_step_id
):
    """async_step_validate_token must not return a form.

    Home Assistant requires show_progress or show_progress_done from this
    step - returning a form raises ValueError in the progress done-callback.
    """
    flow = _make_flow()
    flow._token_flow_error = token_flow_error
    flow._installations = installations
    flow._api_token = "token"
    # Treat task as finished so we exercise the post-validation branches.
    done_task = MagicMock()
    done_task.done.return_value = True
    flow._validate_task = done_task
    result = await flow.async_step_validate_token(None)
    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == expected_next_step_id
    if token_flow_error is None and not installations:
        assert flow._token_flow_error == "no_installations"


@pytest.mark.asyncio
async def test_async_step_validate_token_keeps_progress_while_task_running():
    """While the validate task is in flight, keep showing progress (issue #37)."""
    flow = _make_flow()
    pending_task = MagicMock()
    pending_task.done.return_value = False
    flow._validate_task = pending_task
    flow._installations = []
    flow._token_flow_error = None

    result = await flow.async_step_validate_token(None)

    assert result["type"] == FlowResultType.SHOW_PROGRESS
    flow.async_show_progress.assert_called_with(
        step_id="validate_token",
        progress_action="validate_token",
        progress_task=pending_task,
    )


@pytest.mark.asyncio
async def test_async_validate_token_task_cancelled_sets_error():
    """Cancelled validation must not leave an empty installations picker."""
    flow = _make_flow()
    flow._pending_token = "token"

    async def _raise_cancelled(*_args, **_kwargs):
        raise asyncio.CancelledError()

    with patch(
        "custom_components.jullix.config_flow._validate_token",
        new_callable=AsyncMock,
        side_effect=_raise_cancelled,
    ):
        await flow._async_validate_token_task()

    assert flow._token_flow_error == "cannot_connect"
    assert flow._installations == []


@pytest.mark.asyncio
async def test_step_installations_no_input_shows_form():
    """async_step_installations with no input shows installations form."""
    flow = _make_flow()
    flow._installations = [{"id": "i1", "name": "Inst 1"}]
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    await flow.async_step_installations(None)
    flow.async_show_form.assert_called_once()
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["step_id"] == "installations"
    assert call_kw["description_placeholders"] == {"count": "1"}


@pytest.mark.asyncio
async def test_step_installations_empty_selection_error():
    """Empty multi-select shows no_installations_selected."""
    flow = _make_flow()
    flow._installations = [{"id": "i1", "name": "Inst 1"}]
    flow._api_token = "token"
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    await flow.async_step_installations({CONF_INSTALL_IDS: []})
    call_kw = flow.async_show_form.call_args[1]
    assert call_kw["errors"] == {"base": "no_installations_selected"}


@pytest.mark.asyncio
async def test_step_installations_with_selection_goes_to_local():
    """async_step_installations with selection proceeds to local step."""
    flow = _make_flow()
    flow._installations = [{"id": "i1", "name": "Inst 1"}]
    flow._api_token = "token"
    result = await flow.async_step_installations({CONF_INSTALL_IDS: ["i1"]})
    assert result["type"] == "form"
    assert flow.async_show_form.call_args[1]["step_id"] == "local"


@pytest.mark.asyncio
async def test_step_local_skip_creates_entry_with_title():
    """async_step_local with empty local host creates entry without local."""
    flow = _make_flow()
    flow._installations = [{"id": "i1", "name": "Cottage"}]
    flow._config = {CONF_API_TOKEN: "token", CONF_INSTALL_IDS: ["i1"]}
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    await flow.async_step_local({CONF_LOCAL_HOST: ""})
    flow.async_create_entry.assert_called_once()
    call_args = flow.async_create_entry.call_args[1]
    assert call_args["title"] == "Jullix – Cottage"
    assert call_args["data"][CONF_LOCAL_HOST] is None
    assert call_args["options"][OPTION_USE_LOCAL] is False
    assert call_args["options"][OPTION_SCAN_INTERVAL] == 60
    assert call_args["options"][OPTION_ENABLE_INSIGHTS] is True
    assert call_args["options"][OPTION_ENABLE_EVENTS] is True


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
    flow._installations = [{"id": "i1", "name": "A"}, {"id": "i2", "name": "B"}]
    flow._config = {CONF_API_TOKEN: "token", CONF_INSTALL_IDS: ["i1", "i2"]}
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
    assert call_args["title"] == "Jullix (2 sites)"
    assert call_args["data"][CONF_LOCAL_HOST] == "jullix.local"
    assert call_args["options"][OPTION_USE_LOCAL] is True


def test_async_get_options_flow_constructs_handler_without_args():
    """async_get_options_flow must not pass config_entry into the constructor.

    Home Assistant 2025.12 made OptionsFlow.config_entry a read-only property
    supplied by the base class; constructing the handler with a positional
    config_entry argument now raises instead of being silently accepted.
    Regression test for https://github.com/DRYTRIX/Home-Assistant-Jullix/issues/21.
    """
    config_entry = MagicMock()
    handler = JullixConfigFlow.async_get_options_flow(config_entry)
    assert isinstance(handler, JullixOptionsFlowHandler)


@pytest.mark.asyncio
async def test_options_flow_init_shows_form():
    """Options flow init step shows form with current options."""
    config_entry = MagicMock()
    config_entry.options = {
        OPTION_SCAN_INTERVAL: 90,
        OPTION_ENABLE_COST: True,
        OPTION_ENABLE_STATISTICS: False,
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
        OPTION_ENABLE_STATISTICS: True,
        OPTION_ENABLE_CHARGER_CONTROL: True,
        OPTION_ENABLE_PLUG_CONTROL: True,
        OPTION_USE_LOCAL: False,
        OPTION_ENABLE_INSIGHTS: True,
        OPTION_ENABLE_EVENTS: True,
        OPTION_ENABLE_ADAPTIVE_POLLING: False,
        OPTION_ENABLE_CHARGER_SESSION: True,
        OPTION_ENABLE_SESSION_HISTORY: False,
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
async def test_step_zeroconf_jullix_sets_host_and_user_form():
    """Zeroconf discovery with jullix in hostname continues to user step."""
    flow = _make_flow()
    info = MagicMock()
    info.host = "192.168.1.50"
    info.hostname = "jullix.local."
    info.name = "Jullix"
    result = await flow.async_step_zeroconf(info)
    assert flow._discovered_host == "192.168.1.50"
    assert result["type"] == "form"
    flow.async_set_unique_id.assert_called_once()
    flow._abort_if_unique_id_configured.assert_called_once()


@pytest.mark.asyncio
async def test_step_zeroconf_aborts_when_already_configured():
    """Zeroconf aborts immediately when a Jullix entry already exists."""
    flow = _make_flow()
    flow._async_current_entries = MagicMock(return_value=[MagicMock()])
    info = MagicMock()
    info.host = "192.168.1.50"
    info.hostname = "jullix.local."
    info.name = "Jullix"
    result = await flow.async_step_zeroconf(info)
    assert result["type"] == "abort"
    flow.async_abort.assert_called_once_with(reason="already_configured")
    flow.async_set_unique_id.assert_not_called()


@pytest.mark.asyncio
async def test_step_zeroconf_non_jullix_aborts():
    """Zeroconf without jullix in host or name aborts."""
    flow = _make_flow()
    info = MagicMock()
    info.host = "192.168.1.1"
    info.hostname = "router.local."
    info.name = "router"
    result = await flow.async_step_zeroconf(info)
    assert result["type"] == "abort"
    flow.async_abort.assert_called_once_with(reason="not_jullix")


def test_local_host_already_configured_matches_hostname():
    """local_host_already_configured matches normalized hostname."""
    entry = MagicMock()
    entry.data = {CONF_LOCAL_HOST: "Jullix.local."}
    assert local_host_already_configured(
        [entry], "192.168.1.50", "jullix.local."
    )
    assert not local_host_already_configured(
        [entry], "192.168.1.50", "other.local."
    )


@pytest.mark.asyncio
async def test_validate_token_empty_raises_flow_error():
    """_validate_token raises FlowTokenError when API returns empty list."""
    with patch(
        "custom_components.jullix.config_flow.JullixApiClient",
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_installations = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client
        with pytest.raises(FlowTokenError) as exc_info:
            await _validate_token(MagicMock(), "token")
        assert exc_info.value.key == "no_installations"
