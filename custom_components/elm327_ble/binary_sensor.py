"""Engine running, and the check-engine light (if the profile has it)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ObdConfigEntry
from .entity import ObdEntity
from .profiles import all_keys


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ObdConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add engine running, plus check engine if the profile reads it."""
    coordinator = entry.runtime_data
    entities = [
        ObdBinary(
            coordinator,
            "engine_running",
            "Engine running",
            BinarySensorDeviceClass.RUNNING,
            "mdi:engine",
        )
    ]
    if "check_engine" in all_keys(coordinator.profile):
        entities.append(
            ObdBinary(
                coordinator,
                "check_engine",
                "Check engine light",
                BinarySensorDeviceClass.PROBLEM,
                "mdi:engine-off-outline",
            )
        )
    async_add_entities(entities)


class ObdBinary(ObdEntity, BinarySensorEntity):
    """An on/off value; keeps its last reading."""

    def __init__(self, coordinator, key, name, device_class, icon) -> None:
        """Create the sensor."""
        super().__init__(coordinator, key)
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_icon = icon

    @property
    def is_on(self):
        """The latest value."""
        return (self.coordinator.data or {}).get(self._key)
