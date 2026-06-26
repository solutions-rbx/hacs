"""Hermes Assist integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HermesClient
from .const import (
    CONF_ENABLE_CONVERSATION,
    CONF_ENABLE_STT,
    CONF_ENABLE_TTS,
    DOMAIN,
    STORAGE_CLIENT,
)

type HermesConfigEntry = ConfigEntry[dict[str, HermesClient]]


def _enabled_platforms(entry: ConfigEntry) -> list[Platform]:
    """Return platforms enabled for this entry."""
    enabled: list[Platform] = []

    if entry.data.get(CONF_ENABLE_CONVERSATION, True):
        enabled.append(Platform.CONVERSATION)
    if entry.data.get(CONF_ENABLE_STT, False):
        enabled.append(Platform.STT)
    if entry.data.get(CONF_ENABLE_TTS, False):
        enabled.append(Platform.TTS)

    return enabled


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
