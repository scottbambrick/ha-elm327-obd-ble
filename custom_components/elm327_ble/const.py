"""Constants for OBD-II over Bluetooth LE."""

DOMAIN = "elm327_ble"
CONF_PROFILE = "profile"

# Parked: how often to check the dongle (connect, read voltage, hang up)
CHECK_MINUTES = 2
# Engine running: seconds between voltage checks and between full reads
RUNNING_RECHECK = 10
QUERY_EVERY = 60
# Give up a held connection after this long (seconds)
MAX_SESSION = 3 * 3600
# Don't start a check on an advertisement more often than this (seconds)
ADVERT_DEBOUNCE = 30
