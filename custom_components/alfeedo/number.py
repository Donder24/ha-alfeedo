"""Number platform voor alfeedo — motor- en fillsensor instellingen."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import aiohttp

from homeassistant.components.number import (
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


# Volgorde hier bepaalt de volgorde in HA — reset staat niet hier, die zit in button.py
MOTOR_NUMBERS = (
    {
        "description": NumberEntityDescription(
            key="revolutionsPerPortion",
            name="Meal Size (revolutions)",
            icon="mdi:food-drumstick-outline",
            native_step=0.1,
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.SLIDER,
        ),
        "api_key": "revolutionsPerPortion",
        "endpoint": "motor",
        "min_key": "minRevolutionsPerPortion",
        "max_key": "maxRevolutionsPerPortion",
    },
    {
        "description": NumberEntityDescription(
            key="revolutionsPerSnack",
            name="Snack Size (revolutions)",
            icon="mdi:food-apple-outline",
            native_step=0.1,
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.SLIDER,
        ),
        "api_key": "revolutionsPerSnack",
        "endpoint": "motor",
        "min_key": "minRevolutionsPerPortion",
        "max_key": "maxRevolutionsPerPortion",
    },
    {
        "description": NumberEntityDescription(
            key="speed",
            name="Motor Speed",
            icon="mdi:speedometer",
            native_step=0.05,
            entity_category=EntityCategory.CONFIG,
            mode=NumberMode.SLIDER,
        ),
        "api_key": "speed",
        "endpoint": "motor",
        "min_key": "minSpeed",
        "max_key": "maxSpeed",
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
        "min_key": None,
        "max_key": None,
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
        "min_key": None,
        "max_key": None,
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
                min_key=item["min_key"],
                max_key=item["max_key"],
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
        min_key: str | None,
        max_key: str | None,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._client = client
        self._api_key = api_key
        self._endpoint = endpoint
        self._min_key = min_key
        self._max_key = max_key

        entry_uid = (
            getattr(coordinator.config_entry, "unique_id", None)
            or coordinator.config_entry.entry_id
        )
        self._attr_unique_id = f"{entry_uid}_{entity_description.key}"

    @property
    def native_min_value(self) -> float:
        """Min waarde dynamisch uit coordinator (bv. minSpeed van ESP32)."""
        if self._min_key and self.coordinator.data:
            val = self.coordinator.data.get(self._min_key)
            if val is not None:
                return float(val)
        return self.entity_description.native_min_value or 0.0

    @property
    def native_max_value(self) -> float:
        """Max waarde dynamisch uit coordinator (bv. maxSpeed van ESP32)."""
        if self._max_key and self.coordinator.data:
            val = self.coordinator.data.get(self._max_key)
            if val is not None:
                return float(val)
        return self.entity_description.native_max_value or 100.0

    @property
    def native_value(self) -> float | None:
        """Huidige waarde uit coordinator data."""
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
                    await self.coordinator.async_request_refresh()
                else:
                    LOGGER.warning(
                        "ESP32 weigerde instelling %s: HTTP %s",
                        self._api_key,
                        resp.status,
                    )
        except Exception as err:
            LOGGER.error("Fout bij instellen van %s: %s", self._api_key, err)
