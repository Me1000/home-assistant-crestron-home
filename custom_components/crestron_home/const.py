"""Constants for the Crestron Home integration."""
from typing import Final

DOMAIN: Final = "crestron_home"

CONF_HOST: Final = "host"
CONF_API_TOKEN: Final = "api_token"
CONF_POLLING_INTERVAL: Final = "polling_interval"
CONF_POLL_SENSORS: Final = "poll_sensors"
CONF_IMPORT_MEDIA_SCENES: Final = "import_media_scenes"
CONF_IMPORT_LIGHT_SCENES: Final = "import_light_scenes"
CONF_IMPORT_GENERIC_IO_SCENES: Final = "import_generic_io_scenes"

DEFAULT_NAME: Final = "Crestron Home"
DEFAULT_PORT: Final = 443
DEFAULT_POLLING_INTERVAL: Final = 30

ATTR_LIGHT_ID: Final = "light_id"
ATTR_ROOM_ID: Final = "room_id"
ATTR_CONNECTION_STATUS: Final = "connection_status"
ATTR_SCENE_ID: Final = "scene_id"

LIGHT_SUBTYPE_DIMMER: Final = "Dimmer"
LIGHT_SUBTYPE_SWITCH: Final = "Switch"

SENSOR_SUBTYPE_OCCUPANCY: Final = "OccupancySensor"
SENSOR_SUBTYPE_PHOTO: Final = "PhotoSensor"

SCENE_TYPE_MEDIA: Final = "Media"
SCENE_TYPE_LIGHT: Final = "Lighting"
SCENE_TYPE_GENERIC_IO: Final = "genericIO"

MAX_BRIGHTNESS: Final = 65535