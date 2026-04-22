"""Telldus Live (custom) integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TelldusLiveClient
from .const import (
    CONF_PRIVATE_KEY,
    CONF_PUBLIC_KEY,
    CONF_TOKEN,
    CONF_TOKEN_SECRET,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import TelldusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Telldus Live from a config entry."""
    session = async_get_clientsession(hass)
    client = TelldusLiveClient(
        session,
        public_key=entry.data[CONF_PUBLIC_KEY],
        private_key=entry.data[CONF_PRIVATE_KEY],
        token=entry.data[CONF_TOKEN],
        token_secret=entry.data[CONF_TOKEN_SECRET],
    )
    coordinator = TelldusDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
