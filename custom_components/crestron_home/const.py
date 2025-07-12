"""Constants for the Crestron Home integration."""
from typing import Final

DOMAIN: Final = "crestron_home"

CONF_HOST: Final = "host"
CONF_API_TOKEN: Final = "api_token"
CONF_POLLING_INTERVAL: Final = "polling_interval"
CONF_POLL_SENSORS: Final = "poll_sensors"

DEFAULT_NAME: Final = "Crestron Home"
DEFAULT_PORT: Final = 443
DEFAULT_POLLING_INTERVAL: Final = 30

ATTR_LIGHT_ID: Final = "light_id"
ATTR_ROOM_ID: Final = "room_id"
ATTR_CONNECTION_STATUS: Final = "connection_status"

LIGHT_SUBTYPE_DIMMER: Final = "Dimmer"
LIGHT_SUBTYPE_SWITCH: Final = "Switch"

SENSOR_SUBTYPE_OCCUPANCY: Final = "OccupancySensor"
SENSOR_SUBTYPE_PHOTO: Final = "PhotoSensor"

MAX_BRIGHTNESS: Final = 65535