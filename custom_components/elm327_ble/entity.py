"""Base entity: shared device info for a dongle's entities."""
from __future__ import annotations

from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ObdCoordinator


class ObdEntity(CoordinatorEntity[ObdCoordinator]):
    """An entity belonging to one dongle."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ObdCoordinator, key: str) -> None:
        """Link the entity to the dongle's device."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            name=coordinator.name,
            manufacturer="ELM327",
            model=coordinator.profile.name,
        )

    @property
    def available(self) -> bool:
        """Always available: keeps the last reading while away/asleep."""
        return True
