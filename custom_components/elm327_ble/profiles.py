"""Car profiles: what to ask the engine computer and how to decode it.

Every request goes to the engine ECU (header 7E0) once a minute while the
engine is running. `prefix` is the positive reply that precedes the data
bytes (the request's mode + 0x40, then the PID), `count` the number of data
bytes, and `decode` turns those bytes into the value. A "NO DATA" reply
just leaves the previous value, so a car that doesn't support a request
simply never fills that sensor.

To add a car, add a Profile below (and descriptions in sensor.py for any
new keys).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Pid:
    """One request and how to decode its reply."""

    key: str
    request: str
    prefix: str
    count: int
    decode: Callable[[list[int]], float | int | bool]


# Standard mode 01 requests (SAE J1979)
MIL = Pid("check_engine", "0101", "4101", 1, lambda b: bool(b[0] & 0x80))
DTC_COUNT = Pid("fault_codes", "0101", "4101", 1, lambda b: b[0] & 0x7F)
COOLANT = Pid("coolant_temperature", "0105", "4105", 1, lambda b: b[0] - 40)
FUEL = Pid(
    "fuel_level", "012F", "412F", 1, lambda b: round(b[0] * 100 / 255)
)
KM_SINCE_CLEAR = Pid(
    "km_since_codes_cleared", "0131", "4131", 2, lambda b: b[0] * 256 + b[1]
)
AMBIENT = Pid("ambient_temperature", "0146", "4146", 1, lambda b: b[0] - 40)
STANDARD = [MIL, DTC_COUNT, COOLANT, FUEL, KM_SINCE_CLEAR, AMBIENT]

# ELM327 setup, sent once per connection
DEFAULT_INIT = [
    "ATZ",      # reset
    "ATE0",     # echo off
    "ATL0",     # no linefeeds
    "ATS0",     # no spaces
    "ATH0",     # no CAN headers in replies
    "ATSP6",    # ISO 15765-4 CAN, 11-bit IDs, 500 kbit/s
    "ATSH7E0",  # talk to the engine ECU
]


@dataclass(frozen=True)
class Profile:
    """A car: its setup commands, requests and engine-running voltage."""

    name: str
    pids: list[Pid] = field(default_factory=list)
    init: list[str] = field(default_factory=lambda: list(DEFAULT_INIT))
    # Battery voltage at the OBD port at or above this = engine running
    running_volts: float = 13.2


PROFILES: dict[str, Profile] = {
    # GM diesel: the DPF requests (mode 22, GM-specific) come first, since
    # there may only be seconds before the ignition goes off.
    "captiva": Profile(
        name="Holden / Chevrolet Captiva (diesel)",
        pids=[
            Pid("dpf_soot_load", "223275", "623275", 1, lambda b: b[0]),
            Pid(
                "km_since_dpf_regen",
                "223277",
                "623277",
                3,
                lambda b: b[1] * 256 + b[2],
            ),
            *STANDARD,
        ],
    ),
    # Petrol: standard requests only
    "cx5": Profile(name="Mazda CX-5 (petrol)", pids=list(STANDARD)),
}


def all_keys(profile: Profile) -> list[str]:
    """The value keys a profile provides, in order, without repeats."""
    keys: list[str] = []
    for pid in profile.pids:
        if pid.key not in keys:
            keys.append(pid.key)
    return keys
