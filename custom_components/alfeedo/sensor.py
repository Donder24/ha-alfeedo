from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import DOMAIN, LOGGER

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.helpers.entity import EntityCategory

from .entity import AlfeedoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AlfeedoDataUpdateCoordinator
    from .data import AlfeedoConfigEntry

ENTITY_STATE_DESCRIPTIONS = {
    SensorEntityDescription(key="state", name="Feeder state", icon="mdi:cat"),
}

ENTITY_FILL_LEVEL_DESCRIPTIONS = (
    SensorEntityDescription(
        key="fill_level",
        name="Feeder Fill Level",
        icon="mdi:cup",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

ENTITY_DIAGNOSTIC_DESCRIPTIONS = (
    SensorEntityDescription(
        key="wifiRssi",
        name="WiFi Signal Strength",
        icon="mdi:wifi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="wifiSsid",
        name="WiFi SSID",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="ipAddress",
        name="IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="freeHeap",
        name="Free Heap Memory",
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="firmwareVersion",
        name="Firmware Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: AlfeedoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    LOGGER.debug("alfeedo.sensor: async_setup_entry for entry %s", entry.entry_id)
    async_add_entities(
        AlfeedoStateSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_STATE_DESCRIPTIONS
    )
    async_add_entities(
        AlfeedoFillLevelSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_FILL_LEVEL_DESCRIPTIONS
    )
    async_add_entities(
        AlfeedoDiagnosticSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DIAGNOSTIC_DESCRIPTIONS
    )


class AlfeedoStateSensor(AlfeedoEntity, SensorEntity):
    _attr_icon = "mdi:cat"

    def __init__(
        self,
        coordinator: AlfeedoDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry_uid = (
            getattr(coordinator.config_entry, "unique_id", None)
            or coordinator.config_entry.entry_id
        )
        key = getattr(entity_description, "key", None)
        self._attr_unique_id = f"{entry_uid}_{key}" if key else f"{entry_uid}"
        LOGGER.debug("alfeedo.sensor: created sensor entity %s", self._attr_unique_id)

    @property
    def native_value(self) -> str | None:
        value = self.coordinator.data.get("state")
        if value is None:
            return None
        try:
            return value
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "fill_level": self.coordinator.data.get("fillLevel"),
            "error_state": self.coordinator.data.get("errorState"),
            "next_timer": self.coordinator.data.get("nextTimer", {}).get("time"),
            "next_timer_mode": self.coordinator.data.get("nextTimer", {}).get("mode"),
        }


class AlfeedoFillLevelSensor(AlfeedoEntity, SensorEntity):
    def __init__(
        self,
        coordinator: AlfeedoDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry_uid = (
            getattr(coordinator.config_entry, "unique_id", None)
            or coordinator.config_entry.entry_id
        )
        key = getattr(entity_description, "key", None)
        self._attr_unique_id = f"{entry_uid}_{key}" if key else f"{entry_uid}"
        LOGGER.debug("alfeedo.sensor: created sensor entity %s", self._attr_unique_id)

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get("fillLevel")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class AlfeedoDiagnosticSensor(AlfeedoEntity, SensorEntity):
    """Generieke sensor voor diagnostische waarden van de ESP32."""

    def __init__(
        self,
        coordinator: AlfeedoDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry_uid = (
            getattr(coordinator.config_entry, "unique_id", None)
            or coordinator.config_entry.entry_id
        )
        self._attr_unique_id = f"{entry_uid}_{entity_description.key}"
        LOGGER.debug("alfeedo.sensor: created diagnostic sensor entity %s", self._attr_unique_id)

    @property
    def native_value(self) -> str | int | float | None:
        return self.coordinator.data.get(self.entity_description.key)
