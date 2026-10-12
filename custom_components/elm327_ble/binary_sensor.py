"""Engine running, and the check-engine light (if the profile has it)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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


# Engine running is re-checked straight away and must not stick at "on"
# if the car left during a restart, so only these are restored
RESTORED = {"check_engine"}


class ObdBinary(ObdEntity, BinarySensorEntity, RestoreEntity):
    """An on/off value; keeps its last reading."""

    def __init__(self, coordinator, key, name, device_class, icon) -> None:
        """Create the sensor."""
        super().__init__(coordinator, key)
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        """Bring back the value from before a restart (until a new read)."""
        await super().async_added_to_hass()
        data = self.coordinator.data
        if self._key not in RESTORED or data.get(self._key) is not None:
            return
        state = await self.async_get_last_state()
        if state is not None and state.state in (STATE_ON, STATE_OFF):
            data[self._key] = state.state == STATE_ON

    @property
    def is_on(self):
        """The latest value."""
        return (self.coordinator.data or {}).get(self._key)
