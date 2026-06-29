"""HTTP client for Hermes Assist."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientError, ClientResponse, ClientSession

from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_CAPABILITIES_PATH,
    CONF_CHAT_COMPLETIONS_PATH,
    CONF_CONVERSATION_API,
    CONF_CONVERSATION_PATH,
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
)

_LOGGER = logging.getLogger(__name__)


class HermesError(Exception):
    """Base Hermes API error."""


class HermesAuthError(HermesError):
    """Hermes authentication failed."""


class HermesConnectionError(HermesError):
    """Hermes connection failed."""


class HermesResponseError(HermesError):
    """Hermes returned an unsupported response."""


@dataclass(slots=True)
class HermesConversationResponse:
    """Parsed Hermes conversation response."""

    text: str
    conversation_id: str | None = None
    continue_conversation: bool = False


def _clean_path(path: str) -> str:
    """Normalize a configured endpoint path."""
    if not path:
        return "/"
    return path if path.startswith("/") else f"/{path}"


def _extract_text(payload: Any) -> str | None:
    """Extract response text from common Hermes/OpenAI-like shapes."""
    if isinstance(payload, str):
        return payload.strip() or None

    if not isinstance(payload, dict):
        return None

    for key in ("response", "text", "speech", "transcript", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    message = payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

            text = first.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    output = payload.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
        if text_parts:
            return "\n".join(text_parts)

    return None


class HermesClient:
    """Minimal async client for Hermes Agent."""

    def __init__(self, session: ClientSession, data: dict[str, Any], options: dict[str, Any]) -> None:
        """Initialize the client."""
        self._session = session
        self._base_url = str(data[CONF_BASE_URL]).rstrip("/")
        self._api_token = data.get(CONF_API_TOKEN)
        self._options = options

    @property
    def model(self) -> str:
        """Return the configured Hermes API model name."""
        return str(self._options.get(CONF_MODEL, DEFAULT_MODEL))

    @property
    def conversation_api(self) -> str:
        """Return the configured Hermes conversation API."""
        return str(self._options.get(CONF_CONVERSATION_API, DEFAULT_CONVERSATION_API))

    @property
    def default_language(self) -> str:
        """Return the configured default language."""
        return str(self._options.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))

    @property
    def timeout(self) -> int:
        """Return the configured request timeout."""
        return int(self._options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))

    @property
    def conversation_timeout(self) -> int:
        """Return a conversation timeout long enough for agent tool calls."""
        return max(self.timeout, DEFAULT_TIMEOUT)

    def _url(self, option_key: str, default_path: str) -> str:
        """Build a Hermes endpoint URL."""
        path = _clean_path(str(self._options.get(option_key, default_path)))
        return urljoin(f"{self._base_url}/", path.lstrip("/"))

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers."""
        headers: dict[str, str] = {}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        if extra:
            headers.update(extra)
        return headers

    async def _raise_for_status(self, response: ClientResponse) -> None:
        """Convert HTTP errors to integration errors."""
        if response.status in (401, 403):
            raise HermesAuthError("Hermes rejected the configured credentials")
        if response.status >= 400:
            text = await response.text()
            raise HermesResponseError(f"Hermes returned HTTP {response.status}: {text[:200]}")

    async def async_health_check(self) -> None:
        """Check Hermes availability."""
        url = self._url(CONF_HEALTH_PATH, DEFAULT_HEALTH_PATH)
        try:
            async with self._session.get(url, headers=self._headers(), timeout=self.timeout) as response:
                await self._raise_for_status(response)
        except TimeoutError as err:
            raise HermesConnectionError("Timed out connecting to Hermes") from err
        except ClientError as err:
            raise HermesConnectionError("Could not connect to Hermes") from err

    async def async_capabilities_check(self) -> None:
        """Check that Hermes exposes the API server surface."""
        url = self._url(CONF_CAPABILITIES_PATH, DEFAULT_CAPABILITIES_PATH)
        try:
            async with self._session.get(url, headers=self._headers(), timeout=self.timeout) as response:
                await self._raise_for_status(response)
        except TimeoutError as err:
            raise HermesConnectionError("Timed out connecting to Hermes API server") from err
        except ClientError as err:
            raise HermesConnectionError("Could not connect to Hermes API server") from err

    async def async_converse(
        self,
        text: str,
        language: str,
        conversation_id: str | None,
        chat_history: list[dict[str, str]],
    ) -> HermesConversationResponse:
        """Send a conversation turn to Hermes."""
        if self.conversation_api == "chat_completions":
            return await self._async_chat_completions(text, conversation_id, chat_history)

        return await self._async_responses(text, conversation_id)

    async def _async_responses(
        self,
        text: str,
        conversation_id: str | None,
    ) -> HermesConversationResponse:
        """Send a turn through Hermes' OpenAI-compatible Responses API."""
        url = self._url(CONF_CONVERSATION_PATH, DEFAULT_CONVERSATION_PATH)
        payload = {
            "model": self.model,
            "input": text,
            "store": True,
        }
        if conversation_id:
            if conversation_id.startswith("resp_"):
                payload["previous_response_id"] = conversation_id
            else:
                payload["conversation"] = conversation_id

        try:
            async with self._session.post(
                url,
                headers=self._headers({"Content-Type": "application/json"}),
                json=payload,
                timeout=self.conversation_timeout,
            ) as response:
                await self._raise_for_status(response)
                data = await _read_json_or_text(response)
        except TimeoutError as err:
            raise HermesConnectionError("Timed out waiting for Hermes conversation response") from err
        except ClientError as err:
            raise HermesConnectionError("Could not send conversation request to Hermes") from err

        response_text = _extract_text(data)
        if not response_text:
            raise HermesResponseError("Hermes Responses API response did not include text")

        response_id = None
        if isinstance(data, dict):
            response_id = data.get("id") or data.get("conversation_id")

        return HermesConversationResponse(
            text=response_text,
            conversation_id=str(response_id) if response_id else conversation_id,
            continue_conversation=False,
        )

    async def _async_chat_completions(
        self,
        text: str,
        conversation_id: str | None,
        chat_history: list[dict[str, str]],
    ) -> HermesConversationResponse:
        """Send a turn through Hermes' OpenAI-compatible Chat Completions API."""
        url = self._url(CONF_CHAT_COMPLETIONS_PATH, DEFAULT_CHAT_COMPLETIONS_PATH)
        messages = [*chat_history, {"role": "user", "content": text}]
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        try:
            async with self._session.post(
                url,
                headers=self._headers({"Content-Type": "application/json"}),
                json=payload,
                timeout=self.conversation_timeout,
            ) as response:
                await self._raise_for_status(response)
                data = await _read_json_or_text(response)
        except TimeoutError as err:
            raise HermesConnectionError("Timed out waiting for Hermes chat completion") from err
        except ClientError as err:
            raise HermesConnectionError("Could not send chat completion request to Hermes") from err

        response_text = _extract_text(data)
        if not response_text:
            raise HermesResponseError("Hermes chat completion did not include text")

        return HermesConversationResponse(
            text=response_text,
            conversation_id=conversation_id,
            continue_conversation=False,
        )

    async def async_configure_home_assistant_skill(self) -> str:
        """Ask Hermes Agent to create/update its Home Assistant knowledge skill."""
        response = await self._async_responses(_home_assistant_skill_prompt(), None)
        return response.text


