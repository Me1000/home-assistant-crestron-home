"""Crestron Home API client."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import async_timeout

from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

API_TIMEOUT = 30
AUTH_REFRESH_INTERVAL = 540  # 9 minutes


class CrestronAPI:
    """Crestron Home API client."""

    def __init__(self, host: str, api_token: str) -> None:
        """Initialize the API client."""
        self.host = host
        self.api_token = api_token
        self.auth_key: str | None = None
        self.auth_expires: datetime | None = None
        self._session: aiohttp.ClientSession | None = None

    @property
    def base_url(self) -> str:
        """Return the base URL for the API."""
        return f"https://{self.host}/cws/api"

    async def async_authenticate(self) -> None:
        """Authenticate with the Crestron Home API."""
        if self.auth_key and self.auth_expires and datetime.now() < self.auth_expires:
            return

        headers = {"Crestron-RestAPI-AuthToken": self.api_token}
        
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._get_session().get(
                    f"{self.base_url}/login", headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.auth_key = data.get("authkey")
                        self.auth_expires = datetime.now() + timedelta(seconds=AUTH_REFRESH_INTERVAL)
                        _LOGGER.debug("Authentication successful")
                    else:
                        _LOGGER.error("Authentication failed: %s", response.status)
                        raise CrestronAuthError(f"Authentication failed: {response.status}")
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout during authentication")
            raise CrestronConnectionError("Authentication timeout") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error during authentication: %s", err)
            raise CrestronConnectionError(f"Connection error: {err}") from err

    async def async_get_lights(self) -> dict[str, Any]:
        """Get all lights from the Crestron Home system."""
        return await self._make_authenticated_request("GET", "/lights")

    async def async_get_sensors(self) -> dict[str, Any]:
        """Get all sensors from the Crestron Home system."""
        return await self._make_authenticated_request("GET", "/sensors")

    async def async_get_scenes(self) -> dict[str, Any]:
        """Get all scenes from the Crestron Home system."""
        return await self._make_authenticated_request("GET", "/scenes")

    async def async_set_light_state(self, lights: list[dict[str, Any]]) -> dict[str, Any]:
        """Set the state of one or more lights."""
        payload = {"lights": lights}
        return await self._make_authenticated_request("POST", "/lights/SetState", json=payload)

    async def async_recall_scene(self, scene_id: int) -> dict[str, Any]:
        """Recall a scene by ID."""
        return await self._make_authenticated_request("POST", f"/scenes/recall/{scene_id}")

    async def _make_authenticated_request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Make an authenticated request with automatic retry on auth failure."""
        for attempt in range(2):  # Try twice: once with existing auth, once after refresh
            await self.async_authenticate()
            
            headers = kwargs.pop("headers", {})
            headers["Crestron-RestAPI-AuthKey"] = self.auth_key
            
            if method == "POST":
                headers["Content-Type"] = "application/json"
            
            try:
                async with async_timeout.timeout(API_TIMEOUT):
                    async with self._get_session().request(
                        method, f"{self.base_url}{path}", headers=headers, **kwargs
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 401 and attempt == 0:
                            # Auth failed, force refresh and retry
                            _LOGGER.warning("Auth token expired, refreshing and retrying")
                            self.auth_key = None
                            self.auth_expires = None
                            continue
                        else:
                            _LOGGER.error("API request failed: %s %s - %s", method, path, response.status)
                            raise CrestronAPIError(f"API request failed: {response.status}")
            except asyncio.TimeoutError as err:
                _LOGGER.error("Timeout during API request: %s %s", method, path)
                raise CrestronConnectionError(f"Request timeout: {method} {path}") from err
            except aiohttp.ClientError as err:
                _LOGGER.error("Connection error during API request: %s %s - %s", method, path, err)
                raise CrestronConnectionError(f"Connection error: {err}") from err
        
        raise CrestronAPIError("Failed to complete request after retry")

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None:
            connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def async_close(self) -> None:
        """Close the API session."""
        if self._session:
            await self._session.close()
            self._session = None


class CrestronError(HomeAssistantError):
    """Base exception for Crestron Home errors."""


class CrestronConnectionError(CrestronError):
    """Exception for connection errors."""


class CrestronAuthError(CrestronError):
    """Exception for authentication errors."""


class CrestronAPIError(CrestronError):
    """Exception for API errors."""