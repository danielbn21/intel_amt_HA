"""Base entity for Intel AMT integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AMTDataUpdateCoordinator
from .const import CONF_HOST, CONF_PORT, DOMAIN, MANUFACTURER


class AMTBaseEntity(CoordinatorEntity):
    """Base class for all Intel AMT entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AMTDataUpdateCoordinator,
        entry_id: str,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        host = coordinator.client.host
        port = coordinator.client.port
        self._attr_unique_id = f"{entry_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{port}")},
            name=f"Intel AMT – {host}",
            manufacturer=MANUFACTURER,
            model="Intel vPro / AMT",
            configuration_url=(
                f"{'https' if coordinator.client.tls else 'http'}://{host}:{port}"
            ),
        )
