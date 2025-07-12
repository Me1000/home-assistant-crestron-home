"""DataUpdateCoordinator for Crestron Home."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CrestronAPI, CrestronError
from .const import CONF_API_TOKEN, CONF_POLL_SENSORS, CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL, DOMAIN

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

    async def async_set_light_state(self, light_id: int, level: int, time: int = 0) -> None:
        """Set the state of a light."""
        lights = [{"id": light_id, "level": level, "time": time}]
        await self.api.async_set_light_state(lights)

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.async_close()