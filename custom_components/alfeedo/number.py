"""Number platform voor alfeedo — motor- en fillsensor instellingen."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import aiohttp

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.helpers.entity import EntityCategory

from .const import LOGGER
from .entity import AlfeedoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from .coordinator import AlfeedoDataUpdateCoordinator
    from .data import AlfeedoConfigEntry


MOTOR_NUMBERS = (
    {
        "description": NumberEntityDescription(
            key="speed",
            name="Motor Speed",
            icon="mdi:speedometer",
            native_min_value=0.1,
            native_max_value=1.0,
            native_step=0.05,
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.SLIDER,
        ),
        "api_key": "speed",
        "endpoint": "motor",
    },
    {
        "description": NumberEntityDescription(
            key="revolutionsPerPortion",
            name="Meal Size (revolutions)",
            icon="mdi:food-drumstick-outline",
            native_min_value=0.1,
            native_max_value=10.0,
            native_step=0.1,
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.SLIDER,
        ),
        "api_key": "revolutionsPerPortion",
        "endpoint": "motor",
    },
    {
        "description": NumberEntityDescription(
            key="revolutionsPerSnack",
            name="Snack Size (revolutions)",
            icon="mdi:food-apple-outline",
            native_min_value=0.1,
            native_max_value=10.0,
            native_step=0.1,
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.SLIDER,
        ),
        "api_key": "revolutionsPerSnack",
        "endpoint": "motor",
    },
)

FILLSENSOR_NUMBERS = (
    {
        "description": NumberEntityDescription(
            key="fullMeasurement",
            name="Fill Sensor — Full (mm)",
            icon="mdi:cup",
            native_min_value=0,
            native_max_value=100,
            native_step=1,
            native_unit_of_measurement="mm",
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.BOX,
        ),
        "api_key": "fullMeasurement",
        "endpoint": "fillsensor",
    },
    {
        "description": NumberEntityDescription(
            key="emptyMeasurement",
            name="Fill Sensor — Empty (mm)",
            icon="mdi:cup-off-outline",
            native_min_value=100,
            native_max_value=400,
            native_step=1,
            native_unit_of_measurement="mm",
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.BOX,
        ),
        "api_key": "emptyMeasurement",
        "endpoint": "fillsensor",
    },
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlfeedoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client

    entities = []
    for item in (*MOTOR_NUMBERS, *FILLSENSOR_NUMBERS):
        entities.append(
            AlfeedoNumber(
                coordinator=coordinator,
                client=client,
                entity_description=item["description"],
                api_key=item["api_key"],
                endpoint=item["endpoint"],
            )
        )
    async_add_entities(entities)


class AlfeedoNumber(AlfeedoEntity, NumberEntity):
    """Instelbare waarde — leest uit coordinator, schrijft naar ESP32 API."""

    def __init__(
        self,
        coordinator: AlfeedoDataUpdateCoordinator,
        client: Any,
        entity_description: NumberEntityDescription,
        api_key: str,
        endpoint: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._client = client
        self._api_key = api_key
        self._endpoint = endpoint

        entry_uid = (
            getattr(coordinator.config_entry, "unique_id", None)
            or coordinator.config_entry.entry_id
        )
        self._attr_unique_id = f"{entry_uid}_{entity_description.key}"

    @property
    def native_value(self) -> float | None:
        """Waarde komt nu rechtstreeks uit de coordinator data."""
        value = self.coordinator.data.get(self._api_key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Stuur de nieuwe waarde naar de ESP32 en refresh coordinator."""
        try:
            host = self._client._host
            url = f"http://{host}:80/api/settings/{self._endpoint}"
            async with self._client._session.post(
                url,
                json={self._api_key: value},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    LOGGER.debug("Instelling %s gezet op %s", self._api_key, value)
                    # Refresh coordinator zodat alle sliders bijwerken
                    await self.coordinator.async_request_refresh()
                else:
                    LOGGER.warning("ESP32 weigerde instelling %s: HTTP %s", self._api_key, resp.status)
        except Exception as err:
            LOGGER.error("Fout bij instellen van %s: %s", self._api_key, err)
