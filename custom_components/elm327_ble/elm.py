"""A text session with an ELM327 dongle over Bluetooth LE."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import math

from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)

_LOGGER = logging.getLogger(__name__)


def _uuid(short: str) -> str:
    """Full UUID for a 16-bit Bluetooth SIG-style short UUID."""
    return f"0000{short}-0000-1000-8000-00805f9b34fb"


# Known dongle layouts: (service, notify characteristic, write characteristic)
KNOWN_LAYOUTS = [
    # Most generic "OBD2 BLE" dongles
    (_uuid("fff0"), _uuid("fff1"), _uuid("fff2")),
    # Vgate iCar Pro BLE / 2S
    (
        "e7810a71-73ae-499d-8c15-faa9aef0c3f2",
        "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
        "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
    ),
    # LeLink and other HM-10 style dongles
    (_uuid("ffe0"), _uuid("ffe1"), _uuid("ffe1")),
]

ERRORS = (
    "NO DATA",
    "ERROR",
    "UNABLE",
    "STOPPED",
    "BUS INIT",
    "BUFFER FULL",
    "CAN ERROR",
    "?",
)


def is_error(rx: str) -> bool:
    """Whether a reply is an error or "no answer" rather than data."""
    return any(e in rx.upper() for e in ERRORS)


def data_bytes(rx: str, prefix: str, count: int) -> list[int] | None:
    """The `count` data bytes after the positive reply `prefix`, or None.

    Example: request "0105" is answered "41057B" (or "41 05 7B") ->
    prefix "4105", count 1 -> [0x7B]. Spaces, CRs and echoes are ignored.
    """
    if is_error(rx):
        return None
    hexs = "".join(c for c in rx.upper() if c in "0123456789ABCDEF")
    p = hexs.find(prefix)
    if p < 0 or len(hexs) < p + len(prefix) + count * 2:
        return None
    p += len(prefix)
    return [int(hexs[p + i * 2:p + i * 2 + 2], 16) for i in range(count)]


def volts(rx: str) -> float:
    """The reply to ATRV (e.g. "12.6V") as a number, or NaN."""
    for i, c in enumerate(rx):
        if c.isdigit():
            num = ""
            for d in rx[i:]:
                if not (d.isdigit() or d == "."):
                    break
                num += d
            try:
                return float(num)
            except ValueError:
                return math.nan
    return math.nan


class ElmLink:
    """One connection to a dongle: send a command, read up to '>'."""

    def __init__(self, name: str) -> None:
        """Prepare a link; `name` is used in logs."""
        self.name = name
        self.client = None
        self._write_char = None
        self._write_response = True
        self._rx = ""
        self._prompt = asyncio.Event()

    def _on_notify(self, _sender, data: bytearray) -> None:
        self._rx += data.decode("ascii", "ignore")
        if ">" in self._rx:
            self._prompt.set()

    async def connect(self, device: BLEDevice) -> None:
        """Connect and find the dongle's serial characteristics."""
        self.client = await establish_connection(
            BleakClientWithServiceCache, device, self.name, max_attempts=2
        )
        services = self.client.services
        notify = write = None
        for service, notify_uuid, write_uuid in KNOWN_LAYOUTS:
            if services.get_service(service):
                notify = services.get_characteristic(notify_uuid)
                write = services.get_characteristic(write_uuid)
                if notify and write:
                    break
        if not (notify and write):
            # Unknown dongle: first service with a notify and a write
            # characteristic
            for service in services:
                chars = service.characteristics
                notify = next(
                    (c for c in chars if "notify" in c.properties), None
                )
                write = next(
                    (
                        c
                        for c in chars
                        if {"write", "write-without-response"}
                        & set(c.properties)
                    ),
                    None,
                )
                if notify and write:
                    break
        if not (notify and write):
            raise ConnectionError("no ELM327 serial characteristics found")
        self._write_char = write
        self._write_response = "write" in write.properties
        await self.client.start_notify(notify, self._on_notify)
        _LOGGER.debug("%s: using %s / %s", self.name, notify.uuid,
                      write.uuid)

    async def cmd(self, text: str, timeout: float = 3) -> str:
        """Send one command and return the reply up to the '>' prompt."""
        self._rx = ""
        self._prompt.clear()
        await self.client.write_gatt_char(
            self._write_char,
            (text + "\r").encode(),
            response=self._write_response,
        )
        try:
            await asyncio.wait_for(self._prompt.wait(), timeout)
        except TimeoutError:
            _LOGGER.debug("%s: no prompt after %s (got %r)", self.name, text,
                          self._rx)
        return self._rx.replace(">", "").strip()

    async def disconnect(self) -> None:
        """Hang up (safe to call more than once, never raises)."""
        client, self.client = self.client, None
        if client is None:
            return
        # The link may already be gone (out of range, proxy restarted)
        with contextlib.suppress(Exception):
            await client.disconnect()
