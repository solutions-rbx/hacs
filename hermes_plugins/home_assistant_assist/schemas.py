"""Tool schemas for the Home Assistant Assist Hermes plugin."""

HOME_ASSISTANT_ASSIST_CONFIG = {
    "name": "home_assistant_assist_config",
    "description": (
        "Return the Hermes Assist Home Assistant integration settings for this "
        "Hermes Agent instance, including the conversation API URL and the "
        "plugin-hosted STT/TTS endpoint URLs."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

