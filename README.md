# Hermes Assist

Hermes Assist is a Home Assistant custom integration for HACS. It adds a configurable Hermes-backed conversation agent and optional Hermes STT/TTS providers that can be selected in Home Assistant Assist pipelines.

## Features

- Conversation agent provider for Home Assistant Assist
- Optional Speech-to-Text provider backed by the companion Hermes plugin
- Optional Text-to-Speech provider backed by the companion Hermes plugin
- UI setup through Home Assistant config flow
- Configurable base URL, token, endpoint paths, timeout, language, and enabled providers
- Provider-only behavior: it does not edit or replace your Assist pipelines automatically

## HACS installation

1. In HACS, open **Custom repositories**.
2. Add this repository URL.
3. Select **Integration** as the category.
4. Install **Hermes Assist**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration** and search for **Hermes Assist**.

## Hermes API server defaults

Hermes Assist uses the official Hermes Agent API server for conversation and the companion Hermes plugin for STT/TTS.

Enable the official Hermes API server:

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
hermes gateway
```

Install the companion plugin by copying this folder:

```text
hermes_plugins/home_assistant_assist/
```

to:

```text
~/.hermes/plugins/home_assistant_assist/
```

Then enable it:

```bash
hermes plugins enable home_assistant_assist
```

Start the plugin sidecar for Home Assistant voice providers:

```bash
HERMES_ASSIST_API_ENABLED=true
HERMES_ASSIST_API_HOST=0.0.0.0
HERMES_ASSIST_API_PORT=8765
HERMES_ASSIST_API_KEY="$API_SERVER_KEY"
```

Then configure Hermes Assist with:

- Base URL: `http://<hermes-host>:8642`
- Voice base URL: `http://<hermes-host>:8765`
- API token: the value of `API_SERVER_KEY`

The integration defaults to these paths under your configured base URL:

| Purpose | Default path |
| --- | --- |
| Health check | `/health` |
| Capabilities check | `/v1/capabilities` |
| Conversation, default | `/v1/responses` |
| Conversation, alternate | `/v1/chat/completions` |
| Speech-to-text | `/ha/v1/audio/transcriptions` |
| Text-to-speech | `/ha/v1/audio/speech` |

You can change these from the integration options.

## Conversation API

By default Hermes Assist uses Hermes Agent's OpenAI-compatible Responses API:

```json
{
  "model": "hermes-agent",
  "input": "Turn on the living room lights",
  "store": true
}
```

It also supports the documented Chat Completions API as an option. Responses are parsed from standard OpenAI-compatible response objects.

## Companion Plugin STT and TTS

The official Hermes plugin API does not document a route-registration hook for adding endpoints to Hermes' main API server. The companion plugin therefore starts a small local HTTP sidecar on port `8765` and exposes stable Home Assistant voice endpoints.

By default the sidecar uses Hermes' already configured voice stack:

- STT calls Hermes' own `tools.transcription_tools.transcribe_audio()`
- TTS calls Hermes' own `tools.tts_tool.text_to_speech_tool()`
- `GET /ha/v1/capabilities` reports the active Hermes provider, model, whether it is remote, and whether it is using Hermes config

For your example setup, the sidecar will expose:

```text
STT: local faster-whisper, model base
TTS: mimo-tts command provider
```

No separate Home Assistant STT/TTS backend config is needed.

Manual override modes still exist for unusual deployments:

```bash
HERMES_ASSIST_STT_PROVIDER=hermes
HERMES_ASSIST_TTS_PROVIDER=hermes

# Optional escape hatches:
# HERMES_ASSIST_STT_PROVIDER=command|openai|custom
# HERMES_ASSIST_TTS_PROVIDER=command|openai|custom
```

Manual command override example:

```bash
HERMES_ASSIST_STT_PROVIDER=command
HERMES_ASSIST_STT_COMMAND='whisper-cli -f {input_path} -otxt -of {output_dir}/transcript'
HERMES_ASSIST_TTS_PROVIDER=command
HERMES_ASSIST_TTS_COMMAND='piper -m ~/voices/en_US-lessac-medium.onnx -f {output_path} < {input_path}'
HERMES_ASSIST_TTS_FORMAT=wav
```

Manual OpenAI-compatible override example:

```bash
HERMES_ASSIST_STT_PROVIDER=openai
HERMES_ASSIST_STT_BASE_URL=https://api.openai.com/v1
HERMES_ASSIST_STT_ENDPOINT=/audio/transcriptions
HERMES_ASSIST_STT_API_KEY="$VOICE_TOOLS_OPENAI_KEY"
HERMES_ASSIST_STT_MODEL=whisper-1

HERMES_ASSIST_TTS_PROVIDER=openai
HERMES_ASSIST_TTS_BASE_URL=https://api.openai.com/v1
HERMES_ASSIST_TTS_ENDPOINT=/audio/speech
HERMES_ASSIST_TTS_API_KEY="$VOICE_TOOLS_OPENAI_KEY"
HERMES_ASSIST_TTS_MODEL=gpt-4o-mini-tts
HERMES_ASSIST_TTS_VOICE=alloy
HERMES_ASSIST_TTS_FORMAT=mp3
```

For custom servers, set `HERMES_ASSIST_STT_PROVIDER=custom` or `HERMES_ASSIST_TTS_PROVIDER=custom` and point the matching `*_BASE_URL` and `*_ENDPOINT` variables at your service. The custom server should use OpenAI-style request/response shapes.

Inside Hermes, call the plugin tool `home_assistant_assist_config` to print the exact URLs and feature status.

## Assist pipeline setup

After setup, open Home Assistant Assist pipeline settings and choose:

- **Hermes Assist** as the conversation agent
- **Hermes Assist STT** as the speech-to-text provider, if enabled
- **Hermes Assist TTS** as the text-to-speech provider, if enabled

You can mix Hermes with other providers.
