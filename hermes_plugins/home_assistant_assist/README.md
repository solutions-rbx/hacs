# Hermes Home Assistant Assist Plugin

This is a companion Hermes Agent plugin for the Hermes Assist Home Assistant HACS integration.

It starts a small local HTTP sidecar that gives Home Assistant stable STT and TTS endpoints while conversation continues to use Hermes Agent's official OpenAI-compatible API server.

## Install

Copy this folder to:

```text
~/.hermes/plugins/home_assistant_assist/
```

Enable it:

```bash
hermes plugins enable home_assistant_assist
```

Start Hermes with plugin debugging if needed:

```bash
HERMES_PLUGINS_DEBUG=1 hermes gateway
```

## Environment

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
HERMES_ASSIST_API_ENABLED=true
HERMES_ASSIST_API_HOST=0.0.0.0
HERMES_ASSIST_API_PORT=8765
HERMES_ASSIST_API_KEY="$API_SERVER_KEY"
```

## STT/TTS Backends

By default the sidecar uses Hermes' already configured providers:

```bash
HERMES_ASSIST_STT_PROVIDER=hermes
HERMES_ASSIST_TTS_PROVIDER=hermes
```

In this mode, STT is routed through Hermes' own `tools.transcription_tools.transcribe_audio()` and TTS is routed through Hermes' own `tools.tts_tool.text_to_speech_tool()`. That means Home Assistant automatically uses whatever is active in `~/.hermes/config.yaml`, including local faster-whisper, OpenAI/Groq/Mistral/xAI STT, built-in TTS providers, and custom command-type TTS providers like `mimo-tts`.

The sidecar exposes the detected provider metadata at:

```text
GET /ha/v1/capabilities
```

Example for a local STT plus custom command TTS setup:

```json
{
  "stt": {"backend": "hermes", "provider": "local", "remote": false, "model": "base"},
  "tts": {"backend": "hermes", "provider": "mimo-tts", "remote": false}
}
```

## Manual Override Backends

Use these only when you want the Home Assistant sidecar to bypass Hermes' active voice config.

Local command STT/TTS:

```bash
HERMES_ASSIST_STT_PROVIDER=command
HERMES_ASSIST_STT_COMMAND='whisper-cli -f {input_path} -otxt -of {output_dir}/transcript'
HERMES_ASSIST_TTS_PROVIDER=command
HERMES_ASSIST_TTS_COMMAND='piper -m ~/voices/en_US-lessac-medium.onnx -f {output_path} < {input_path}'
HERMES_ASSIST_TTS_FORMAT=wav
```

OpenAI-compatible STT/TTS:

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

Custom HTTP TTS that accepts an OpenAI-style JSON body and returns audio bytes:

```bash
HERMES_ASSIST_STT_PROVIDER=custom
HERMES_ASSIST_STT_BASE_URL=http://stt-server:8080
HERMES_ASSIST_STT_ENDPOINT=/v1/audio/transcriptions
HERMES_ASSIST_STT_RESPONSE_TEXT_FIELD=text

HERMES_ASSIST_TTS_PROVIDER=custom
HERMES_ASSIST_TTS_BASE_URL=http://tts-server:8080
HERMES_ASSIST_TTS_ENDPOINT=/v1/audio/speech
HERMES_ASSIST_TTS_MODEL=my-tts-model
HERMES_ASSIST_TTS_VOICE=default
HERMES_ASSIST_TTS_FORMAT=wav
```

## Home Assistant Integration Settings

- Base URL: `http://<hermes-host>:8642`
- Voice base URL: `http://<hermes-host>:8765`
- API token: `API_SERVER_KEY`
- STT path: `/ha/v1/audio/transcriptions`
- TTS path: `/ha/v1/audio/speech`
