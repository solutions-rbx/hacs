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


@dataclass(slots=True)
class HermesTtsResponse:
    """Parsed Hermes TTS response."""

    extension: str
    data: bytes


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


def _audio_extension(content_type: str | None, fallback: str) -> str:
    """Infer an audio extension from a content type."""
    if content_type:
        lower = content_type.lower()
        if "wav" in lower or "wave" in lower:
            return "wav"
        if "mpeg" in lower or "mp3" in lower:
            return "mp3"
        if "ogg" in lower:
            return "ogg"
    return fallback


class HermesClient:
    """Minimal async client for Hermes Agent."""

    def __init__(self, session: ClientSession, data: dict[str, Any], options: dict[str, Any]) -> None:
        """Initialize the client."""
        self._session = session
        self._base_url = str(data[CONF_BASE_URL]).rstrip("/")
        self._api_token = data.get(CONF_API_TOKEN)
        self._options = options
        self._voice_base_url = str(self._options.get(CONF_VOICE_BASE_URL, DEFAULT_VOICE_BASE_URL)).rstrip("/")

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
    def tts_audio_format(self) -> str:
        """Return the fallback TTS extension."""
        return str(self._options.get(CONF_TTS_AUDIO_FORMAT, DEFAULT_TTS_AUDIO_FORMAT))

    def _url(self, option_key: str, default_path: str, *, voice: bool = False) -> str:
        """Build a Hermes endpoint URL."""
        path = _clean_path(str(self._options.get(option_key, default_path)))
        base_url = self._voice_base_url if voice else self._base_url
        return urljoin(f"{base_url}/", path.lstrip("/"))

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

    async def async_voice_health_check(self) -> None:
        """Check that the Hermes Assist plugin sidecar is available."""
        url = urljoin(f"{self._voice_base_url}/", "health")
        try:
            async with self._session.get(url, headers=self._headers(), timeout=self.timeout) as response:
                await self._raise_for_status(response)
        except TimeoutError as err:
            raise HermesConnectionError("Timed out connecting to Hermes Assist plugin voice API") from err
        except ClientError as err:
            raise HermesConnectionError("Could not connect to Hermes Assist plugin voice API") from err

    async def async_converse(
        self,
        text: str,
        language: str,
        conversation_id: str | None,
        chat_history: list[dict[str, str]],
    ) -> HermesConversationResponse:
        """Send a conversation turn to Hermes."""
        if self.conversation_api == "chat_completions":
            return await self._async_chat_completions(text, language, conversation_id, chat_history)

        return await self._async_responses(text, language, conversation_id)

    async def _async_responses(
        self,
        text: str,
        language: str,
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
                timeout=self.timeout,
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
        continue_conversation = False
        if isinstance(data, dict):
            response_id = data.get("id") or data.get("conversation_id")

        return HermesConversationResponse(
            text=response_text,
            conversation_id=str(response_id) if response_id else conversation_id,
            continue_conversation=continue_conversation,
        )

    async def _async_chat_completions(
        self,
        text: str,
        language: str,
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
                timeout=self.timeout,
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

    async def async_stt(self, audio: bytes, language: str, content_type: str = "audio/wav") -> str:
        """Send audio to Hermes STT and return recognized text."""
        url = self._url(CONF_STT_PATH, DEFAULT_STT_PATH, voice=True)
        headers = self._headers(
            {
                "Content-Type": content_type,
                "Accept": "application/json, text/plain",
                "X-Hermes-Language": language,
            }
        )
        try:
            async with self._session.post(
                url,
                headers=headers,
                data=audio,
                timeout=self.timeout,
            ) as response:
                await self._raise_for_status(response)
                data = await _read_json_or_text(response)
        except TimeoutError as err:
            raise HermesConnectionError("Timed out waiting for Hermes STT response") from err
        except ClientError as err:
            raise HermesConnectionError("Could not send STT request to Hermes") from err

        text = _extract_text(data)
        if not text:
            raise HermesResponseError("Hermes STT response did not include recognized text")
        return text

    async def async_tts(self, message: str, language: str, options: dict[str, Any]) -> HermesTtsResponse:
        """Send text to Hermes TTS and return audio."""
        url = self._url(CONF_TTS_PATH, DEFAULT_TTS_PATH, voice=True)
        payload = {"text": message, "language": language, "options": options}
        try:
            async with self._session.post(
                url,
                headers=self._headers({"Content-Type": "application/json"}),
                json=payload,
                timeout=self.timeout,
            ) as response:
                await self._raise_for_status(response)
                content_type = response.headers.get("Content-Type")
                data = await response.read()
        except TimeoutError as err:
            raise HermesConnectionError("Timed out waiting for Hermes TTS response") from err
        except ClientError as err:
            raise HermesConnectionError("Could not send TTS request to Hermes") from err

        if not data:
            raise HermesResponseError("Hermes TTS response did not include audio")

        return HermesTtsResponse(
            extension=_audio_extension(content_type, self.tts_audio_format),
            data=data,
        )


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
