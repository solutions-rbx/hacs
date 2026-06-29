"""Diagnostics support for Hermes Assist."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_TOKEN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = dict(entry.data)
    if CONF_API_TOKEN in data:
        data[CONF_API_TOKEN] = "**REDACTED**"

    return {
        "entry": data,
        "options": dict(entry.options),
    }
