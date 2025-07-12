"""Light platform for Crestron Home."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CONNECTION_STATUS,
    ATTR_LIGHT_ID,
    ATTR_ROOM_ID,
    DOMAIN,
    LIGHT_SUBTYPE_DIMMER,
    LIGHT_SUBTYPE_SWITCH,
    MAX_BRIGHTNESS,
)
from .coordinator import CrestronDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crestron Home lights from a config entry."""
    coordinator: CrestronDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    for light_data in coordinator.data.get("lights", []):
        subtype = light_data.get("subType")
        if subtype not in (LIGHT_SUBTYPE_DIMMER, LIGHT_SUBTYPE_SWITCH):
            _LOGGER.warning(
                "Unknown light subType '%s' for light '%s' (ID: %s). Treating as switch.",
                subtype, light_data.get("name"), light_data.get("id")
            )
        entities.append(CrestronLight(coordinator, light_data))
    
    async_add_entities(entities)


class CrestronLight(CoordinatorEntity[CrestronDataUpdateCoordinator], LightEntity):
    """Representation of a Crestron Home light."""

    def __init__(
        self,
        coordinator: CrestronDataUpdateCoordinator,
        light_data: dict[str, Any],
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._light_id = light_data["id"]
        self._light_data = light_data
        self._attr_unique_id = f"{DOMAIN}_light_{self._light_id}"
        self._attr_name = light_data["name"]
        
        # Set supported features based on light type
        if light_data.get("subType") == LIGHT_SUBTYPE_DIMMER:
            self._attr_supported_features = LightEntityFeature.TRANSITION

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this light."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._light_id))},
            name=self._light_data["name"],
            manufacturer="Crestron",
            model=self._light_data.get("subType", "Light"),
            via_device=(DOMAIN, self.coordinator.entry.entry_id),
        )

    @property
    def light_data(self) -> dict[str, Any]:
        """Return the current light data."""
        for light in self.coordinator.data.get("lights", []):
            if light["id"] == self._light_id:
                return light
        return self._light_data

    def _update_local_state(self, level: int) -> None:
        """Update the local light state optimistically."""
        # Update the cached light data
        for light in self.coordinator.data.get("lights", []):
            if light["id"] == self._light_id:
                light["level"] = level
                break
        else:
            # If not found in coordinator data, update our local cache
            self._light_data["level"] = level

    @property
    def is_on(self) -> bool:
        """Return True if light is on."""
        return self.light_data.get("level", 0) > 0

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self.light_data.get("subType") == LIGHT_SUBTYPE_DIMMER:
            # Convert from Crestron range (0-65535) to HA range (0-255)
            level = self.light_data.get("level", 0)
            return max(1, int(level * 255 / MAX_BRIGHTNESS)) if level > 0 else 0
        return None

    @property
    def available(self) -> bool:
        """Return True if light is available."""
        return (
            self.coordinator.last_update_success
            and self.light_data.get("connectionStatus") == "online"
        )

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return the list of supported color modes."""
        if self.light_data.get("subType") == LIGHT_SUBTYPE_DIMMER:
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        if self.light_data.get("subType") == LIGHT_SUBTYPE_DIMMER:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            ATTR_LIGHT_ID: self._light_id,
            ATTR_ROOM_ID: self.light_data.get("roomId"),
            ATTR_CONNECTION_STATUS: self.light_data.get("connectionStatus"),
            "subType": self.light_data.get("subType"),
            "level": self.light_data.get("level"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        transition = kwargs.get("transition", 0)
        
        if self.light_data.get("subType") == LIGHT_SUBTYPE_DIMMER:
            if brightness is not None:
                # Convert from HA range (0-255) to Crestron range (0-65535)
                level = int(brightness * MAX_BRIGHTNESS / 255)
            else:
                level = MAX_BRIGHTNESS
        else:
            # For switches, any non-zero level is full on
            level = MAX_BRIGHTNESS
        
        # Send command to Crestron
        await self.coordinator.async_set_light_state(
            self._light_id, level, int(transition * 1000)
        )
        
        # Update local state immediately for responsive UI
        self._update_local_state(level)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        transition = kwargs.get("transition", 0)
        
        # Send command to Crestron
        await self.coordinator.async_set_light_state(
            self._light_id, 0, int(transition * 1000)
        )
        
        # Update local state immediately for responsive UI
        self._update_local_state(0)
        self.async_write_ha_state()