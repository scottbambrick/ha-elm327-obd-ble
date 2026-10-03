"""OBD-II (ELM327) dongles over Home Assistant's Bluetooth.

Each config entry is one car's dongle, read through whichever connectable
Bluetooth adapter or ESPHome Bluetooth proxy hears it best.
"""
from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_PROFILE
from .coordinator import ObdCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type ObdConfigEntry = ConfigEntry[ObdCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: ObdConfigEntry
) -> bool:
    """Set up one dongle."""
    coordinator = ObdCoordinator(
        hass,
        entry,
        entry.data[CONF_ADDRESS],
        entry.data[CONF_PROFILE],
        entry.data[CONF_NAME],
    )
    entry.runtime_data = coordinator

    # The dongle advertises when it wakes (e.g. the car starts): check now
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            coordinator.async_advertisement,
            {"address": coordinator.address},
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_refresh()  # starts the first check
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ObdConfigEntry
) -> bool:
    """Stop any session and unload."""
    await entry.runtime_data.async_shutdown()
    return await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
