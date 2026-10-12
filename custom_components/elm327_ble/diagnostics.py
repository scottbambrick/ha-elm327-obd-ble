"""Diagnostics: settings and the latest values (address redacted)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from . import ObdConfigEntry

TO_REDACT = {CONF_ADDRESS}


def _iso(value) -> str | None:
    return value.isoformat() if value else None


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ObdConfigEntry
) -> dict[str, Any]:
    """Return the entry's settings, values and connection state."""
    c = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "profile": c.profile_key,
        "values": dict(c.data),
        "session_running": c.busy,
        "dongle_last_answered": _iso(c.last_seen),
        "last_engine_reading": _iso(c.last_reading),
        "last_error": c.last_error,
    }