async def _read_json_or_text(response: ClientResponse) -> Any:
    """Read a response as JSON when possible, otherwise text."""
    content_type = response.headers.get("Content-Type", "")
    if "json" in content_type.lower():
        return await response.json()

    text = await response.text()
    if not text:
        return ""

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        _LOGGER.debug("Hermes returned non-JSON text response")
        return text


def _home_assistant_skill_prompt() -> str:
    """Build the first-run Hermes skill setup prompt."""
    return (
        "Create or update a Hermes Agent skill named `home-assistant-assist`. "
        "The skill should teach Hermes how to work well as the conversation agent for "
        "Home Assistant Assist through the Hermes Assist HACS integration. "
        "The integration sends user text from Home Assistant Assist to Hermes Agent and "
        "expects concise natural-language responses. It does not provide STT or TTS. "
        "Home Assistant handles microphones, speakers, STT, TTS, and Assist pipelines separately. "
        "The skill should explain what Hermes can do: answer smart-home questions, reason about "
        "the user's request, call any Home Assistant tools or APIs already available to Hermes, "
        "summarize device state, ask a clarifying question when a command is ambiguous, and avoid "
        "claiming an action succeeded unless a tool/API confirms it. "
        "The skill should explain how Hermes should behave: keep responses short for voice use, "
        "mention the room/device acted on, use the user's language when possible, preserve context "
        "across turns, and be honest when Home Assistant access is missing. "
        "Also include examples: turning lights on/off, setting climate temperature, checking doors, "
        "explaining automations, creating reminders if Hermes has that tool, and asking which room "
        "when the target is unclear. "
        "If you can write skills to disk, create the skill now. If you cannot write files, return "
        "the complete skill content and exact install instructions. Reply with a short summary of "
        "what you created or what the user must do next."
    )
