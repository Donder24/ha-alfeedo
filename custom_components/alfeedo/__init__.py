"""
Custom integration to integrate alfeedo with Home Assistant.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import StaticPathConfig

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
    Platform.NUMBER,   # ← nieuw: motor- en fillsensor instellingen
]

URL_BASE = "/alfeedo/ui"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alfeedo component globally and register static paths."""
    card_path = Path(__file__).parent / "card"

    await hass.http.async_register_static_paths(
        [StaticPathConfig(url_path=URL_BASE, path=str(card_path), cache_headers=True)]
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

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AlfeedoConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: AlfeedoConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _register_lovelace_resource(hass: HomeAssistant):
    """Register the custom card as a Lovelace resource."""
    resources = hass.data.get("lovelace", {}).resources

    if not resources or not hasattr(resources, "async_create_item"):
        return

    url = f"{URL_BASE}/ha-alfeedo.js"

    if not any(res.get("url") == url for res in resources.async_items()):
        LOGGER.info("Registering Alfeedo card resource at %s", url)
        await resources.async_create_item(
            {
                "res_type": "module",
                "url": url,
            }
        )
