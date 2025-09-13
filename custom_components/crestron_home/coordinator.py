"""DataUpdateCoordinator for Crestron Home."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CrestronAPI, CrestronError
from .const import (
    CONF_API_TOKEN,
    CONF_IMPORT_GENERIC_IO_SCENES,
    CONF_IMPORT_LIGHT_SCENES,
    CONF_IMPORT_MEDIA_SCENES,
    CONF_POLL_SENSORS,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    SCENE_TYPE_GENERIC_IO,
    SCENE_TYPE_LIGHT,
    SCENE_TYPE_MEDIA,
)

_LOGGER = logging.getLogger(__name__)

class CrestronDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Crestron Home data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
        api_token = entry.options.get(CONF_API_TOKEN, entry.data[CONF_API_TOKEN])
        self.api = CrestronAPI(host, api_token)
        self.entry = entry
        
        polling_interval = entry.options.get(
            CONF_POLLING_INTERVAL, 
            entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
        )
        update_interval = timedelta(seconds=polling_interval)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{host}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Crestron Home."""
        try:
            data = {}
            
            # Always fetch lights
            lights_data = await self.api.async_get_lights()
            data["lights"] = lights_data.get("lights", [])
            
            # Always fetch sensors initially, but only poll if enabled
            poll_sensors = self.entry.options.get(
                CONF_POLL_SENSORS, 
                self.entry.data.get(CONF_POLL_SENSORS, False)
            )
            if poll_sensors:
                sensors_data = await self.api.async_get_sensors()
                data["sensors"] = sensors_data.get("sensors", [])
            else:
                # If not polling, provide empty sensors list but still allow platform to load
                data["sensors"] = getattr(self, '_cached_sensors', [])
            
            # Always provide cached scenes (scenes don't change frequently)
            data["scenes"] = getattr(self, '_cached_scenes', [])
            
            return data
        except CrestronError as err:
            raise UpdateFailed(f"Error communicating with Crestron Home: {err}") from err

    async def async_get_initial_sensors(self) -> list[dict[str, Any]]:
        """Get initial sensor data for setup, regardless of polling setting."""
        try:
            sensors_data = await self.api.async_get_sensors()
            sensors = sensors_data.get("sensors", [])
            # Cache for non-polling mode
            self._cached_sensors = sensors
            return sensors
        except CrestronError:
            _LOGGER.warning("Could not fetch initial sensor data")
            return []

    async def async_get_initial_scenes(self) -> list[dict[str, Any]]:
        """Get initial scene data for setup."""
        try:
            scenes_data = await self.api.async_get_scenes()
            all_scenes = scenes_data.get("scenes", [])
            
            # Filter scenes based on configuration
            filtered_scenes = self._filter_scenes(all_scenes)
            
            # Cache scenes since they don't change frequently
            self._cached_scenes = filtered_scenes
            return filtered_scenes
        except CrestronError:
            _LOGGER.warning("Could not fetch initial scene data")
            return []

    def _filter_scenes(self, scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter scenes based on configuration options."""
        import_media = self.entry.options.get(
            CONF_IMPORT_MEDIA_SCENES,
            self.entry.data.get(CONF_IMPORT_MEDIA_SCENES, False)
        )
        import_light = self.entry.options.get(
            CONF_IMPORT_LIGHT_SCENES,
            self.entry.data.get(CONF_IMPORT_LIGHT_SCENES, False)
        )
        import_generic_io = self.entry.options.get(
            CONF_IMPORT_GENERIC_IO_SCENES,
            self.entry.data.get(CONF_IMPORT_GENERIC_IO_SCENES, True)
        )

        filtered_scenes = []
        for scene in scenes:
            scene_type = scene.get("type", "")
            
            if scene_type == SCENE_TYPE_MEDIA and import_media:
                filtered_scenes.append(scene)
            elif scene_type == SCENE_TYPE_LIGHT and import_light:
                filtered_scenes.append(scene)
            elif scene_type == SCENE_TYPE_GENERIC_IO and import_generic_io:
                filtered_scenes.append(scene)
            else:
                _LOGGER.debug(
                    "Skipping scene '%s' (type: %s) due to configuration",
                    scene.get("name", "Unknown"),
                    scene_type
                )
        
        return filtered_scenes

    async def async_update_scene_entities(self) -> None:
        """Update scene entities based on current configuration."""
        try:
            # Get fresh scene data from API when settings change
            scenes_data = await self.api.async_get_scenes()
            all_scenes = scenes_data.get("scenes", [])
            
            # Get currently enabled scenes with fresh data
            new_filtered_scenes = self._filter_scenes(all_scenes)
            old_filtered_scenes = getattr(self, '_cached_scenes', [])
            
            # Update cached scenes with fresh filtered data
            self._cached_scenes = new_filtered_scenes
            
            # Get entity registry
            entity_registry = er.async_get(self.hass)
            
            # Find scenes that need to be removed and added
            old_scene_ids = {scene["id"] for scene in old_filtered_scenes}
            new_scene_ids = {scene["id"] for scene in new_filtered_scenes}
            scenes_to_remove = old_scene_ids - new_scene_ids
            scenes_to_add = new_scene_ids - old_scene_ids
            
            # Remove disabled scene entities and their device entries
            device_registry = dr.async_get(self.hass)
            for scene_id in scenes_to_remove:
                entity_id = f"scene.{DOMAIN}_scene_{scene_id}"
                entity_entry = entity_registry.async_get(entity_id)
                if entity_entry:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.info("Removed scene entity: %s", entity_id)
                
                # Also remove the device entry for this scene
                device_id = (DOMAIN, str(scene_id))
                device_entry = device_registry.async_get_device(identifiers={device_id})
                if device_entry:
                    device_registry.async_remove_device(device_entry.id)
                    _LOGGER.info("Removed scene device: %s", device_id)
            
            # Add new scene entities if we have the callback
            if scenes_to_add and hasattr(self, 'scene_add_entities_callback'):
                from .scene import CrestronScene
                
                new_entities = []
                for scene_data in new_filtered_scenes:
                    if scene_data["id"] in scenes_to_add:
                        new_entities.append(CrestronScene(self, scene_data))
                
                if new_entities:
                    self.scene_add_entities_callback(new_entities)
                    _LOGGER.info("Added %d new scene entities", len(new_entities))
            
            # Clean up any phantom scene devices
            await self.async_cleanup_phantom_scenes()
            
            # Trigger a coordinator update to refresh entities
            await self.async_request_refresh()
            
        except CrestronError as err:
            _LOGGER.error("Error updating scene entities: %s", err)
        except Exception as err:
            _LOGGER.error("Unexpected error updating scene entities: %s", err)

    async def async_cleanup_phantom_scenes(self) -> None:
        """Remove phantom scene devices that have no entities."""
        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            
            # Get all devices for this integration
            devices = dr.async_entries_for_config_entry(device_registry, self.entry.entry_id)
            
            # Get current valid scene IDs
            current_scene_ids = {str(scene["id"]) for scene in self._cached_scenes}
            
            # Remove phantom scene devices
            for device in devices:
                # Check if this is a scene device (has scene-like identifier)
                scene_identifiers = [id_tuple for id_tuple in device.identifiers if id_tuple[0] == DOMAIN]
                if scene_identifiers:
                    device_id = scene_identifiers[0][1]
                    # Skip the hub device (entry_id) and only check scene devices
                    if device_id != self.entry.entry_id and device_id not in current_scene_ids:
                        # Check if this device has any entities
                        entities = er.async_entries_for_device(entity_registry, device.id)
                        if not entities:
                            # Phantom device with no entities - remove it
                            device_registry.async_remove_device(device.id)
                            _LOGGER.info("Removed phantom scene device: %s", device_id)
                            
        except Exception as err:
            _LOGGER.error("Error cleaning up phantom scenes: %s", err)

    async def async_set_light_state(self, light_id: int, level: int, time: int = 0) -> None:
        """Set the state of a light."""
        lights = [{"id": light_id, "level": level, "time": time}]
        await self.api.async_set_light_state(lights)

    async def async_recall_scene(self, scene_id: int) -> None:
        """Recall a scene by ID."""
        await self.api.async_recall_scene(scene_id)

    async def async_set_mediaroom_source(self, media_room_id: int, media_source_id: int) -> None:
        """Recall a scene by ID."""
        await self.api.async_set_mediaroom_source(media_room_id, media_source_id)

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.async_close()