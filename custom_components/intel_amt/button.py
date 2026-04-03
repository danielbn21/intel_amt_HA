"""Button platform for Intel AMT integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AMTDataUpdateCoordinator
from .amt_client import AMTClient
from .const import DOMAIN
from .entity import AMTBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class AMTButtonDescription(ButtonEntityDescription):
    """Describes an Intel AMT button entity."""
    press_fn: Callable[[AMTClient], Awaitable[bool]] | None = None
    icon: str = "mdi:power"
    unique_id_suffix: str = ""


BUTTON_DESCRIPTIONS: tuple[AMTButtonDescription, ...] = (
    AMTButtonDescription(
        key="power_on",
        name="Power On",
        icon="mdi:power-on",
        unique_id_suffix="btn_power_on",
        press_fn=lambda client: client.async_power_on(),
    ),
    AMTButtonDescription(
        key="power_off_hard",
        name="Power Off (Hard)",
        icon="mdi:power-off",
        unique_id_suffix="btn_power_off_hard",
        press_fn=lambda client: client.async_power_off(),
    ),
    AMTButtonDescription(
        key="power_off_soft",
        name="Shutdown (Graceful)",
        icon="mdi:power-sleep",
        unique_id_suffix="btn_power_off_soft",
        press_fn=lambda client: client.async_soft_power_off(),
    ),
    AMTButtonDescription(
        key="reset_hard",
        name="Reset (Hard)",
        icon="mdi:restart-alert",
        unique_id_suffix="btn_reset_hard",
        press_fn=lambda client: client.async_reset(),
    ),
    AMTButtonDescription(
        key="reset_soft",
        name="Reboot (Graceful)",
        icon="mdi:restart",
        unique_id_suffix="btn_reset_soft",
        press_fn=lambda client: client.async_soft_reset(),
    ),
    AMTButtonDescription(
        key="power_cycle",
        name="Power Cycle",
        icon="mdi:power-cycle",
        unique_id_suffix="btn_power_cycle",
        press_fn=lambda client: client.async_power_cycle(),
    ),
    AMTButtonDescription(
        key="hibernate",
        name="Hibernate",
        icon="mdi:weather-night",
        unique_id_suffix="btn_hibernate",
        press_fn=lambda client: client.async_hibernate(),
    ),
    AMTButtonDescription(
        key="nmi",
        name="Send NMI",
        icon="mdi:bug",
        unique_id_suffix="btn_nmi",
        press_fn=lambda client: client.async_nmi(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intel AMT buttons."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AMTDataUpdateCoordinator = data["coordinator"]
    client: AMTClient = data["client"]

    async_add_entities(
        AMTPowerButton(coordinator, client, entry.entry_id, description)
        for description in BUTTON_DESCRIPTIONS
    )


class AMTPowerButton(AMTBaseEntity, ButtonEntity):
    """A button entity that sends a specific AMT power command."""

    entity_description: AMTButtonDescription

    def __init__(
        self,
        coordinator: AMTDataUpdateCoordinator,
        client: AMTClient,
        entry_id: str,
        description: AMTButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry_id, description.unique_id_suffix)
        self.entity_description = description
        self._client = client
        self._attr_name = description.name
        self._attr_icon = description.icon

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.entity_description.press_fn(self._client)
            _LOGGER.debug(
                "AMT command '%s' sent to %s",
                self.entity_description.key,
                self._client.host,
            )
            # Refresh state after a command
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error(
                "Failed to execute AMT command '%s' on %s: %s",
                self.entity_description.key,
                self._client.host,
                err,
            )
