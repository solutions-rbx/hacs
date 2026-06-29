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
    CONF_STT_API_TOKEN,
    CONF_STT_BASE_URL,
    CONF_STT_MODEL,
    CONF_STT_PATH,
    CONF_STT_PROVIDER,
    CONF_STT_RESPONSE_TEXT_FIELD,
    CONF_TIMEOUT,
    CONF_TTS_API_TOKEN,
    CONF_TTS_AUDIO_FORMAT,
    CONF_TTS_BASE_URL,
    CONF_TTS_MODEL,
    CONF_TTS_PATH,
    CONF_TTS_PROVIDER,
    CONF_TTS_VOICE,
    CONF_VOICE_SETUP_MODE,
    DEFAULT_CAPABILITIES_PATH,
    DEFAULT_CHAT_COMPLETIONS_PATH,
    DEFAULT_CONVERSATION_API,
    DEFAULT_CONVERSATION_PATH,
    DEFAULT_HEALTH_PATH,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_STT_MODEL,
    DEFAULT_STT_PATH,
    DEFAULT_STT_PROVIDER,
    DEFAULT_STT_RESPONSE_TEXT_FIELD,
    DEFAULT_TIMEOUT,
    DEFAULT_TTS_AUDIO_FORMAT,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_PATH,
    DEFAULT_TTS_PROVIDER,
    DEFAULT_TTS_VOICE,
    DEFAULT_VOICE_SETUP_MODE,
    DOMAIN,
)


def _options_schema(options: dict[str, Any] | None = None) -> vol.Schema:
    """Build the options schema."""
    options = options or {}
    return vol.Schema(
        {
            vol.Required(CONF_HEALTH_PATH, default=options.get(CONF_HEALTH_PATH, DEFAULT_HEALTH_PATH)): str,
            vol.Required(
                CONF_CAPABILITIES_PATH,
                default=options.get(CONF_CAPABILITIES_PATH, DEFAULT_CAPABILITIES_PATH),
            ): str,
            vol.Required(CONF_MODEL, default=options.get(CONF_MODEL, DEFAULT_MODEL)): str,
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
                CONF_VOICE_SETUP_MODE,
                default=options.get(CONF_VOICE_SETUP_MODE, DEFAULT_VOICE_SETUP_MODE),
            ): vol.In(["hermes_agent", "custom_http"]),
            vol.Required(CONF_STT_PROVIDER, default=options.get(CONF_STT_PROVIDER, DEFAULT_STT_PROVIDER)): vol.In(
                ["custom_http"]
            ),
            vol.Required(CONF_STT_BASE_URL, default=options.get(CONF_STT_BASE_URL, "")): str,
            vol.Required(CONF_STT_PATH, default=options.get(CONF_STT_PATH, DEFAULT_STT_PATH)): str,
            vol.Optional(CONF_STT_API_TOKEN, default=options.get(CONF_STT_API_TOKEN, "")): str,
            vol.Required(CONF_STT_MODEL, default=options.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)): str,
            vol.Required(
                CONF_STT_RESPONSE_TEXT_FIELD,
                default=options.get(CONF_STT_RESPONSE_TEXT_FIELD, DEFAULT_STT_RESPONSE_TEXT_FIELD),
            ): str,
            vol.Required(CONF_TTS_PROVIDER, default=options.get(CONF_TTS_PROVIDER, DEFAULT_TTS_PROVIDER)): vol.In(
                ["custom_http"]
            ),
            vol.Required(CONF_TTS_BASE_URL, default=options.get(CONF_TTS_BASE_URL, "")): str,
            vol.Required(CONF_TTS_PATH, default=options.get(CONF_TTS_PATH, DEFAULT_TTS_PATH)): str,
            vol.Optional(CONF_TTS_API_TOKEN, default=options.get(CONF_TTS_API_TOKEN, "")): str,
            vol.Required(CONF_TTS_MODEL, default=options.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)): str,
            vol.Required(CONF_TTS_VOICE, default=options.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)): str,
            vol.Required(CONF_TIMEOUT, default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=300)
            ),
            vol.Required(CONF_DEFAULT_LANGUAGE, default=options.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE)): str,
            vol.Required(
                CONF_TTS_AUDIO_FORMAT,
                default=options.get(CONF_TTS_AUDIO_FORMAT, DEFAULT_TTS_AUDIO_FORMAT),
            ): vol.In(["mp3", "wav", "ogg"]),
        }
    )


