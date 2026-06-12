"""
Custom integration to integrate alfeedo with Home Assistant.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from pathlib import Path
import json

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_HOST, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers import config_validation as cv

from .api import AlfeedoApiClient
from .const import DOMAIN, LOGGER
from .coordinator import AlfeedoDataUpdateCoordinator
from .data import AlfeedoData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .data import AlfeedoConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
]

URL_BASE = "/alfeedo/ui"

SERVICE_ADD_TIMER = "add_timer"
SERVICE_DELETE_TIMER = "delete_timer"

SERVICE_ADD_TIMER_SCHEMA = vol.Schema(
    {
        vol.Required("time"): cv.string,
        vol.Required("mode"): vol.In(["meal", "snack"]),
    }
)

SERVICE_DELETE_TIMER_SCHEMA = vol.Schema(
    {
        vol.Required("timer_id"): vol.Coerce(int),
    }
)


def _get_version() -> str:
    """Lees versienummer uit manifest.json."""
    manifest_path = Path(__file__).parent / "manifest.json"
    try:
        with open(manifest_path) as f:
            return json.load(f).get("version", "1")
    except Exception:
        return "1"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alfeedo component globally and register static paths."""
    card_path = Path(__file__).parent / "card"

    await hass.http.async_register_static_paths(
        [StaticPathConfig(url_path=URL_BASE, path=str(card_path), cache_headers=False)]
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlfeedoConfigEntry,
) -> bool:
    """Set up alfeedo from a config entry."""
    coordinator = AlfeedoDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=30),
    )

    entry.runtime_data = AlfeedoData(
        client=AlfeedoApiClient(
            host=entry.data[CONF_HOST],
            session=async_get_clientsession(hass),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await _register_lovelace_resource(hass)
    _register_services(hass, entry)

    return True


def _register_services(hass: HomeAssistant, entry: "AlfeedoConfigEntry") -> None:
    """Register timer services."""

    async def handle_add_timer(call: ServiceCall) -> None:
        time = call.data["time"]
        mode = call.data["mode"]
        client = entry.runtime_data.client
        await client.async_add_timer(time_h_m=time, mode=mode)
        await entry.runtime_data.coordinator.async_request_refresh()
        LOGGER.info("Timer toegevoegd: %s %s", time, mode)

    async def handle_delete_timer(call: ServiceCall) -> None:
        timer_id = call.data["timer_id"]
        client = entry.runtime_data.client
        await client.async_delete_timer(timer_id=timer_id)
        await entry.runtime_data.coordinator.async_request_refresh()
        LOGGER.info("Timer verwijderd: id=%s", timer_id)

    if not hass.services.has_service(DOMAIN, SERVICE_ADD_TIMER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_TIMER,
            handle_add_timer,
            schema=SERVICE_ADD_TIMER_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_TIMER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DELETE_TIMER,
            handle_delete_timer,
            schema=SERVICE_DELETE_TIMER_SCHEMA,
        )


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AlfeedoConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    hass.services.async_remove(DOMAIN, SERVICE_ADD_TIMER)
    hass.services.async_remove(DOMAIN, SERVICE_DELETE_TIMER)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: AlfeedoConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _register_lovelace_resource(hass: HomeAssistant):
    """Register the custom card as a Lovelace resource, with version from manifest."""
    resources = hass.data.get("lovelace", {}).resources

    if not resources or not hasattr(resources, "async_create_item"):
        return

    version = _get_version()
    url = f"{URL_BASE}/ha-alfeedo.js?v={version}"
    old_url_prefix = f"{URL_BASE}/ha-alfeedo.js"

    # Verwijder oude resource als versie verschilt
    for res in list(resources.async_items()):
        if res.get("url", "").startswith(old_url_prefix) and res.get("url") != url:
            LOGGER.info("Verwijder oude Alfeedo resource: %s", res.get("url"))
            await resources.async_delete_item(res["id"])

    # Voeg nieuwe resource toe als die nog niet bestaat
    if not any(res.get("url") == url for res in resources.async_items()):
        LOGGER.info("Registering Alfeedo card resource at %s", url)
        await resources.async_create_item({"res_type": "module", "url": url})
