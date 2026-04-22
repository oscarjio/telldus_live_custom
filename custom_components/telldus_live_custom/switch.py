"""Switch platform — one entity per on/off-capable Telldus device."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, METHOD_TURNOFF, METHOD_TURNON
from .coordinator import TelldusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TelldusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new_entities: list[TelldusLiveSwitch] = []
        for dev_id, dev in (coordinator.data or {}).get("devices", {}).items():
            methods = int(dev.get("methods") or 0)
            # Only expose devices that can at least turn on+off as switches.
            if not (methods & METHOD_TURNON and methods & METHOD_TURNOFF):
                continue
            if dev_id in known:
                continue
            known.add(dev_id)
            new_entities.append(TelldusLiveSwitch(coordinator, dev_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class TelldusLiveSwitch(
    CoordinatorEntity[TelldusDataUpdateCoordinator], SwitchEntity
):
    """A Telldus on/off device."""

    _attr_has_entity_name = True
    _attr_name = None  # Use device name as entity name

    def __init__(
        self, coordinator: TelldusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"telldus_switch_{device_id}"

    @property
    def _device(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get("devices", {}).get(self._device_id)

    @property
    def available(self) -> bool:
        dev = self._device
        if not super().available or dev is None:
            return False
        # "state" == 2 means "turned off with no known last state" in practice;
        # we still consider it available. Treat only missing devices as unavailable.
        return True

    @property
    def is_on(self) -> bool | None:
        dev = self._device
        if not dev:
            return None
        # Telldus state codes: 1 = ON, 2 = OFF, 16 = DIM (level in statevalue).
        state = dev.get("state")
        if state is None:
            return None
        try:
            state = int(state)
        except (TypeError, ValueError):
            return None
        if state == METHOD_TURNON or state == 16:  # DIM counts as "on"
            return True
        if state == METHOD_TURNOFF:
            return False
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_turn_on(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_turn_off(self._device_id)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        dev = self._device or {}
        return DeviceInfo(
            identifiers={(DOMAIN, f"device:{self._device_id}")},
            name=dev.get("name") or f"Telldus device {self._device_id}",
            manufacturer="Telldus",
            model=dev.get("protocol") or "Device",
            via_device=(DOMAIN, f"client:{dev.get('clientName', 'telldus')}"),
        )
