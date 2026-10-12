"""Checks a car's OBD dongle, and reads the engine while it's running.

Parked: every CHECK_MINUTES connect, read the battery voltage at the OBD
port (ATRV - measured by the dongle itself, so it doesn't wake the car's
computers) and disconnect again. A held connection would stop the dongle
sleeping and slowly drain the car's battery.

Engine running (voltage at or above the profile's running_volts, i.e. the
alternator is charging): stay connected, re-check every RUNNING_RECHECK
seconds and read the profile's requests every QUERY_EVERY seconds until the
engine stops. Hearing the dongle advertise (it wakes when the car starts)
triggers a check straight away. Values keep their last reading.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import math
from datetime import datetime, timedelta

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ADVERT_DEBOUNCE,
    CHECK_MINUTES,
    MAX_SESSION,
    QUERY_EVERY,
    RUNNING_RECHECK,
)
from .elm import ElmLink, data_bytes, volts
from .profiles import PROFILES

_LOGGER = logging.getLogger(__name__)


class ObdCoordinator(DataUpdateCoordinator[dict]):
    """One car's dongle."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        address: str,
        profile_key: str,
        name: str,
    ) -> None:
        """Set up checks for the dongle at `address`."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=name,
            update_interval=timedelta(minutes=CHECK_MINUTES),
        )
        self.address = address.upper()
        self.profile_key = profile_key
        self.profile = PROFILES[profile_key]
        self.data: dict = {}
        self.last_seen: datetime | None = None     # dongle answered
        self.last_reading: datetime | None = None  # engine ECU answered
        self.last_error: str | None = None
        self._task: asyncio.Task | None = None
        self._last_start: datetime | None = None

    @property
    def busy(self) -> bool:
        """Whether a session is running."""
        return self._task is not None and not self._task.done()

    def _start(self) -> None:
        """Start a session in the background unless one is running."""
        if self.busy:
            return
        self._last_start = dt_util.utcnow()
        self._task = self.config_entry.async_create_background_task(
            self.hass, self._session(), f"elm327_ble {self.name}"
        )

    @callback
    def async_advertisement(self, service_info, change) -> None:
        """Heard the dongle: check now (debounced)."""
        if self.busy:
            return
        if self._last_start and (
            (dt_util.utcnow() - self._last_start).total_seconds()
            < ADVERT_DEBOUNCE
        ):
            return
        self._start()

    async def _async_update_data(self) -> dict:
        """Scheduled check; results arrive via async_set_updated_data."""
        self._start()
        return self.data

    async def async_shutdown(self) -> None:
        """Cancel any running session and wait for it to hang up."""
        if self.busy:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await super().async_shutdown()

    def _push(self, **values) -> None:
        """Merge new values in and update the entities."""
        self.async_set_updated_data({**self.data, **values})

    async def _session(self) -> None:
        """Connect, check the voltage, read the engine while it runs."""
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            self.last_error = (
                "not heard by any connectable Bluetooth adapter or proxy"
            )
            self._push()
            return

        link = ElmLink(self.name)
        started = dt_util.utcnow()
        last_query: datetime | None = None
        try:
            await link.connect(device)
            for command in self.profile.init:
                await link.cmd(command, timeout=5 if command == "ATZ" else 3)
            while True:
                v = volts(await link.cmd("ATRV"))
                if math.isnan(v):
                    raise ConnectionError("no voltage reply")
                self.last_seen = dt_util.utcnow()
                self.last_error = None
                running = v >= self.profile.running_volts
                self._push(port_voltage=round(v, 1), engine_running=running)
                if not running:
                    break
                if last_query is None or (
                    (dt_util.utcnow() - last_query).total_seconds()
                    >= QUERY_EVERY
                ):
                    last_query = dt_util.utcnow()
                    await self._query(link)
                if (dt_util.utcnow() - started).total_seconds() > MAX_SESSION:
                    break
                await asyncio.sleep(RUNNING_RECHECK)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            # Out of range, asleep, busy proxy...: not an error
            self.last_error = f"{type(err).__name__}: {err}"
            _LOGGER.debug("%s: %s", self.name, self.last_error)
            if self.data.get("engine_running"):
                self._push(engine_running=False)
            else:
                self._push()
        finally:
            await link.disconnect()

    async def _query(self, link: ElmLink) -> None:
        """Send each of the profile's requests and decode the replies."""
        values: dict = {}
        replies: dict[str, str] = {}
        for pid in self.profile.pids:
            if pid.request not in replies:  # one request can serve two
                replies[pid.request] = await link.cmd(pid.request)
            data = data_bytes(replies[pid.request], pid.prefix, pid.count)
            if data is not None:
                values[pid.key] = pid.decode(data)
        if values:
            self.last_reading = dt_util.utcnow()
            self._push(**values)
        _LOGGER.debug("%s: read %s", self.name, values)
