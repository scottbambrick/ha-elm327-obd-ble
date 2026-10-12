"""Profile requests decode to the documented values."""
from custom_components.elm327_ble.profiles import (
    AMBIENT,
    COOLANT,
    DTC_COUNT,
    FUEL,
    KM_SINCE_CLEAR,
    MIL,
    PROFILES,
    all_keys,
)


def test_standard_decoders():
    assert COOLANT.decode([0x7B]) == 83
    assert AMBIENT.decode([0x28]) == 0
    assert FUEL.decode([0xFF]) == 100
    assert FUEL.decode([0x80]) == 50
    assert KM_SINCE_CLEAR.decode([0x01, 0xF4]) == 500
    assert MIL.decode([0x83]) is True
    assert DTC_COUNT.decode([0x83]) == 3
    assert MIL.decode([0x00]) is False


def test_captiva_dpf_decoders():
    pids = {p.key: p for p in PROFILES["captiva"].pids}
    assert pids["dpf_soot_load"].decode([42]) == 42
    assert pids["km_since_dpf_regen"].decode([0x00, 0x01, 0x2C]) == 300


def test_all_keys_keeps_order_without_repeats():
    keys = all_keys(PROFILES["cx5"])
    assert keys[:2] == ["check_engine", "fault_codes"]
    assert len(keys) == len(set(keys))


def test_profiles_have_unique_keys_and_valid_prefixes():
    for profile in PROFILES.values():
        for pid in profile.pids:
            mode = int(pid.request[:2], 16)
            assert pid.prefix.startswith(f"{mode + 0x40:02X}")
            assert pid.prefix[2:] == pid.request[2:]
