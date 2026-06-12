"""Button platform for alfeedo (momentary feed action + reset)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from .const import DOMAIN, LOGGER

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers.entity import EntityCategory

from .entity import AlfeedoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AlfeedoDataUpdateCoordinator
    from .data import AlfeedoConfigEntry

FEED_DESCRIPTIONS = (
    ButtonEntityDescription(
        key="meal",
        name="Feed Meal",
        icon="mdi:food-drumstick-outline",
    ),
    ButtonEntityDescription(
        key="snack",
        name="Feed Snack",
        icon="mdi:food-apple-outline",
    ),
)

RESET_DESCRIPTIONS = (
    ButtonEntityDescription(
        key="reset",
        name="Restart Feeder",
        icon="mdi:restart",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlfeedoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client

    async_add_entities(
        AlfeedoFeedButton(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in FEED_DESCRIPTIONS
    )
    async_add_entities(
        AlfeedoResetButton(
            coordinator=coordinator,
            client=client,
            entity_description=entity_description,
        )
        for entity_description in RESET_DESCRIPTIONS
    )


class AlfeedoFeedButton(AlfeedoEntity, ButtonEntity):
    def __init__(
        self,
        coordinator: AlfeedoDataUpdateCoordinator,
        entity_description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        entry_uid = (
            getattr(coordinator.config_entry, "unique_id", None)
            or coordinator.config_entry.entry_id
        )
        key = getattr(entity_description, "key", None)
        self._attr_unique_id = f"{entry_uid}_{key}" if key else f"{entry_uid}"

    async def async_press(self, **_: Any) -> None:
        """Stuur een voederopdracht naar de ESP32."""
        client = self.coordinator.config_entry.runtime_data.client
        mode = getattr(self.entity_description, "key", None)
        logging.debug("AlfeedoFeedButton: Button %s pressed", mode)
        await client.async_feed(mode)
        await self.coordinator.async_start_burst_refresh()


class AlfeedoResetButton(AlfeedoEntity, ButtonEntity):
    """Knop om de ESP32 te herstarten via de reset API."""

    def __init__(
        self,
        coordinator: AlfeedoDataUpdateCoordinator,
        client: Any,
        entity_description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._client = client

        entry_uid = (
            getattr(coordinator.config_entry, "unique_id", None)
            or coordinator.config_entry.entry_id
        )
        self._attr_unique_id = f"{entry_uid}_reset"

    async def async_press(self, **_: Any) -> None:
        """Stuur reset commando naar de ESP32."""
        try:
            host = self._client._host
            url = f"http://{host}:80/api/reset"
            async with self._client._session.post(url, timeout=10) as resp:
                if resp.status == 200:
                    LOGGER.info("ESP32 herstart gestuurd")
                else:
                    LOGGER.warning("Reset mislukt: HTTP %s", resp.status)
        except Exception as err:
            LOGGER.error("Fout bij reset: %s", err)
