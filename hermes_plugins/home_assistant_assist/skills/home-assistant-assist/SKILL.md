# Home Assistant Assist Bridge

Use this skill when helping a user connect Hermes Agent to the Hermes Assist Home Assistant HACS integration.

## Setup Summary

Hermes has two HTTP surfaces in this project:

- Hermes Agent API server for conversation: `http://localhost:8642`
- Home Assistant Assist plugin voice bridge for STT/TTS: `http://localhost:8765`

The Home Assistant integration should use:

- Base URL: value of `HERMES_API_BASE_URL`, usually `http://<hermes-host>:8642`
- API token: value of `API_SERVER_KEY`
- Voice base URL: `http://<hermes-host>:8765`
- STT path: `/ha/v1/audio/transcriptions`
- TTS path: `/ha/v1/audio/speech`

## Required Hermes Settings

Enable the official Hermes API server:

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
hermes gateway
```

Enable the plugin sidecar:

```bash
HERMES_ASSIST_API_ENABLED=true
HERMES_ASSIST_API_HOST=0.0.0.0
HERMES_ASSIST_API_PORT=8765
HERMES_ASSIST_API_KEY="$API_SERVER_KEY"
```

## Voice Auto-Detection

The default and recommended sidecar mode is:

```bash
HERMES_ASSIST_STT_PROVIDER=hermes
HERMES_ASSIST_TTS_PROVIDER=hermes
```

In this mode the sidecar must use Hermes' currently configured voice providers, not a separate sidecar config:

- STT calls `tools.transcription_tools.transcribe_audio()`
- TTS calls `tools.tts_tool.text_to_speech_tool()`
- `GET /ha/v1/capabilities` reports the detected active providers

If the user's Hermes config says:

```text
stt.provider: local
stt.local.model: base
tts.provider: mimo-tts
tts.providers.mimo-tts.type: command
```

then tell the user that Home Assistant will use local faster-whisper for STT and the `mimo-tts` command provider for TTS.

## Manual Overrides

Only use manual overrides when the user wants Home Assistant to bypass Hermes' active voice config. The sidecar supports:

- `command`: a local Hermes-style command template
- `openai`: OpenAI-compatible HTTP API with bearer token
- `custom`: OpenAI-shaped custom HTTP API, token optional

For local STT, configure a Hermes-style command template:

```bash
HERMES_ASSIST_STT_PROVIDER=command
HERMES_ASSIST_STT_COMMAND='whisper-cli -f {input_path} -otxt -of {output_dir}/transcript'
```

The bridge supports `{input_path}`, `{output_path}`, `{output_dir}`, `{format}`, `{language}`, and `{model}`.

For OpenAI-compatible STT:

```bash
HERMES_ASSIST_STT_PROVIDER=openai
HERMES_ASSIST_STT_BASE_URL=https://api.openai.com/v1
HERMES_ASSIST_STT_ENDPOINT=/audio/transcriptions
HERMES_ASSIST_STT_MODEL=whisper-1
HERMES_ASSIST_STT_API_KEY="$VOICE_TOOLS_OPENAI_KEY"
```

For local TTS, configure a Hermes-style command template:

```bash
HERMES_ASSIST_TTS_PROVIDER=command
HERMES_ASSIST_TTS_COMMAND='piper -m ~/voices/en_US-lessac-medium.onnx -f {output_path} < {input_path}'
HERMES_ASSIST_TTS_FORMAT=wav
```

The bridge supports `{input_path}`, `{text_path}`, `{output_path}`, `{format}`, `{voice}`, `{model}`, `{speed}`, and `{language}`.

For OpenAI-compatible TTS:

```bash
HERMES_ASSIST_TTS_PROVIDER=openai
HERMES_ASSIST_TTS_BASE_URL=https://api.openai.com/v1
HERMES_ASSIST_TTS_ENDPOINT=/audio/speech
HERMES_ASSIST_TTS_MODEL=gpt-4o-mini-tts
HERMES_ASSIST_TTS_VOICE=alloy
HERMES_ASSIST_TTS_FORMAT=mp3
HERMES_ASSIST_TTS_API_KEY="$VOICE_TOOLS_OPENAI_KEY"
```

## Helper Tool

Call `home_assistant_assist_config` to print the exact current URLs and whether STT/TTS commands are configured.
