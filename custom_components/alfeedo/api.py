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
        """Get all device data: status + motor settings + fillsensor settings."""
        logging.debug("AlfeedoApiClient: Fetching data from host %s", self._host)

        # Haal alle endpoints parallel op
        status, motor, fillsensor = await asyncio.gather(
            self._api_wrapper(method="get", url=f"http://{self._host}:80/api/status"),
            self._api_wrapper(method="get", url=f"http://{self._host}:80/api/settings/motor"),
            self._api_wrapper(method="get", url=f"http://{self._host}:80/api/settings/fillsensor"),
            return_exceptions=True,
        )

        # Begin met status als basis
        result = status if isinstance(status, dict) else {}

        # Voeg motor settings toe (met prefix om conflicten te vermijden)
        if isinstance(motor, dict):
            result.update(motor)

        # Voeg fillsensor settings toe
        if isinstance(fillsensor, dict):
            result.update(fillsensor)

        return result

    async def async_feed(self, mode: str) -> Any:
        """Send feed command to the device."""
        url = f"http://{self._host}:80/api/feed"
        return await self._api_wrapper(
            method="post",
            url=url,
            data={"mode": mode},
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
