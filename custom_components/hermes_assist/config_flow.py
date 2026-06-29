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
    CONF_CREATE_HERMES_SKILL,
    CONF_DEFAULT_LANGUAGE,
    CONF_HEALTH_PATH,
    CONF_MODEL,
    CONF_TIMEOUT,
    DEFAULT_CAPABILITIES_PATH,
    DEFAULT_CHAT_COMPLETIONS_PATH,
    DEFAULT_CONVERSATION_API,
    DEFAULT_CONVERSATION_PATH,
    DEFAULT_HEALTH_PATH,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
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
            vol.Required(CONF_TIMEOUT, default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=300)
            ),
            vol.Required(CONF_DEFAULT_LANGUAGE, default=options.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE)): str,
        }
    )


class HermesAssistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Hermes Assist config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self._skill_result = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            await self.async_set_unique_id(base_url)
            self._abort_if_unique_id_configured()

            self._data = {
                CONF_BASE_URL: base_url,
                CONF_API_TOKEN: user_input.get(CONF_API_TOKEN, ""),
            }
            self._options = _default_options()

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
                if user_input.get(CONF_CREATE_HERMES_SKILL, True):
                    return await self.async_step_hermes_skill()
                self._skill_result = "Skipped Hermes skill setup."
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BASE_URL, default="http://localhost:8642"): str,
                    vol.Optional(CONF_API_TOKEN): str,
                    vol.Required(CONF_CREATE_HERMES_SKILL, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_hermes_skill(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Ask Hermes to create/update its Home Assistant skill."""
        errors: dict[str, str] = {}

        client = HermesClient(async_get_clientsession(self.hass), self._data, self._options)
        try:
            self._skill_result = await client.async_configure_home_assistant_skill()
        except HermesConnectionError:
            errors["base"] = "cannot_connect"
        except HermesError as err:
            errors["base"] = "skill_setup_failed"
            self._skill_result = str(err)
        else:
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="hermes_skill",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"skill_result": self._skill_result},
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
            description_placeholders={"skill_result": self._skill_result},
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


def _default_options() -> dict[str, Any]:
    """Return default options for a new config entry."""
    return {
        CONF_HEALTH_PATH: DEFAULT_HEALTH_PATH,
        CONF_CAPABILITIES_PATH: DEFAULT_CAPABILITIES_PATH,
        CONF_MODEL: DEFAULT_MODEL,
        CONF_CONVERSATION_API: DEFAULT_CONVERSATION_API,
        CONF_CONVERSATION_PATH: DEFAULT_CONVERSATION_PATH,
        CONF_CHAT_COMPLETIONS_PATH: DEFAULT_CHAT_COMPLETIONS_PATH,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
        CONF_DEFAULT_LANGUAGE: DEFAULT_LANGUAGE,
    }
