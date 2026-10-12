"""Reply parsing for the ELM327 text protocol."""
import math

from custom_components.elm327_ble.elm import data_bytes, is_error, volts


def test_data_bytes_plain_and_spaced():
    assert data_bytes("41057B", "4105", 1) == [0x7B]
    assert data_bytes("41 05 7B", "4105", 1) == [0x7B]


def test_data_bytes_ignores_echo_and_prompt():
    assert data_bytes("0105\r41 05 7B \r\r", "4105", 1) == [0x7B]


def test_data_bytes_multi_byte():
    assert data_bytes("4131 01 F4", "4131", 2) == [0x01, 0xF4]


def test_data_bytes_errors_and_short_replies():
    assert data_bytes("NO DATA", "4105", 1) is None
    assert data_bytes("CAN ERROR", "4105", 1) is None
    assert data_bytes("?", "4105", 1) is None
    assert data_bytes("4105", "4105", 1) is None
    assert data_bytes("410C1A", "4105", 1) is None


def test_is_error_is_case_insensitive():
    assert is_error("unable to connect")
    assert not is_error("41057B")


def test_volts():
    assert volts("12.6V") == 12.6
    assert volts("\r14.1V\r") == 14.1
    assert math.isnan(volts("?"))
    assert math.isnan(volts(""))
