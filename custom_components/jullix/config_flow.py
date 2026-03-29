"""Config flow for Jullix integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import JullixApiClient, JullixApiError, JullixAuthError
from .const import (
    CONF_API_TOKEN,
    CONF_INSTALL_IDS,
    CONF_LOCAL_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
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

_LOGGER = logging.getLogger(__name__)


class FlowTokenError(Exception):
    """Token validation failed with a flow error key (see .key)."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


async def _validate_token(hass: HomeAssistant, token: str) -> list[dict[str, Any]]:
    """Validate API token and return installations."""
    client = JullixApiClient(token)
    try:
        installations = await client.get_installations()
    except JullixAuthError as err:
        _LOGGER.debug("Jullix auth error during token validation: %s", err)
        raise FlowTokenError("invalid_auth") from err
    except JullixApiError as err:
        _LOGGER.debug("Jullix API error during token validation: %s", err)
        raise FlowTokenError("cannot_connect") from err
    except Exception as err:
        _LOGGER.exception("Token validation failed: %s", err)
        raise FlowTokenError("cannot_connect") from err
    if not installations:
        raise FlowTokenError("no_installations")
    return installations


def _build_entry_title(
    install_ids: list[str], installations: list[dict[str, Any]]
) -> str:
    """Human-readable config entry title."""
    id_to_name: dict[str, str] = {}
    for inst in installations:
        iid = str(inst.get("id", inst.get("install_id", "")))
        if iid:
            id_to_name[iid] = str(inst.get("name", iid))
    names = [id_to_name.get(iid, iid) for iid in install_ids]
    if len(names) == 1:
        return f"Jullix – {names[0]}"
    return f"Jullix ({len(names)} sites)"


def _default_options() -> dict[str, Any]:
    """Options for new config entries."""
    return {
        OPTION_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        OPTION_ENABLE_COST: False,
        OPTION_ENABLE_STATISTICS: False,
        OPTION_ENABLE_CHARGER_CONTROL: True,
        OPTION_ENABLE_PLUG_CONTROL: True,
        OPTION_USE_LOCAL: False,
        OPTION_ENABLE_INSIGHTS: True,
        OPTION_ENABLE_EVENTS: True,
        OPTION_ENABLE_ADAPTIVE_POLLING: False,
        OPTION_ENABLE_CHARGER_SESSION: True,
        OPTION_ENABLE_SESSION_HISTORY: False,
    }


class JullixConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jullix."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> JullixOptionsFlowHandler:
        """Get the options flow for this handler."""
        return JullixOptionsFlowHandler(config_entry)

    def __init__(self) -> None:
        """Initialize config flow."""
        self._installations: list[dict[str, Any]] = []
        self._api_token: str | None = None
        self._config: dict[str, Any] = {}
        self._pending_token: str | None = None
        self._token_flow_error: str | None = None
        self._discovered_host: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Discovered Jullix-Direct HTTP service; pre-fill local host after login."""
        host = discovery_info.host
        if not host:
            return self.async_abort(reason="cannot_connect")
        hn = discovery_info.hostname.rstrip(".").lower()
        name_l = (discovery_info.name or "").lower()
        if "jullix" not in hn and "jullix" not in name_l:
            return self.async_abort(reason="not_jullix")
        await self.async_set_unique_id(f"zeroconf_{host}", raise_on_progress=False)
        self._abort_if_unique_id_configured()
        self._discovered_host = host
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input.get(CONF_API_TOKEN, "").strip()
            if not token:
                errors["base"] = "invalid_token"
            else:
                self._pending_token = token
                return self.async_show_progress(
                    step_id="validate_token",
                    progress_action="validate_token",
                    progress_task=self.hass.async_create_task(
                        self._async_validate_token_task()
                    ),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def _async_validate_token_task(self) -> None:
        """Run token validation (progress task)."""
        assert self._pending_token is not None
        try:
            self._installations = await _validate_token(
                self.hass, self._pending_token
            )
            self._api_token = self._pending_token
            self._token_flow_error = None
        except FlowTokenError as err:
            self._token_flow_error = err.key
            self._installations = []

    async def async_step_validate_token(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Continue after token validation progress completes."""
        if self._token_flow_error:
            err = self._token_flow_error
            self._token_flow_error = None
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CONF_API_TOKEN): str},
                ),
                errors={"base": err},
            )

        n = len(self._installations)
        if n == 1:
            inst = self._installations[0]
            iid = str(inst.get("id", inst.get("install_id", "")))
            if not iid:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {vol.Required(CONF_API_TOKEN): str},
                    ),
                    errors={"base": "cannot_connect"},
                )
            return await self.async_step_local(
                {
                    CONF_API_TOKEN: self._api_token,
                    CONF_INSTALL_IDS: [iid],
                }
            )

        install_options = {
            str(inst.get("id", inst.get("install_id", ""))): inst.get(
                "name", f"Installation {inst.get('id', '?')}"
            )
            for inst in self._installations
        }

        return self.async_show_form(
            step_id="installations",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INSTALL_IDS): cv.multi_select(install_options),
                }
            ),
            description_placeholders={"count": str(n)},
        )

    async def async_step_installations(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which installations to add."""
        errors: dict[str, str] = {}

        if user_input is not None:
            install_ids = user_input.get(CONF_INSTALL_IDS, [])
            if not install_ids:
                errors["base"] = "no_installations_selected"
            else:
                return await self.async_step_local(
                    {CONF_API_TOKEN: self._api_token, CONF_INSTALL_IDS: install_ids}
                )

        install_options = {
            str(inst.get("id", inst.get("install_id", ""))): inst.get(
                "name", f"Installation {inst.get('id', '?')}"
            )
            for inst in self._installations
        }

        return self.async_show_form(
            step_id="installations",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INSTALL_IDS): cv.multi_select(install_options),
                }
            ),
            description_placeholders={"count": str(len(self._installations))},
            errors=errors,
        )

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Optional: configure local Jullix-Direct host."""
        if user_input is not None and CONF_INSTALL_IDS in user_input:
            self._config = user_input
            return self.async_show_form(
                step_id="local",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_LOCAL_HOST,
                            default=(self._discovered_host or ""),
                        ): str,
                    }
                ),
            )

        if user_input is not None:
            data = {**self._config, **user_input}
            local_host = (user_input.get(CONF_LOCAL_HOST) or "").strip()
            title = _build_entry_title(
                data[CONF_INSTALL_IDS], self._installations
            )

            if not local_host:
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_API_TOKEN: data[CONF_API_TOKEN],
                        CONF_INSTALL_IDS: data[CONF_INSTALL_IDS],
                        CONF_LOCAL_HOST: None,
                    },
                    options=_default_options(),
                )

            try:
                from .local_client import JullixLocalClient

                client = JullixLocalClient(local_host)
                await client.test_connection()
            except Exception as exc:
                _LOGGER.debug("Local connection test failed: %s", exc)
                return self.async_show_form(
                    step_id="local",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(CONF_LOCAL_HOST, default=local_host): str,
                        }
                    ),
                    errors={"base": "local_connection_failed"},
                )

            return self.async_create_entry(
                title=title,
                data={
                    CONF_API_TOKEN: data[CONF_API_TOKEN],
                    CONF_INSTALL_IDS: data[CONF_INSTALL_IDS],
                    CONF_LOCAL_HOST: local_host,
                },
                options={**_default_options(), OPTION_USE_LOCAL: True},
            )

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_LOCAL_HOST,
                        default=(self._discovered_host or ""),
                    ): str,
                }
            ),
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth when API token is invalid or expired."""
        return await self._async_reauth_show_form(user_input)

    async def _async_reauth_show_form(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> FlowResult:
        """Show reauth form for new API token."""
        errors = errors or {}
        if user_input is not None:
            token = (user_input.get(CONF_API_TOKEN) or "").strip()
            if not token:
                errors["base"] = "invalid_token"
            else:
                try:
                    await _validate_token(self.hass, token)
                    entry = self.hass.config_entries.async_get_entry(
                        self.context["entry_id"]
                    )
                    if entry:
                        self.hass.config_entries.async_update_entry(
                            entry,
                            data={**entry.data, CONF_API_TOKEN: token},
                        )
                        self.hass.async_create_task(
                            self.hass.config_entries.async_reload(entry.entry_id)
                        )
                        return self.async_abort(reason="reauth_successful")
                    errors["base"] = "cannot_connect"
                except FlowTokenError as err:
                    errors["base"] = err.key

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): str}),
            errors=errors,
            description_placeholders={"entry_id": self.context.get("entry_id", "")},
        )


class JullixOptionsFlowHandler(OptionsFlow):
    """Handle Jullix options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            result = self.async_create_entry(data=user_input)
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )
            return result

        options = self.config_entry.options or {}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        OPTION_SCAN_INTERVAL,
                        default=options.get(OPTION_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
                    vol.Required(
                        OPTION_ENABLE_COST,
                        default=options.get(OPTION_ENABLE_COST, False),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_STATISTICS,
                        default=options.get(OPTION_ENABLE_STATISTICS, False),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_CHARGER_CONTROL,
                        default=options.get(OPTION_ENABLE_CHARGER_CONTROL, True),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_PLUG_CONTROL,
                        default=options.get(OPTION_ENABLE_PLUG_CONTROL, True),
                    ): bool,
                    vol.Required(
                        OPTION_USE_LOCAL,
                        default=options.get(OPTION_USE_LOCAL, False),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_INSIGHTS,
                        default=options.get(OPTION_ENABLE_INSIGHTS, True),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_EVENTS,
                        default=options.get(OPTION_ENABLE_EVENTS, True),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_ADAPTIVE_POLLING,
                        default=options.get(OPTION_ENABLE_ADAPTIVE_POLLING, False),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_CHARGER_SESSION,
                        default=options.get(OPTION_ENABLE_CHARGER_SESSION, True),
                    ): bool,
                    vol.Required(
                        OPTION_ENABLE_SESSION_HISTORY,
                        default=options.get(OPTION_ENABLE_SESSION_HISTORY, False),
                    ): bool,
                }
            ),
        )
