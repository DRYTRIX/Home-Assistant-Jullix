"""Home Assistant Repairs issue management for Jullix."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_AUTH = "auth_failed"
ISSUE_API_FAILURE = "api_failure"
ISSUE_LOCAL_UNREACHABLE = "local_unreachable"

PERSISTENT_ERROR_THRESHOLD = 3

ALL_ISSUE_IDS = (ISSUE_AUTH, ISSUE_API_FAILURE, ISSUE_LOCAL_UNREACHABLE)


def _issue_id(entry_id: str, kind: str) -> str:
    return f"{kind}_{entry_id}"


class JullixRepairsManager:
    """Create and clear repair issues based on coordinator health."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._consecutive_errors: dict[str, int] = {}
        self._consecutive_local_failures = 0

    def async_clear_all(self) -> None:
        """Remove all issues for this config entry."""
        for kind in ALL_ISSUE_IDS:
            ir.async_delete_issue(self._hass, DOMAIN, _issue_id(self._entry_id, kind))

    def async_update(
        self,
        *,
        install_errors: dict[str, Exception],
        use_local: bool,
        local_merge_failed: bool,
    ) -> None:
        """Sync repair issues with the latest coordinator state."""
        auth_errors = {
            iid: err
            for iid, err in install_errors.items()
            if err.__class__.__name__ == "JullixAuthError"
        }
        other_errors = {
            iid: err for iid, err in install_errors.items() if iid not in auth_errors
        }

        if auth_errors:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                _issue_id(self._entry_id, ISSUE_AUTH),
                is_fixable=True,
                severity=ir.IssueSeverity.ERROR,
                translation_key=ISSUE_AUTH,
                translation_placeholders={
                    "installations": ", ".join(sorted(auth_errors)),
                },
                data={"entry_id": self._entry_id},
            )
        else:
            ir.async_delete_issue(
                self._hass, DOMAIN, _issue_id(self._entry_id, ISSUE_AUTH)
            )

        for iid in list(self._consecutive_errors):
            if iid not in other_errors:
                self._consecutive_errors[iid] = 0
        for iid, err in other_errors.items():
            self._consecutive_errors[iid] = self._consecutive_errors.get(iid, 0) + 1
            _LOGGER.debug(
                "Installation %s consecutive API errors: %s (%s)",
                iid,
                self._consecutive_errors[iid],
                err,
            )

        persistent = [
            iid
            for iid, count in self._consecutive_errors.items()
            if count >= PERSISTENT_ERROR_THRESHOLD
        ]
        if persistent:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                _issue_id(self._entry_id, ISSUE_API_FAILURE),
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_API_FAILURE,
                translation_placeholders={
                    "installations": ", ".join(sorted(persistent)),
                },
            )
        else:
            ir.async_delete_issue(
                self._hass, DOMAIN, _issue_id(self._entry_id, ISSUE_API_FAILURE)
            )

        if use_local:
            if local_merge_failed:
                self._consecutive_local_failures += 1
            else:
                self._consecutive_local_failures = 0
            if self._consecutive_local_failures >= PERSISTENT_ERROR_THRESHOLD:
                ir.async_create_issue(
                    self._hass,
                    DOMAIN,
                    _issue_id(self._entry_id, ISSUE_LOCAL_UNREACHABLE),
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key=ISSUE_LOCAL_UNREACHABLE,
                )
            else:
                ir.async_delete_issue(
                    self._hass,
                    DOMAIN,
                    _issue_id(self._entry_id, ISSUE_LOCAL_UNREACHABLE),
                )
        else:
            self._consecutive_local_failures = 0
            ir.async_delete_issue(
                self._hass, DOMAIN, _issue_id(self._entry_id, ISSUE_LOCAL_UNREACHABLE)
            )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> Any:
    """Repair flow: reauth for auth failures."""
    from homeassistant.config_entries import SOURCE_REAUTH

    if not issue_id.endswith(ISSUE_AUTH) or not data:
        return None
    entry_id = data.get("entry_id")
    if not entry_id:
        return None
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        return None

    from homeassistant.components.repairs import RepairsFlow

    class JullixAuthRepairFlow(RepairsFlow):
        """Confirm reauth for expired Jullix API token."""

        async def async_step_confirm(
            self, user_input: dict[str, Any] | None = None
        ) -> Any:
            if user_input is not None:
                return self.async_create_entry(title="", data={})
            return self.async_show_form(step_id="confirm")

        async def async_step_init(
            self, user_input: dict[str, Any] | None = None
        ) -> Any:
            return await self.async_step_confirm(user_input)

    flow = JullixAuthRepairFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.issue_id = issue_id
    flow.data = data
    flow.context = {"source": SOURCE_REAUTH, "entry_id": entry_id}
    return flow
