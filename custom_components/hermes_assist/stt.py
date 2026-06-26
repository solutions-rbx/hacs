"""Speech-to-text platform for Hermes Assist."""

from __future__ import annotations

import logging

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HermesClient, HermesError
from .const import DOMAIN, STORAGE_CLIENT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hermes Assist STT entity."""
    client: HermesClient = hass.data[DOMAIN][entry.entry_id][STORAGE_CLIENT]
    async_add_entities([HermesSttEntity(entry.entry_id, client)])


class HermesSttEntity(SpeechToTextEntity):
    """Hermes speech-to-text provider."""

    _attr_name = "Hermes Assist STT"
    _attr_has_entity_name = False

    def __init__(self, entry_id: str, client: HermesClient) -> None:
        """Initialize the STT entity."""
        self._attr_unique_id = f"{entry_id}_stt"
        self._client = client

    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return [self._client.default_language]

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return supported audio formats."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return supported audio codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return supported bit rates."""
        return [AudioBitRates.BIT_RATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return supported sample rates."""
        return [AudioSampleRates.SAMPLE_RATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return supported channels."""
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self,
        metadata: SpeechMetadata,
        stream,
    ) -> SpeechResult:
        """Process an audio stream through Hermes STT."""
        audio = bytearray()
        async for chunk in stream:
            audio.extend(chunk)

        language = metadata.language or self._client.default_language

        try:
            text = await self._client.async_stt(bytes(audio), language)
        except HermesError:
            _LOGGER.exception("Hermes STT failed")
            return SpeechResult(None, SpeechResultState.ERROR)

        return SpeechResult(text, SpeechResultState.SUCCESS)

