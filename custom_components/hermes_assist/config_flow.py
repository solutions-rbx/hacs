"""Config flow for Hermes Assist."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HermesAuthError, HermesClient, HermesConnectionError, HermesError
from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_CAPABILITIES_PATH,
    CONF_CHAT_COMPLETIONS_PATH,
    CONF_CONVERSATION_API,
    CONF_CONVERSATION_PATH,
    CONF_DEFAULT_LANGUAGE,
    CONF_ENABLE_CONVERSATION,
    CONF_ENABLE_STT,
    CONF_ENABLE_TTS,
    CONF_HEALTH_PATH,
    CONF_MODEL,
    CONF_STT_PATH,
    CONF_TIMEOUT,
    CONF_TTS_AUDIO_FORMAT,
    CONF_TTS_PATH,
    CONF_VOICE_BASE_URL,
    DEFAULT_CAPABILITIES_PATH,
    DEFAULT_CHAT_COMPLETIONS_PATH,
    DEFAULT_CONVERSATION_API,
    DEFAULT_CONVERSATION_PATH,
    DEFAULT_HEALTH_PATH,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_STT_PATH,
    DEFAULT_TIMEOUT,
    DEFAULT_TTS_AUDIO_FORMAT,
    DEFAULT_TTS_PATH,
    DEFAULT_VOICE_BASE_URL,
    DOMAIN,
)


def _options_schema(options: dict[str, Any] | None = None) -> vol.Schema:
    """Build the options schema."""
    options = options or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_HEALTH_PATH,
                default=options.get(CONF_HEALTH_PATH, DEFAULT_HEALTH_PATH),
            ): str,
            vol.Required(
                CONF_CAPABILITIES_PATH,
                default=options.get(CONF_CAPABILITIES_PATH, DEFAULT_CAPABILITIES_PATH),
            ): str,
            vol.Required(
                CONF_MODEL,
                default=options.get(CONF_MODEL, DEFAULT_MODEL),
            ): str,
            vol.Required(
                CONF_CONVERSATION_API,
                default=options.get(CONF_CONVERSATION_API, DEFAULT_CONVERSATION_API),
            ): vol.In(["responses", "chat_completions"]),
            vol.Required(
                CONF_CONVERSATION_PATH,
                default=options.get(CONF_CONVERSATION_PATH, DEFAULT_CONVERSATION_PATH),
            ): str,
            vol.Required(
                CONF_CHAT_COMPLETIONS_PATH,
                default=options.get(CONF_CHAT_COMPLETIONS_PATH, DEFAULT_CHAT_COMPLETIONS_PATH),
            ): str,
            vol.Required(
                CONF_VOICE_BASE_URL,
                default=options.get(CONF_VOICE_BASE_URL, DEFAULT_VOICE_BASE_URL),
            ): str,
            vol.Required(
                CONF_STT_PATH,
                default=options.get(CONF_STT_PATH, DEFAULT_STT_PATH),
            ): str,
            vol.Required(
                CONF_TTS_PATH,
                default=options.get(CONF_TTS_PATH, DEFAULT_TTS_PATH),
            ): str,
            vol.Required(
                CONF_TIMEOUT,
                default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
            vol.Required(
                CONF_DEFAULT_LANGUAGE,
                default=options.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE),
            ): str,
            vol.Required(
                CONF_TTS_AUDIO_FORMAT,
                default=options.get(CONF_TTS_AUDIO_FORMAT, DEFAULT_TTS_AUDIO_FORMAT),
            ): vol.In(["mp3", "wav", "ogg"]),
        }
    )


class HermesAssistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Hermes Assist config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_BASE_URL].rstrip("/"))
            self._abort_if_unique_id_configured()

            options = {
                CONF_HEALTH_PATH: DEFAULT_HEALTH_PATH,
                CONF_CAPABILITIES_PATH: DEFAULT_CAPABILITIES_PATH,
                CONF_MODEL: DEFAULT_MODEL,
                CONF_CONVERSATION_API: DEFAULT_CONVERSATION_API,
                CONF_CONVERSATION_PATH: DEFAULT_CONVERSATION_PATH,
                CONF_CHAT_COMPLETIONS_PATH: DEFAULT_CHAT_COMPLETIONS_PATH,
                CONF_VOICE_BASE_URL: user_input.get(CONF_VOICE_BASE_URL, DEFAULT_VOICE_BASE_URL),
                CONF_STT_PATH: DEFAULT_STT_PATH,
                CONF_TTS_PATH: DEFAULT_TTS_PATH,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_DEFAULT_LANGUAGE: DEFAULT_LANGUAGE,
                CONF_TTS_AUDIO_FORMAT: DEFAULT_TTS_AUDIO_FORMAT,
            }

            client = HermesClient(async_get_clientsession(self.hass), user_input, options)
            try:
                await client.async_health_check()
                await client.async_capabilities_check()
                if user_input[CONF_ENABLE_STT] or user_input[CONF_ENABLE_TTS]:
                    await client.async_voice_health_check()
            except HermesAuthError:
                errors["base"] = "invalid_auth"
            except HermesConnectionError:
                errors["base"] = "cannot_connect"
            except HermesError:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Hermes Assist",
                    data=user_input,
                    options=options,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BASE_URL, default="http://localhost:8642"): str,
                    vol.Required(CONF_VOICE_BASE_URL, default=DEFAULT_VOICE_BASE_URL): str,
                    vol.Optional(CONF_API_TOKEN): str,
                    vol.Required(CONF_ENABLE_CONVERSATION, default=True): bool,
                    vol.Required(CONF_ENABLE_STT, default=True): bool,
                    vol.Required(CONF_ENABLE_TTS, default=True): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> HermesAssistOptionsFlow:
        """Create the options flow."""
        return HermesAssistOptionsFlow(config_entry)


class HermesAssistOptionsFlow(config_entries.OptionsFlow):
    """Handle Hermes Assist options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Manage Hermes Assist options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self._config_entry.options)),
        )
