"""Switch platform for Intel AMT integration — master power toggle."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AMTDataUpdateCoordinator
from .amt_client import AMTClient
from .const import DOMAIN
from .entity import AMTBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intel AMT switch."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AMTDataUpdateCoordinator = data["coordinator"]
    client: AMTClient = data["client"]

    async_add_entities([AMTPowerSwitch(coordinator, client, entry.entry_id)])


class AMTPowerSwitch(AMTBaseEntity, SwitchEntity):
    """Switch entity: turn the machine on (hard power on) or off (hard power off)."""

    _attr_name = "Power Switch"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:power"

    def __init__(
        self,
        coordinator: AMTDataUpdateCoordinator,
        client: AMTClient,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry_id, "power_switch")
        self._client = client

    @property
    def is_on(self) -> bool | None:
        """Return True if the system is powered on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("is_on", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the system on."""
        try:
            await self._client.async_power_on()
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to power on %s: %s", self._client.host, err)

    async def async_turn_off(self, **kwargs) -> None:
        """Hard power off the system."""
        try:
            await self._client.async_power_off()
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to power off %s: %s", self._client.host, err)
