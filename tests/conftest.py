"""Load the integration's plain-Python modules without Home Assistant.

The package's __init__.py imports Home Assistant, so the package is
registered here by path instead; bleak is stubbed when not installed (the
tests never open a Bluetooth connection).
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.elm327_ble"

sys.modules.setdefault(
    "custom_components", types.ModuleType("custom_components")
)
_pkg = types.ModuleType(PACKAGE)
_pkg.__path__ = [str(ROOT / "custom_components" / "elm327_ble")]
sys.modules[PACKAGE] = _pkg

try:
    import bleak  # noqa: F401
    import bleak_retry_connector  # noqa: F401
except ImportError:
    _device = types.ModuleType("bleak.backends.device")
    _device.BLEDevice = object
    sys.modules["bleak"] = types.ModuleType("bleak")
    sys.modules["bleak.backends"] = types.ModuleType("bleak.backends")
    sys.modules["bleak.backends.device"] = _device
    _brc = types.ModuleType("bleak_retry_connector")
    _brc.BleakClientWithServiceCache = object
    _brc.establish_connection = None
    sys.modules["bleak_retry_connector"] = _brc
