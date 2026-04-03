"""Binary sensor platform for Intel AMT integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up Intel AMT binary sensors."""
    coordinator: AMTDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([AMTPowerBinarySensor(coordinator, entry.entry_id)])


class AMTPowerBinarySensor(AMTBaseEntity, BinarySensorEntity):
    """Binary sensor: True when system is powered on (state == 2)."""

    _attr_name = "Power"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, coordinator: AMTDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id, "is_on")

    @property
    def is_on(self) -> bool | None:
        """Return True if the system is powered on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("is_on", False)
