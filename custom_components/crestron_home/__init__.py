"""The Crestron Home integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from aiohttp.web import Request, Response
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, config_validation as cv

from .const import DOMAIN, CONF_ENABLE_WEBHOOK, WEBHOOK_ID
from .coordinator import CrestronDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.BINARY_SENSOR, Platform.SCENE]

SERVICE_SET_MEDIA_ROOM_SCHEMA = vol.Schema(
    {
        vol.Required("media_room_id"): cv.positive_int,
        vol.Required("source_id"): cv.positive_int,
    }
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Crestron Home from a config entry."""
    coordinator = CrestronDataUpdateCoordinator(hass, entry)
    
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.exception("Error setting up Crestron Home: %s", err)
        raise ConfigEntryNotReady from err

    # Create the hub device that child devices will reference
    device_registry = dr.async_get(hass)
    host = entry.data[CONF_HOST]
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Crestron",
        model="Home Hub",
        name=f"Crestron Home ({host})",
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Create a callable service action for setting the media room.
    async def handle_set_media_room(call: ServiceCall) -> None:
        media_room_id = call.data["media_room_id"]
        source_id = call.data["source_id"]

        return await coordinator.async_set_mediaroom_source(media_room_id=media_room_id, media_source_id=source_id)

    hass.services.async_register(
        DOMAIN,
        "set_mediaroom_source",
        handle_set_media_room,
        schema=SERVICE_SET_MEDIA_ROOM_SCHEMA,
    )

    # Register webhook for immediate sensor updates
    enable_webhook = entry.options.get(
        CONF_ENABLE_WEBHOOK, entry.data.get(CONF_ENABLE_WEBHOOK, True)
    )
    if enable_webhook:
        webhook.async_register(
            hass,
            DOMAIN,
            "Crestron Sensor Update",
            WEBHOOK_ID,
            handle_webhook,
            allowed_methods=["POST", "PUT", "GET"],
        )
        _LOGGER.info(
            "Crestron webhook registered. URL: /api/webhook/%s", WEBHOOK_ID
        )

    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    return True


async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request
) -> Response:
    """Handle incoming webhook from Crestron."""
    _LOGGER.debug("Received Crestron webhook, forcing sensor refresh")

    coordinators = hass.data.get(DOMAIN, {})
    if not coordinators:
        return Response(text="No coordinator", status=404)

    for coordinator in coordinators.values():
        await coordinator.async_force_sensor_refresh()

    return Response(text="OK", status=200)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    enable_webhook = entry.options.get(
        CONF_ENABLE_WEBHOOK, entry.data.get(CONF_ENABLE_WEBHOOK, True)
    )
    if enable_webhook:
        webhook.async_unregister(hass, WEBHOOK_ID)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: CrestronDataUpdateCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        # Update scene entities based on new configuration
        await coordinator.async_update_scene_entities()


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)