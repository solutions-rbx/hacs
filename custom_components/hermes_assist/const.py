"""Constants for Hermes Assist."""

from __future__ import annotations

DOMAIN = "hermes_assist"

PLATFORMS = ["conversation"]

CONF_BASE_URL = "base_url"
CONF_API_TOKEN = "api_token"
CONF_CREATE_HERMES_SKILL = "create_hermes_skill"
CONF_HEALTH_PATH = "health_path"
CONF_CAPABILITIES_PATH = "capabilities_path"
CONF_MODEL = "model"
CONF_CONVERSATION_API = "conversation_api"
CONF_CONVERSATION_PATH = "conversation_path"
CONF_CHAT_COMPLETIONS_PATH = "chat_completions_path"
CONF_TIMEOUT = "timeout_seconds"
CONF_DEFAULT_LANGUAGE = "default_language"

DEFAULT_HEALTH_PATH = "/health"
DEFAULT_CAPABILITIES_PATH = "/v1/capabilities"
DEFAULT_MODEL = "hermes-agent"
DEFAULT_CONVERSATION_API = "responses"
DEFAULT_CONVERSATION_PATH = "/v1/responses"
DEFAULT_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
DEFAULT_TIMEOUT = 120
DEFAULT_LANGUAGE = "en"

STORAGE_CLIENT = "client"
