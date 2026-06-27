"""Diagnostics support for Hermes Assist."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_TOKEN, CONF_STT_API_TOKEN, CONF_TTS_API_TOKEN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = dict(entry.data)
    for key in (CONF_API_TOKEN, CONF_STT_API_TOKEN, CONF_TTS_API_TOKEN):
        if key in data:
            data[key] = "**REDACTED**"

    return {
        "entry": data,
        "options": {
            key: "**REDACTED**" if key in (CONF_STT_API_TOKEN, CONF_TTS_API_TOKEN) else value
            for key, value in dict(entry.options).items()
        },
    }
