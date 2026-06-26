"""Constants for Hermes Assist."""

from __future__ import annotations

DOMAIN = "hermes_assist"

PLATFORMS = ["conversation", "stt", "tts"]

CONF_BASE_URL = "base_url"
CONF_VOICE_BASE_URL = "voice_base_url"
CONF_API_TOKEN = "api_token"
CONF_ENABLE_CONVERSATION = "enable_conversation"
CONF_ENABLE_STT = "enable_stt"
CONF_ENABLE_TTS = "enable_tts"
CONF_HEALTH_PATH = "health_path"
CONF_CAPABILITIES_PATH = "capabilities_path"
CONF_MODEL = "model"
CONF_CONVERSATION_API = "conversation_api"
CONF_CONVERSATION_PATH = "conversation_path"
CONF_CHAT_COMPLETIONS_PATH = "chat_completions_path"
CONF_STT_PATH = "stt_path"
CONF_TTS_PATH = "tts_path"
CONF_TIMEOUT = "timeout_seconds"
CONF_DEFAULT_LANGUAGE = "default_language"
CONF_TTS_AUDIO_FORMAT = "tts_audio_format"

DEFAULT_HEALTH_PATH = "/health"
DEFAULT_CAPABILITIES_PATH = "/v1/capabilities"
DEFAULT_MODEL = "hermes-agent"
DEFAULT_CONVERSATION_API = "responses"
DEFAULT_CONVERSATION_PATH = "/v1/responses"
DEFAULT_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
DEFAULT_VOICE_BASE_URL = "http://localhost:8765"
DEFAULT_STT_PATH = "/ha/v1/audio/transcriptions"
DEFAULT_TTS_PATH = "/ha/v1/audio/speech"
DEFAULT_TIMEOUT = 30
DEFAULT_LANGUAGE = "en"
DEFAULT_TTS_AUDIO_FORMAT = "mp3"

STORAGE_CLIENT = "client"