def _custom_voice_schema(options: dict[str, Any], enable_stt: bool, enable_tts: bool) -> vol.Schema:
    """Build a manual custom voice provider schema."""
    fields: dict[Any, Any] = {}
    if enable_stt:
        fields.update(
            {
                vol.Required(CONF_STT_BASE_URL, default=options.get(CONF_STT_BASE_URL, "")): str,
                vol.Required(CONF_STT_PATH, default=options.get(CONF_STT_PATH, DEFAULT_STT_PATH)): str,
                vol.Optional(CONF_STT_API_TOKEN, default=options.get(CONF_STT_API_TOKEN, "")): str,
                vol.Required(CONF_STT_MODEL, default=options.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)): str,
                vol.Required(
                    CONF_STT_RESPONSE_TEXT_FIELD,
                    default=options.get(CONF_STT_RESPONSE_TEXT_FIELD, DEFAULT_STT_RESPONSE_TEXT_FIELD),
                ): str,
            }
        )
    if enable_tts:
        fields.update(
            {
                vol.Required(CONF_TTS_BASE_URL, default=options.get(CONF_TTS_BASE_URL, "")): str,
                vol.Required(CONF_TTS_PATH, default=options.get(CONF_TTS_PATH, DEFAULT_TTS_PATH)): str,
                vol.Optional(CONF_TTS_API_TOKEN, default=options.get(CONF_TTS_API_TOKEN, "")): str,
                vol.Required(CONF_TTS_MODEL, default=options.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)): str,
                vol.Required(CONF_TTS_VOICE, default=options.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)): str,
                vol.Required(
                    CONF_TTS_AUDIO_FORMAT,
                    default=options.get(CONF_TTS_AUDIO_FORMAT, DEFAULT_TTS_AUDIO_FORMAT),
                ): vol.In(["mp3", "wav", "ogg"]),
            }
        )
    return vol.Schema(fields)


class HermesAssistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Hermes Assist config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self._setup_summary = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            await self.async_set_unique_id(base_url)
            self._abort_if_unique_id_configured()

            self._data = {**user_input, CONF_BASE_URL: base_url}
            self._options = _default_options(base_url)

            client = HermesClient(async_get_clientsession(self.hass), self._data, self._options)
            try:
                await client.async_health_check()
                await client.async_capabilities_check()
            except HermesAuthError:
                errors["base"] = "invalid_auth"
            except HermesConnectionError:
                errors["base"] = "cannot_connect"
            except HermesError:
                errors["base"] = "unknown"
            else:
                if not user_input[CONF_ENABLE_STT] and not user_input[CONF_ENABLE_TTS]:
                    self._setup_summary = "Voice providers disabled."
                    return await self.async_step_confirm()
                return await self.async_step_voice_setup()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BASE_URL, default="http://localhost:8642"): str,
                    vol.Optional(CONF_API_TOKEN): str,
                    vol.Required(CONF_ENABLE_CONVERSATION, default=True): bool,
                    vol.Required(CONF_ENABLE_STT, default=True): bool,
                    vol.Required(CONF_ENABLE_TTS, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_voice_setup(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Choose how voice endpoints are configured."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"voice_error": ""}

        if user_input is not None:
            mode = user_input[CONF_VOICE_SETUP_MODE]
            self._options[CONF_VOICE_SETUP_MODE] = mode

            if mode == "custom_http":
                return await self.async_step_custom_voice()

            client = HermesClient(async_get_clientsession(self.hass), self._data, self._options)
            try:
                setup = await client.async_voice_setup(
                    self._data[CONF_ENABLE_STT],
                    self._data[CONF_ENABLE_TTS],
                )
                _apply_voice_setup(
                    self._options,
                    setup.payload,
                    self._data[CONF_ENABLE_STT],
                    self._data[CONF_ENABLE_TTS],
                )
            except HermesConnectionError:
                errors["base"] = "cannot_connect"
            except HermesError as err:
                errors["base"] = "invalid_voice_setup"
                placeholders["voice_error"] = str(err)
            else:
                status = str(setup.payload.get("status", "")).lower()
                if status == "ready":
                    self._setup_summary = _voice_summary(self._options)
                    return await self.async_step_confirm()
                if status == "needs_user_action":
                    errors["base"] = "needs_user_action"
                    placeholders["voice_error"] = "\n".join(
                        str(action) for action in setup.payload.get("user_actions", [])
                    ) or setup.raw_text[:500]
                else:
                    errors["base"] = "voice_setup_failed"
                    placeholders["voice_error"] = setup.raw_text[:500]

        return self.async_show_form(
            step_id="voice_setup",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_VOICE_SETUP_MODE,
                        default=self._options.get(CONF_VOICE_SETUP_MODE, DEFAULT_VOICE_SETUP_MODE),
                    ): vol.In(["hermes_agent", "custom_http"]),
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_custom_voice(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Collect manual custom STT/TTS provider settings."""
        if user_input is not None:
            self._options.update(user_input)
            self._options[CONF_VOICE_SETUP_MODE] = "custom_http"
            self._options[CONF_STT_PROVIDER] = DEFAULT_STT_PROVIDER
            self._options[CONF_TTS_PROVIDER] = DEFAULT_TTS_PROVIDER
            self._setup_summary = _voice_summary(self._options)
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="custom_voice",
            data_schema=_custom_voice_schema(
                self._options,
                self._data[CONF_ENABLE_STT],
                self._data[CONF_ENABLE_TTS],
            ),
        )

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Confirm setup before creating the entry."""
        if user_input is not None:
            return self.async_create_entry(
                title="Hermes Assist",
                data=self._data,
                options=self._options,
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"summary": self._setup_summary},
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


def _default_options(base_url: str) -> dict[str, Any]:
    """Return default options for a new config entry."""
    return {
        CONF_HEALTH_PATH: DEFAULT_HEALTH_PATH,
        CONF_CAPABILITIES_PATH: DEFAULT_CAPABILITIES_PATH,
        CONF_MODEL: DEFAULT_MODEL,
        CONF_CONVERSATION_API: DEFAULT_CONVERSATION_API,
        CONF_CONVERSATION_PATH: DEFAULT_CONVERSATION_PATH,
        CONF_CHAT_COMPLETIONS_PATH: DEFAULT_CHAT_COMPLETIONS_PATH,
        CONF_VOICE_SETUP_MODE: DEFAULT_VOICE_SETUP_MODE,
        CONF_STT_PROVIDER: DEFAULT_STT_PROVIDER,
        CONF_STT_BASE_URL: base_url,
        CONF_STT_PATH: DEFAULT_STT_PATH,
        CONF_STT_API_TOKEN: "",
        CONF_STT_MODEL: DEFAULT_STT_MODEL,
        CONF_STT_RESPONSE_TEXT_FIELD: DEFAULT_STT_RESPONSE_TEXT_FIELD,
        CONF_TTS_PROVIDER: DEFAULT_TTS_PROVIDER,
        CONF_TTS_BASE_URL: base_url,
        CONF_TTS_PATH: DEFAULT_TTS_PATH,
        CONF_TTS_API_TOKEN: "",
        CONF_TTS_MODEL: DEFAULT_TTS_MODEL,
        CONF_TTS_VOICE: DEFAULT_TTS_VOICE,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
        CONF_DEFAULT_LANGUAGE: DEFAULT_LANGUAGE,
        CONF_TTS_AUDIO_FORMAT: DEFAULT_TTS_AUDIO_FORMAT,
    }


def _apply_voice_setup(
    options: dict[str, Any],
    setup: dict[str, Any],
    enable_stt: bool,
    enable_tts: bool,
) -> None:
    """Apply a Hermes voice setup response to options."""
    if enable_stt:
        stt = _section(setup, "stt")
        options[CONF_STT_PROVIDER] = DEFAULT_STT_PROVIDER
        options[CONF_STT_BASE_URL] = str(stt.get("base_url") or options[CONF_STT_BASE_URL]).rstrip("/")
        options[CONF_STT_PATH] = str(stt.get("path") or DEFAULT_STT_PATH)
        options[CONF_STT_API_TOKEN] = str(stt.get("api_token") or "")
        options[CONF_STT_MODEL] = str(stt.get("model") or DEFAULT_STT_MODEL)
        options[CONF_STT_RESPONSE_TEXT_FIELD] = str(
            stt.get("response_text_field") or DEFAULT_STT_RESPONSE_TEXT_FIELD
        )

    if enable_tts:
        tts = _section(setup, "tts")
        options[CONF_TTS_PROVIDER] = DEFAULT_TTS_PROVIDER
        options[CONF_TTS_BASE_URL] = str(tts.get("base_url") or options[CONF_TTS_BASE_URL]).rstrip("/")
        options[CONF_TTS_PATH] = str(tts.get("path") or DEFAULT_TTS_PATH)
        options[CONF_TTS_API_TOKEN] = str(tts.get("api_token") or "")
        options[CONF_TTS_MODEL] = str(tts.get("model") or DEFAULT_TTS_MODEL)
        options[CONF_TTS_VOICE] = str(tts.get("voice") or DEFAULT_TTS_VOICE)
        options[CONF_TTS_AUDIO_FORMAT] = str(tts.get("audio_format") or DEFAULT_TTS_AUDIO_FORMAT)


def _voice_summary(options: dict[str, Any]) -> str:
    """Build a short setup summary."""
    return (
        f"STT: {options.get(CONF_STT_BASE_URL, '')}{options.get(CONF_STT_PATH, '')}\n"
        f"TTS: {options.get(CONF_TTS_BASE_URL, '')}{options.get(CONF_TTS_PATH, '')}\n"
        f"TTS format: {options.get(CONF_TTS_AUDIO_FORMAT, DEFAULT_TTS_AUDIO_FORMAT)}"
    )


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a nested dict section."""
    value = payload.get(key, {})
    return value if isinstance(value, dict) else {}
