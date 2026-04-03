"""Sensor platform for Intel AMT integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AMTDataUpdateCoordinator
from .const import DOMAIN
from .entity import AMTBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intel AMT sensors."""
    coordinator: AMTDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        [
            AMTPowerStateSensor(coordinator, entry.entry_id),
            AMTPowerStateCodeSensor(coordinator, entry.entry_id),
        ]
    )


class AMTPowerStateSensor(AMTBaseEntity, SensorEntity):
    """Sensor showing the human-readable power state."""

    _attr_name = "Power State"
    _attr_icon = "mdi:power-settings"

    def __init__(self, coordinator: AMTDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, "power_state_text")

    @property
    def native_value(self) -> str | None:
        """Return the current power state as a string."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("power_state", "Unknown")

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return {}
        return {
            "power_state_code": self.coordinator.data.get("power_state_code"),
            "requested_state": self.coordinator.data.get("requested_state"),
            "host": self.coordinator.client.host,
            "port": self.coordinator.client.port,
        }


class AMTPowerStateCodeSensor(AMTBaseEntity, SensorEntity):
    """Sensor showing the raw CIM power state code."""

    _attr_name = "Power State Code"
    _attr_icon = "mdi:numeric"
    _attr_entity_registry_enabled_default = False  # hidden by default, advanced

    def __init__(self, coordinator: AMTDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, "power_state_code")

    @property
    def native_value(self) -> int | None:
        """Return the raw CIM power state code."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("power_state_code")
