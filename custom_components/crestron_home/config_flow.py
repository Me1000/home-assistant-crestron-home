"""Config flow for Crestron Home integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import CrestronAPI, CrestronAuthError, CrestronConnectionError
from .const import (
    CONF_API_TOKEN,
    CONF_IMPORT_GENERIC_IO_SCENES,
    CONF_IMPORT_LIGHT_SCENES,
    CONF_IMPORT_MEDIA_SCENES,
    CONF_POLL_SENSORS,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)

# New option keys for separate intervals (keep them in const.py if you prefer)
CONF_GENERAL_POLLING_INTERVAL = "general_polling_interval"
CONF_SENSOR_POLLING_INTERVAL = "sensor_polling_interval"

DEFAULT_GENERAL_POLLING_INTERVAL = DEFAULT_POLLING_INTERVAL
DEFAULT_SENSOR_POLLING_INTERVAL = DEFAULT_POLLING_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_API_TOKEN): str,
        # Backward-compatible: keep original polling interval in the initial flow
        vol.Optional(CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=300)
        ),
        vol.Optional(CONF_POLL_SENSORS, default=False): bool,
        vol.Optional(CONF_IMPORT_MEDIA_SCENES, default=False): bool,
        vol.Optional(CONF_IMPORT_LIGHT_SCENES, default=False): bool,
        vol.Optional(CONF_IMPORT_GENERIC_IO_SCENES, default=True): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = CrestronAPI(data[CONF_HOST], data[CONF_API_TOKEN])

    try:
        await api.async_authenticate()
        lights = await api.async_get_lights()
    except CrestronAuthError as err:
        _LOGGER.exception("Authentication error: %s", err)
        raise InvalidAuth from err
    except CrestronConnectionError as err:
        _LOGGER.exception("Connection error: %s", err)
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Error connecting to Crestron Home: %s", err)
        raise CannotConnect from err

    return {
        "title": f"Crestron Home ({data[CONF_HOST]})",
        "lights_count": len(lights.get("lights", [])),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Crestron Home."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Crestron Home."""

    def __init__(self) -> None:
        """Initialize options flow."""
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        # Migration fallback:
        # - if new keys not set yet, use existing CONF_POLLING_INTERVAL from options/data.
        legacy_interval = self.config_entry.options.get(
            CONF_POLLING_INTERVAL,
            self.config_entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL),
        )

        general_default = self.config_entry.options.get(
            CONF_GENERAL_POLLING_INTERVAL,
            legacy_interval,
        )
        sensor_default = self.config_entry.options.get(
            CONF_SENSOR_POLLING_INTERVAL,
            legacy_interval,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self.config_entry.options.get(
                            CONF_HOST, self.config_entry.data.get(CONF_HOST)
                        ),
                    ): str,
                    vol.Required(
                        CONF_API_TOKEN,
                        default=self.config_entry.options.get(
                            CONF_API_TOKEN, self.config_entry.data.get(CONF_API_TOKEN)
                        ),
                    ): str,
                    vol.Optional(
                        CONF_GENERAL_POLLING_INTERVAL,
                        default=general_default,
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                    vol.Optional(
                        CONF_SENSOR_POLLING_INTERVAL,
                        default=sensor_default,
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                    vol.Optional(
                        CONF_POLL_SENSORS,
                        default=self.config_entry.options.get(
                            CONF_POLL_SENSORS,
                            self.config_entry.data.get(CONF_POLL_SENSORS, False),
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_IMPORT_MEDIA_SCENES,
                        default=self.config_entry.options.get(
                            CONF_IMPORT_MEDIA_SCENES,
                            self.config_entry.data.get(CONF_IMPORT_MEDIA_SCENES, False),
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_IMPORT_LIGHT_SCENES,
                        default=self.config_entry.options.get(
                            CONF_IMPORT_LIGHT_SCENES,
                            self.config_entry.data.get(CONF_IMPORT_LIGHT_SCENES, False),
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_IMPORT_GENERIC_IO_SCENES,
                        default=self.config_entry.options.get(
                            CONF_IMPORT_GENERIC_IO_SCENES,
                            self.config_entry.data.get(CONF_IMPORT_GENERIC_IO_SCENES, True),
                        ),
                    ): bool,
                }
            ),
            errors=errors,
        )
