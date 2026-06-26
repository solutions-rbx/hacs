"""Text-to-speech platform for Hermes Assist."""

from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HermesClient, HermesError
from .const import DOMAIN, STORAGE_CLIENT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hermes Assist TTS entity."""
    client: HermesClient = hass.data[DOMAIN][entry.entry_id][STORAGE_CLIENT]
    async_add_entities([HermesTtsEntity(entry.entry_id, client)])


class HermesTtsEntity(TextToSpeechEntity):
    """Hermes text-to-speech provider."""

    _attr_name = "Hermes Assist TTS"
    _attr_has_entity_name = False

    def __init__(self, entry_id: str, client: HermesClient) -> None:
        """Initialize the TTS entity."""
        self._attr_unique_id = f"{entry_id}_tts"
        self._client = client

    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return [self._client.default_language]

    @property
    def default_language(self) -> str:
        """Return default language."""
        return self._client.default_language

    @property
    def supported_options(self) -> list[str]:
        """Return supported options."""
        return ["voice"]

    @property
    def default_options(self) -> dict[str, Any]:
        """Return default options."""
        return {}

    @callback
    def async_get_supported_voices(self, language: str) -> list[str] | None:
        """Return supported voices."""
        return None

    async def async_get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any],
    ) -> TtsAudioType:
        """Load TTS audio from Hermes."""
        try:
            response = await self._client.async_tts(message, language, options)
        except HermesError:
            _LOGGER.exception("Hermes TTS failed")
            return None

        return response.extension, response.data

