# Hermes Assist

Hermes Assist is a Home Assistant custom integration for HACS. It adds a Hermes-backed conversation agent and optional STT/TTS providers for Home Assistant Assist pipelines.

## Features

- Conversation agent provider for Home Assistant Assist
- HACS-only setup; no separate Hermes plugin or sidecar is required
- Setup wizard can ask Hermes Agent to prepare STT/TTS endpoints
- Manual custom HTTP STT/TTS provider configuration
- OpenAI-shaped STT multipart upload and TTS JSON support
- Provider-only behavior: it does not edit or replace your Assist pipelines automatically

## HACS Installation

1. In HACS, open **Custom repositories**.
2. Add this repository URL.
3. Select **Integration** as the category.
4. Install **Hermes Assist**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration** and search for **Hermes Assist**.

## Hermes Setup

Hermes Assist uses the official Hermes Agent API server for conversation and setup negotiation.

Start Hermes with the API server enabled:

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
hermes gateway
```

In the Home Assistant setup wizard, enter:

```text
Hermes base URL: http://<hermes-host>:8642
API token:       change-me-local-dev
```

If Home Assistant runs in Docker or on another machine, use the Hermes machine IP instead of `localhost`.

## Voice Setup Wizard

When STT or TTS is enabled, the wizard offers two modes:

```text
hermes_agent
custom_http
```

`hermes_agent` asks Hermes Agent to inspect its current voice config and return strict JSON with STT/TTS endpoint details. If Hermes uses local STT/TTS, Hermes should expose or configure an HTTP API that Home Assistant can call. If Hermes uses an API provider like OpenAI, Groq, Mistral, xAI, Gemini, ElevenLabs, or a custom HTTP provider, Hermes should return direct provider configuration.

`custom_http` lets you enter STT/TTS endpoints yourself.

## Expected Hermes Voice Setup Response

Hermes must return strict JSON only:

```json
{
  "status": "ready",
  "stt": {
    "provider": "local",
    "base_url": "http://hermes-host:8642",
    "path": "/v1/audio/transcriptions",
    "api_token": "optional-token",
    "model": "base",
    "response_text_field": "text",
    "health_url": "",
    "notes": ""
  },
  "tts": {
    "provider": "mimo-tts",
    "base_url": "http://hermes-host:8642",
    "path": "/v1/audio/speech",
    "api_token": "optional-token",
    "model": "",
    "voice": "default",
    "audio_format": "wav",
    "health_url": "",
    "notes": ""
  },
  "user_actions": []
}
```

If Hermes cannot complete setup, it should return:

```json
{
  "status": "needs_user_action",
  "stt": {},
  "tts": {},
  "user_actions": ["Start a local STT HTTP server reachable from Home Assistant."]
}
```

## Custom STT/TTS

Custom STT sends an OpenAI-style multipart request:

```text
POST <STT base URL><STT endpoint path>
Authorization: Bearer <STT API token>
fields:
  model
  language
  file
```

The response text is read from `stt_response_text_field`, default `text`.

Custom TTS sends an OpenAI-style JSON request:

```json
{
  "model": "gpt-4o-mini-tts",
  "input": "Hello",
  "voice": "alloy",
  "response_format": "mp3"
}
```

The TTS response must be raw audio bytes with a useful `Content-Type`, such as `audio/mpeg` or `audio/wav`.

## Assist Pipeline Setup

After setup, open Home Assistant Assist pipeline settings and choose:

- **Hermes Assist** as the conversation agent
- **Hermes Assist STT** as the speech-to-text provider, if enabled
- **Hermes Assist TTS** as the text-to-speech provider, if enabled

You can mix Hermes Assist with other Home Assistant STT/TTS providers.

