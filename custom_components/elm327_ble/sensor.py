"""OBD port voltage, the profile's engine readings, last engine reading.

Every value keeps its last reading, also across Home Assistant restarts.
"""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ObdConfigEntry
from .entity import ObdEntity
from .profiles import all_keys

MEASUREMENT = SensorStateClass.MEASUREMENT
DESCRIPTIONS = {
    d.key: d
    for d in (
        SensorEntityDescription(
            key="port_voltage",
            name="OBD port voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=1,
        ),
        SensorEntityDescription(
            key="fuel_level",
            name="Fuel level",
            state_class=MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:gas-station",
        ),
        SensorEntityDescription(
            key="dpf_soot_load",
            name="DPF soot load",
            state_class=MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:smoke",
        ),
        SensorEntityDescription(
            key="km_since_dpf_regen",
            name="Km since DPF regen",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=MEASUREMENT,
            native_unit_of_measurement=UnitOfLength.KILOMETERS,
            icon="mdi:fire",
        ),
        SensorEntityDescription(
            key="fault_codes",
            name="Fault code count",
            state_class=MEASUREMENT,
            icon="mdi:alert-circle-outline",
        ),
        SensorEntityDescription(
            key="coolant_temperature",
            name="Coolant temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        SensorEntityDescription(
            key="km_since_codes_cleared",
            name="Km since codes cleared",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=MEASUREMENT,
            native_unit_of_measurement=UnitOfLength.KILOMETERS,
        ),
        SensorEntityDescription(
            key="ambient_temperature",
            name="Ambient temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
    )
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ObdConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the port voltage, the profile's sensors and last reading."""
    coordinator = entry.runtime_data
    keys = ["port_voltage"] + [
        k for k in all_keys(coordinator.profile) if k in DESCRIPTIONS
    ]
    entities = [ObdSensor(coordinator, DESCRIPTIONS[k]) for k in keys]
    async_add_entities([*entities, LastReading(coordinator)])


class ObdSensor(ObdEntity, RestoreSensor):
    """One value; keeps its last reading."""

    def __init__(
        self, coordinator, description: SensorEntityDescription
    ) -> None:
        """Create the sensor described by `description`."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Bring back the value from before a restart (until a new read)."""
        await super().async_added_to_hass()
        data = self.coordinator.data
        if data.get(self._key) is not None:
            return
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            data[self._key] = last.native_value

    @property
    def native_value(self):
        """The latest value."""
        return (self.coordinator.data or {}).get(self._key)


class LastReading(ObdEntity, RestoreSensor):
    """When the engine ECU last answered (the readings are from then)."""

    _attr_name = "Last engine reading"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:engine-outline"

    def __init__(self, coordinator) -> None:
        """Create the sensor."""
        super().__init__(coordinator, "last_reading")

    async def async_added_to_hass(self) -> None:
        """Bring back the times from before a restart."""
        await super().async_added_to_hass()
        c = self.coordinator
        last = await self.async_get_last_sensor_data()
        if c.last_reading is None and last is not None and isinstance(
            last.native_value, datetime
        ):
            c.last_reading = last.native_value
        state = await self.async_get_last_state()
        if c.last_seen is None and state is not None:
            seen = state.attributes.get("dongle_last_answered")
            c.last_seen = dt_util.parse_datetime(seen) if seen else None

    @property
    def native_value(self):
        """Time of the last engine reading."""
        return self.coordinator.last_reading

    @property
    def extra_state_attributes(self):
        """Troubleshooting details."""
        c = self.coordinator
        return {
            "dongle_last_answered": (
                c.last_seen.isoformat() if c.last_seen else None
            ),
            "last_error": c.last_error,
        }
