"""Base sensor and helpers for Jullix snapshot-backed entities."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import JullixDataUpdateCoordinator
from ..device_helpers import device_info_hub
from ..models import JullixInstallationSnapshot, build_installation_snapshot
from ..models.installation import RawInstallFetches

_LOGGER = logging.getLogger(__name__)


def get_installation_snapshot(
    coordinator: JullixDataUpdateCoordinator,
    install_id: str,
) -> JullixInstallationSnapshot:
    """Return snapshot for install, or empty snapshot if missing."""
    snap = coordinator.data.get(install_id)
    if snap is not None:
        return snap
    return build_installation_snapshot(RawInstallFetches())


class JullixSensor(CoordinatorEntity[JullixDataUpdateCoordinator], SensorEntity):
    """Base class for Jullix sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JullixDataUpdateCoordinator,
        install_id: str,
        install_name: str,
        unique_id: str,
        name: str,
        *,
        device_info: DeviceInfo | None = None,
        translation_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._install_id = install_id
        self._install_name = install_name
        self._attr_unique_id = f"{DOMAIN}_{unique_id}"
        self._attr_name = name
        if translation_key is not None:
            self._attr_translation_key = translation_key
        self._attr_device_info = device_info or device_info_hub(
            install_id, install_name
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        try:
            self._update_from_snapshot()
        except Exception as err:
            _LOGGER.exception(
                "Jullix sensor update failed (%s): %s", self._attr_unique_id, err
            )
        super()._handle_coordinator_update()

    def _update_from_snapshot(self) -> None:
        """Set _attr_* from coordinator snapshot."""
        raise NotImplementedError
