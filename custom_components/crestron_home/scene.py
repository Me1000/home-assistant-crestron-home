"""Scene platform for Crestron Home."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_SCENE_ID,
    ATTR_ROOM_ID,
    ATTR_CONNECTION_STATUS,
    DOMAIN,
    SCENE_TYPE_GENERIC_IO,
    SCENE_TYPE_LIGHT,
    SCENE_TYPE_MEDIA,
)
from .coordinator import CrestronDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crestron Home scenes from a config entry."""
    coordinator: CrestronDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Get initial scene data
    scenes = await coordinator.async_get_initial_scenes()
    
    entities = []
    for scene_data in scenes:
        entities.append(CrestronScene(coordinator, scene_data))
    
    async_add_entities(entities)

    # Store the add_entities callback for dynamic scene management
    coordinator.scene_add_entities_callback = async_add_entities


class CrestronScene(CoordinatorEntity[CrestronDataUpdateCoordinator], Scene):
    """Representation of a Crestron Home scene."""

    def __init__(
        self,
        coordinator: CrestronDataUpdateCoordinator,
        scene_data: dict[str, Any],
    ) -> None:
        """Initialize the scene."""
        super().__init__(coordinator)
        self._scene_id = scene_data["id"]
        self._scene_data = scene_data
        self._attr_unique_id = f"{DOMAIN}_scene_{self._scene_id}"
        self._attr_name = scene_data["name"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this scene."""
        scene_type = self._scene_data.get("type", "")
        if scene_type == SCENE_TYPE_MEDIA:
            model = "Media Scene"
        elif scene_type == SCENE_TYPE_LIGHT:
            model = "Lighting Scene"
        elif scene_type == SCENE_TYPE_GENERIC_IO:
            model = "GenericIO Scene"
        else:
            model = "Scene"
        
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._scene_id))},
            name=self._scene_data["name"],
            manufacturer="Crestron",
            model=model,
            via_device=(DOMAIN, self.coordinator.entry.entry_id),
        )

    @property
    def scene_data(self) -> dict[str, Any]:
        """Return the current scene data."""
        for scene in self.coordinator.data.get("scenes", []):
            if scene["id"] == self._scene_id:
                return scene
        return self._scene_data

    @property
    def available(self) -> bool:
        """Return True if scene is available."""
        return (
            self.coordinator.last_update_success
            and self.scene_data.get("connectionStatus", "online") == "online"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            ATTR_SCENE_ID: self._scene_id,
            ATTR_ROOM_ID: self.scene_data.get("roomId"),
            ATTR_CONNECTION_STATUS: self.scene_data.get("connectionStatus"),
            "type": self.scene_data.get("type"),
        }

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        await self.coordinator.async_recall_scene(self._scene_id)