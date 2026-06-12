"""Sample API Client."""

from __future__ import annotations

import socket
from typing import Any

import aiohttp
import async_timeout

import asyncio
import logging

_LOGGER = logging.getLogger(__package__)


class AlfeedoApiClientError(Exception):
    """Exception to indicate a general API error."""


class AlfeedoApiClientCommunicationError(
    AlfeedoApiClientError,
):
    """Exception to indicate a communication error."""


class AlfeedoApiClientAuthenticationError(
    AlfeedoApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise AlfeedoApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


class AlfeedoApiClient:
    """Sample API Client."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._host = host
        self._session = session

    async def async_get_data(self) -> Any:
        """Get all device data: status + motor settings + fillsensor settings + timers."""
        logging.debug("AlfeedoApiClient: Fetching data from host %s", self._host)

        status, motor, fillsensor, timers = await asyncio.gather(
            self._api_wrapper(method="get", url=f"http://{self._host}:80/api/status"),
            self._api_wrapper(method="get", url=f"http://{self._host}:80/api/settings/motor"),
            self._api_wrapper(method="get", url=f"http://{self._host}:80/api/settings/fillsensor"),
            self._api_wrapper(method="get", url=f"http://{self._host}:80/api/timers"),
            return_exceptions=True,
        )

        result = status if isinstance(status, dict) else {}

        if isinstance(motor, dict):
            result.update(motor)

        if isinstance(fillsensor, dict):
            result.update(fillsensor)

        # Timers apart bewaren onder eigen sleutel
        if isinstance(timers, dict):
            result["timers"] = timers.get("timers", [])
            result["maxTimers"] = timers.get("maxTimers", 10)
        else:
            result["timers"] = []
            result["maxTimers"] = 10

        return result

    async def async_feed(self, mode: str) -> Any:
        """Send feed command to the device."""
        url = f"http://{self._host}:80/api/feed"
        return await self._api_wrapper(
            method="post",
            url=url,
            data={"mode": mode},
        )

    async def async_get_timers(self) -> list[dict]:
        """Get all timers from the device."""
        result = await self._api_wrapper(
            method="get",
            url=f"http://{self._host}:80/api/timers",
        )
        return result.get("timers", []) if isinstance(result, dict) else []

    async def async_add_timer(self, time_h_m: str, mode: str) -> Any:
        """Add a timer to the device. time_h_m in format 'HH:MM'."""
        return await self._api_wrapper(
            method="post",
            url=f"http://{self._host}:80/api/timers",
            data={"time_h_m": time_h_m, "mode": mode},
        )

    async def async_delete_timer(self, timer_id: int) -> Any:
        """Delete a timer from the device by ID."""
        url = f"http://{self._host}:80/api/timers?timer_id={timer_id}"
        return await self._api_wrapper(
            method="delete",
            url=url,
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise AlfeedoApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise AlfeedoApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise AlfeedoApiClientError(msg) from exception
