"""Binary sensor platform for Crestron Home."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CONNECTION_STATUS,
    ATTR_ROOM_ID,
    DOMAIN,
    SENSOR_SUBTYPE_OCCUPANCY,
    SENSOR_SUBTYPE_PHOTO,
)
from .coordinator import CrestronDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crestron Home binary sensors from a config entry."""
    coordinator: CrestronDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Get initial sensor data for setup
    initial_sensors = await coordinator.async_get_initial_sensors()
    
    entities = []
    for sensor_data in initial_sensors:
        subtype = sensor_data.get("subType")
        if subtype == SENSOR_SUBTYPE_OCCUPANCY:
            entities.append(CrestronOccupancySensor(coordinator, sensor_data))
        elif subtype == SENSOR_SUBTYPE_PHOTO:
            entities.append(CrestronPhotoSensor(coordinator, sensor_data))
        else:
            _LOGGER.warning(
                "Unknown sensor subType '%s' for sensor '%s' (ID: %s). Skipping.",
                subtype, sensor_data.get("name"), sensor_data.get("id")
            )
    
    async_add_entities(entities)


class CrestronBinarySensor(CoordinatorEntity[CrestronDataUpdateCoordinator], BinarySensorEntity):
    """Base class for Crestron Home binary sensors."""

    def __init__(
        self,
        coordinator: CrestronDataUpdateCoordinator,
        sensor_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_id = sensor_data["id"]
        self._sensor_data = sensor_data
        self._attr_unique_id = f"{DOMAIN}_sensor_{self._sensor_id}"
        self._attr_name = sensor_data["name"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this sensor."""
        subtype = self._sensor_data.get("subType")
        if subtype == SENSOR_SUBTYPE_OCCUPANCY:
            model = "OccupancySensor"
        elif subtype == SENSOR_SUBTYPE_PHOTO:
            model = "PhotoSensor"
        else:
            model = "Unknown Sensor Type"
        
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._sensor_id))},
            name=self._sensor_data["name"],
            manufacturer="Crestron",
            model=model,
            via_device=(DOMAIN, self.coordinator.entry.entry_id),
        )

    @property
    def sensor_data(self) -> dict[str, Any]:
        """Return the current sensor data."""
        for sensor in self.coordinator.data.get("sensors", []):
            if sensor["id"] == self._sensor_id:
                return sensor
        return self._sensor_data

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return (
            self.coordinator.last_update_success
            and self.sensor_data.get("connectionStatus") == "online"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "sensor_id": self._sensor_id,
            ATTR_ROOM_ID: self.sensor_data.get("roomId"),
            ATTR_CONNECTION_STATUS: self.sensor_data.get("connectionStatus"),
            "subType": self.sensor_data.get("subType"),
        }


class CrestronOccupancySensor(CrestronBinarySensor):
    """Representation of a Crestron Home occupancy sensor."""

    def __init__(
        self,
        coordinator: CrestronDataUpdateCoordinator,
        sensor_data: dict[str, Any],
    ) -> None:
        """Initialize the occupancy sensor."""
        super().__init__(coordinator, sensor_data)
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self) -> bool:
        """Return True if occupancy is detected."""
        presence = self.sensor_data.get("presence", "").lower()
        return presence == "occupied"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes
        attrs["presence"] = self.sensor_data.get("presence")
        return attrs


class CrestronPhotoSensor(CrestronBinarySensor):
    """Representation of a Crestron Home photo sensor."""

    def __init__(
        self,
        coordinator: CrestronDataUpdateCoordinator,
        sensor_data: dict[str, Any],
    ) -> None:
        """Initialize the photo sensor."""
        super().__init__(coordinator, sensor_data)
        self._attr_device_class = BinarySensorDeviceClass.LIGHT

    @property
    def is_on(self) -> bool:
        """Return True if light is detected."""
        # Photo sensors report level 0-255, treat as light detected if above threshold
        level = self.sensor_data.get("level", 0)
        return level > 50  # Configurable threshold

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes
        attrs["level"] = self.sensor_data.get("level")
        attrs["presence"] = self.sensor_data.get("presence")
        return attrs