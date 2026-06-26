"""Conversation platform for Hermes Assist."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import conversation
from homeassistant.components.conversation import (
    AssistantContent,
    ChatLog,
    ConversationEntity,
    ConversationEntityFeature,
    ConversationInput,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import intent

from .api import HermesClient, HermesError
from .const import DOMAIN, STORAGE_CLIENT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hermes Assist conversation entity."""
    client: HermesClient = hass.data[DOMAIN][entry.entry_id][STORAGE_CLIENT]
    async_add_entities([HermesConversationEntity(entry.entry_id, client)])


class HermesConversationEntity(ConversationEntity):
    """Hermes conversation agent."""

    _attr_name = "Hermes Assist"
    _attr_has_entity_name = False
    _attr_supported_features = ConversationEntityFeature.CONTROL

    def __init__(self, entry_id: str, client: HermesClient) -> None:
        """Initialize the conversation entity."""
        self._attr_unique_id = f"{entry_id}_conversation"
        self._client = client

    @property
    def supported_languages(self) -> list[str] | str:
        """Return supported languages."""
        return "*"

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
        chat_log: ChatLog,
    ) -> conversation.ConversationResult:
        """Handle a message through Hermes."""
        language = user_input.language or self._client.default_language
        history = _chat_history(chat_log)

        try:
            hermes_response = await self._client.async_converse(
                user_input.text,
                language,
                user_input.conversation_id,
                history,
            )
        except HermesError as err:
            _LOGGER.exception("Hermes conversation failed")
            response = intent.IntentResponse(language=language)
            response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Hermes Assist failed: {err}",
            )
            return conversation.ConversationResult(
                conversation_id=user_input.conversation_id,
                response=response,
                continue_conversation=False,
            )

        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(
                agent_id=user_input.agent_id,
                content=hermes_response.text,
            )
        )

        response = intent.IntentResponse(language=language)
        response.async_set_speech(hermes_response.text)
        return conversation.ConversationResult(
            conversation_id=hermes_response.conversation_id,
            response=response,
            continue_conversation=hermes_response.continue_conversation,
        )


def _chat_history(chat_log: ChatLog) -> list[dict[str, str]]:
    """Best-effort conversion of HA chat history into Hermes messages."""
    content: Any = getattr(chat_log, "content", None)
    if not content:
        return []

    history: list[dict[str, str]] = []
    for item in content:
        role = getattr(item, "role", None)
        text = getattr(item, "content", None)
        if isinstance(role, str) and isinstance(text, str):
            history.append({"role": role, "content": text})
    return history

