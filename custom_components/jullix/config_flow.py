"""Config flow for Jullix integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .api import JullixApiClient
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_API_TOKEN,
    CONF_INSTALL_IDS,
    CONF_LOCAL_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OPTION_ENABLE_CHARGER_CONTROL,
    OPTION_ENABLE_COST,
    OPTION_ENABLE_PLUG_CONTROL,
    OPTION_SCAN_INTERVAL,
    OPTION_USE_LOCAL,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_token(hass: HomeAssistant, token: str) -> list[dict[str, Any]]:
    """Validate API token and return installations."""
    client = JullixApiClient(token)
    installations = await client.get_installations()
    if not installations:
        raise ValueError("no_installations")
    return installations


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
                try:
                    self._installations = await _validate_token(self.hass, token)
                    self._api_token = token
                    return await self.async_step_installations()
                except ValueError as err:
                    if str(err) == "no_installations":
                        errors["base"] = "no_installations"
                    else:
                        errors["base"] = "invalid_token"
                except Exception as exc:
                    _LOGGER.exception("Token validation failed: %s", exc)
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_installations(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which installations to add."""
        if user_input is not None:
            install_ids = user_input.get(CONF_INSTALL_IDS, [])
            if install_ids:
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
        )

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Optional: configure local Jullix-Direct host."""
        # Coming from installations step: store config and show form
        if user_input is not None and CONF_INSTALL_IDS in user_input:
            self._config = user_input
            return self.async_show_form(
                step_id="local",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_LOCAL_HOST, default=""): str,
                    }
                ),
            )

        # User submitted local form
        if user_input is not None:
            data = {**self._config, **user_input}
            local_host = (user_input.get(CONF_LOCAL_HOST) or "").strip()

            if not local_host:
                return self.async_create_entry(
                    title="Jullix",
                    data={
                        CONF_API_TOKEN: data[CONF_API_TOKEN],
                        CONF_INSTALL_IDS: data[CONF_INSTALL_IDS],
                        CONF_LOCAL_HOST: None,
                    },
                    options={
                        OPTION_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                        OPTION_ENABLE_COST: False,
                        OPTION_ENABLE_CHARGER_CONTROL: True,
                        OPTION_ENABLE_PLUG_CONTROL: True,
                        OPTION_USE_LOCAL: False,
                    },
                )

            # Validate local connection
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
                title="Jullix",
                data={
                    CONF_API_TOKEN: data[CONF_API_TOKEN],
                    CONF_INSTALL_IDS: data[CONF_INSTALL_IDS],
                    CONF_LOCAL_HOST: local_host,
                },
                options={
                    OPTION_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    OPTION_ENABLE_COST: False,
                    OPTION_ENABLE_CHARGER_CONTROL: True,
                    OPTION_ENABLE_PLUG_CONTROL: True,
                    OPTION_USE_LOCAL: True,
                },
            )

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_LOCAL_HOST, default=""): str,
                }
            ),
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth when API token is invalid or expired."""
        return await self._async_reauth_show_form(user_input)

    async def _async_reauth_show_form(
        self, user_input: dict[str, Any] | None = None, errors: dict[str, str] | None = None
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
                except ValueError:
                    errors["base"] = "no_installations"
                except Exception as exc:
                    _LOGGER.debug("Reauth token validation failed: %s", exc)
                    errors["base"] = "invalid_token"

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema(
                {vol.Required(CONF_API_TOKEN): str}
            ),
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
            # Reload integration so new options take effect (same behavior as OptionsFlowWithReload)
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
                }
            ),
        )
