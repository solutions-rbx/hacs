"""Hermes Assist integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HermesClient
from .const import DOMAIN, STORAGE_CLIENT

type HermesConfigEntry = ConfigEntry[dict[str, HermesClient]]


def _enabled_platforms(entry: ConfigEntry) -> list[Platform]:
    """Return platforms enabled for this entry."""
    return [Platform.CONVERSATION]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hermes Assist from a config entry."""
    session = async_get_clientsession(hass)
    client = HermesClient(session, dict(entry.data), dict(entry.options))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {STORAGE_CLIENT: client}

    await hass.config_entries.async_forward_entry_setups(entry, _enabled_platforms(entry))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Hermes Assist."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _enabled_platforms(entry))
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
