"""Small Home Assistant voice API sidecar for Hermes Agent."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import threading
from typing import Any
from urllib import error, request
from urllib.parse import urljoin

_LOGGER = logging.getLogger(__name__)

_SERVER_LOCK = threading.Lock()
_SERVER: ThreadingHTTPServer | None = None
_SERVER_THREAD: threading.Thread | None = None


@dataclass(frozen=True)
class BridgeConfig:
    """Runtime configuration for the sidecar bridge."""

    enabled: bool
    host: str
    port: int
    api_key: str | None
    default_language: str
    stt_provider: str
    stt_command: str | None
    stt_base_url: str
    stt_endpoint: str
    stt_api_key: str | None
    stt_model: str
    stt_response_text_field: str
    stt_timeout: int
    tts_provider: str
    tts_command: str | None
    tts_base_url: str
    tts_endpoint: str
    tts_api_key: str | None
    tts_timeout: int
    tts_format: str
    tts_voice: str
    tts_model: str
    hermes_api_base_url: str
    hermes_api_key: str | None


def load_config() -> BridgeConfig:
    """Load bridge configuration from environment variables."""
    return BridgeConfig(
        enabled=_env_bool("HERMES_ASSIST_API_ENABLED", True),
        host=os.environ.get("HERMES_ASSIST_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("HERMES_ASSIST_API_PORT", "8765")),
        api_key=os.environ.get("HERMES_ASSIST_API_KEY") or os.environ.get("API_SERVER_KEY"),
        default_language=os.environ.get("HERMES_ASSIST_LANGUAGE", "en"),
        stt_provider=os.environ.get("HERMES_ASSIST_STT_PROVIDER", "hermes").lower(),
        stt_command=os.environ.get("HERMES_ASSIST_STT_COMMAND") or os.environ.get("HERMES_LOCAL_STT_COMMAND"),
        stt_base_url=os.environ.get("HERMES_ASSIST_STT_BASE_URL", "https://api.openai.com/v1"),
        stt_endpoint=os.environ.get("HERMES_ASSIST_STT_ENDPOINT", "/audio/transcriptions"),
        stt_api_key=(
            os.environ.get("HERMES_ASSIST_STT_API_KEY")
            or os.environ.get("VOICE_TOOLS_OPENAI_KEY")
            or os.environ.get("OPENAI_API_KEY")
        ),
        stt_model=os.environ.get("HERMES_ASSIST_STT_MODEL", "whisper-1"),
        stt_response_text_field=os.environ.get("HERMES_ASSIST_STT_RESPONSE_TEXT_FIELD", "text"),
        stt_timeout=int(os.environ.get("HERMES_ASSIST_STT_TIMEOUT", "300")),
        tts_provider=os.environ.get("HERMES_ASSIST_TTS_PROVIDER", "hermes").lower(),
        tts_command=os.environ.get("HERMES_ASSIST_TTS_COMMAND"),
        tts_base_url=os.environ.get("HERMES_ASSIST_TTS_BASE_URL", "https://api.openai.com/v1"),
        tts_endpoint=os.environ.get("HERMES_ASSIST_TTS_ENDPOINT", "/audio/speech"),
        tts_api_key=(
            os.environ.get("HERMES_ASSIST_TTS_API_KEY")
            or os.environ.get("VOICE_TOOLS_OPENAI_KEY")
            or os.environ.get("OPENAI_API_KEY")
        ),
        tts_timeout=int(os.environ.get("HERMES_ASSIST_TTS_TIMEOUT", "120")),
        tts_format=os.environ.get("HERMES_ASSIST_TTS_FORMAT", "mp3"),
        tts_voice=os.environ.get("HERMES_ASSIST_TTS_VOICE", ""),
        tts_model=os.environ.get("HERMES_ASSIST_TTS_MODEL", "gpt-4o-mini-tts"),
        hermes_api_base_url=os.environ.get("HERMES_API_BASE_URL", "http://localhost:8642"),
        hermes_api_key=os.environ.get("API_SERVER_KEY"),
    )


def ensure_server() -> None:
    """Start the sidecar server once."""
    global _SERVER, _SERVER_THREAD

    config = load_config()
    if not config.enabled:
        _LOGGER.info("Home Assistant Assist sidecar disabled")
        return

    with _SERVER_LOCK:
        if _SERVER is not None:
            return

        handler = _make_handler(config)
        _SERVER = ThreadingHTTPServer((config.host, config.port), handler)
        _SERVER_THREAD = threading.Thread(
            target=_SERVER.serve_forever,
            name="home-assistant-assist-api",
            daemon=True,
        )
        _SERVER_THREAD.start()
        _LOGGER.info(
            "Home Assistant Assist sidecar listening on http://%s:%s",
            config.host,
            config.port,
        )


def config_snapshot() -> dict[str, Any]:
    """Return a redacted configuration snapshot for setup/help tools."""
    config = load_config()
    voice_base_url = f"http://{config.host}:{config.port}"
    return {
        "home_assistant": {
            "base_url": config.hermes_api_base_url,
            "voice_base_url": voice_base_url,
            "conversation_path": "/v1/responses",
            "chat_completions_path": "/v1/chat/completions",
            "stt_path": "/ha/v1/audio/transcriptions",
            "tts_path": "/ha/v1/audio/speech",
            "api_token_env": "API_SERVER_KEY",
            "voice_api_token_env": "HERMES_ASSIST_API_KEY or API_SERVER_KEY",
        },
        "plugin": {
            "enabled": config.enabled,
            "host": config.host,
            "port": config.port,
            "stt": _voice_provider_snapshot(config, "stt"),
            "tts": _voice_provider_snapshot(config, "tts"),
            "tts_format": _active_tts_format(config),
            "default_language": config.default_language,
        },
    }


def _make_handler(config: BridgeConfig):
    class HomeAssistantAssistHandler(BaseHTTPRequestHandler):
        server_version = "HermesAssistBridge/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            _LOGGER.debug("Home Assistant Assist API: " + format, *args)

        def do_GET(self) -> None:
            if not self._authorized(config):
                self._json({"error": "unauthorized"}, status=401)
                return

            if self.path == "/health":
                self._json({"status": "ok", "service": "home-assistant-assist"})
                return

            if self.path == "/ha/v1/capabilities":
                self._json(
                    {
                        "stt": {
                            "available": _stt_available(config),
                            "backend": config.stt_provider,
                            "provider": _configured_stt_provider(),
                            "remote": _is_configured_voice_remote("stt"),
                            "base_url": _active_stt_base_url(config),
                            "model": _configured_stt_model(config),
                            "formats": ["wav"],
                            "sample_rates": [16000],
                            "channels": [1],
                            "language": config.default_language,
                        },
                        "tts": {
                            "available": _tts_available(config),
                            "backend": config.tts_provider,
                            "provider": _configured_tts_provider(),
                            "remote": _is_configured_voice_remote("tts"),
                            "base_url": _active_tts_base_url(config),
                            "model": _configured_tts_model(config),
                            "voice": _configured_tts_voice(config),
                            "formats": [_active_tts_format(config)],
                            "language": config.default_language,
                        },
                    }
                )
                return

            self._json({"error": "not_found"}, status=404)

        def do_POST(self) -> None:
            if not self._authorized(config):
                self._json({"error": "unauthorized"}, status=401)
                return

            if self.path == "/ha/v1/audio/transcriptions":
                self._handle_stt(config)
                return

            if self.path == "/ha/v1/audio/speech":
                self._handle_tts(config)
                return

            self._json({"error": "not_found"}, status=404)

        def _handle_stt(self, config: BridgeConfig) -> None:
            audio = self._read_body()
            if not _stt_available(config):
                self._json({"error": "stt_not_configured"}, status=503)
                return

            language = self.headers.get("X-Hermes-Language") or config.default_language
            try:
                transcript = transcribe_audio(config, audio, language)
            except CommandError as err:
                self._json({"error": str(err)}, status=500)
                return

            self._json({"text": transcript, "language": language})

        def _handle_tts(self, config: BridgeConfig) -> None:
            body = self._read_body()
            if not _tts_available(config):
                self._json({"error": "tts_not_configured"}, status=503)
                return

            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._json({"error": "invalid_json"}, status=400)
                return

            text = str(payload.get("text") or payload.get("input") or "").strip()
            if not text:
                self._json({"error": "missing_text"}, status=400)
                return

            language = str(payload.get("language") or config.default_language)
            options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
            try:
                audio = synthesize_speech(config, text, language, options)
            except CommandError as err:
                self._json({"error": str(err)}, status=500)
                return

            self.send_response(200)
            self.send_header("Content-Type", _content_type(_active_tts_format(config)))
            self.send_header("Content-Length", str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0"))
            return self.rfile.read(length)

        def _authorized(self, config: BridgeConfig) -> bool:
            if not config.api_key:
                return True
            header = self.headers.get("Authorization", "")
            return header == f"Bearer {config.api_key}"

        def _json(self, payload: dict[str, Any], status: int = 200) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return HomeAssistantAssistHandler


class CommandError(Exception):
    """A voice command failed."""


def transcribe_audio(config: BridgeConfig, audio: bytes, language: str) -> str:
    """Transcribe audio using the configured STT backend."""
    if config.stt_provider == "hermes":
        return run_hermes_stt(audio, language)
    if config.stt_provider == "command":
        return run_stt_command(config, audio, language)
    if config.stt_provider in {"openai", "custom"}:
        return run_stt_http(config, audio, language)
    raise CommandError(f"Unsupported STT provider: {config.stt_provider}")


def synthesize_speech(config: BridgeConfig, text: str, language: str, options: dict[str, Any]) -> bytes:
    """Synthesize speech using the configured TTS backend."""
    if config.tts_provider == "hermes":
        return run_hermes_tts(config, text, options)
    if config.tts_provider == "command":
        return run_tts_command(config, text, language, options)
    if config.tts_provider in {"openai", "custom"}:
        return run_tts_http(config, text, language, options)
    raise CommandError(f"Unsupported TTS provider: {config.tts_provider}")


def run_hermes_stt(audio: bytes, language: str) -> str:
    """Use Hermes' own configured STT provider."""
    with tempfile.TemporaryDirectory(prefix="hermes-assist-native-stt-") as tmp_dir:
        input_path = Path(tmp_dir) / "input.wav"
        input_path.write_bytes(audio)

        try:
            from tools.transcription_tools import transcribe_audio as hermes_transcribe_audio
        except Exception as err:
            raise CommandError("Hermes transcription tools are not importable in this process") from err

        result = hermes_transcribe_audio(str(input_path))
        if not isinstance(result, dict):
            raise CommandError("Hermes STT returned an unexpected result")
        if not result.get("success"):
            raise CommandError(str(result.get("error") or "Hermes STT failed"))
        transcript = str(result.get("transcript") or "").strip()
        if not transcript:
            raise CommandError("Hermes STT returned no transcript")
        return transcript


def run_hermes_tts(config: BridgeConfig, text: str, options: dict[str, Any]) -> bytes:
    """Use Hermes' own configured TTS provider."""
    output_format = _configured_tts_output_format(config)
    with tempfile.TemporaryDirectory(prefix="hermes-assist-native-tts-") as tmp_dir:
        output_path = Path(tmp_dir) / f"speech.{output_format}"

        try:
            from tools.tts_tool import text_to_speech_tool
        except Exception as err:
            raise CommandError("Hermes TTS tool is not importable in this process") from err

        result_raw = text_to_speech_tool(text, output_path=str(output_path))
        try:
            result = json.loads(result_raw)
        except (TypeError, json.JSONDecodeError) as err:
            raise CommandError("Hermes TTS returned an unexpected result") from err
        if not isinstance(result, dict) or not result.get("success"):
            raise CommandError(str(result.get("error") if isinstance(result, dict) else "Hermes TTS failed"))

        file_path = Path(str(result.get("file_path") or output_path)).expanduser()
        if not file_path.exists() or file_path.stat().st_size <= 0:
            raise CommandError("Hermes TTS produced no audio file")
        return file_path.read_bytes()


def run_stt_command(config: BridgeConfig, audio: bytes, language: str) -> str:
    """Run a Hermes-style STT command template."""
    with tempfile.TemporaryDirectory(prefix="hermes-assist-stt-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / "input.wav"
        output_path = tmp_path / "transcript.txt"
        input_path.write_bytes(audio)

        command = _render_command(
            config.stt_command or "",
            {
                "input_path": input_path,
                "output_path": output_path,
                "output_dir": tmp_path,
                "format": "txt",
                "language": language,
                "model": config.stt_model,
            },
        )
        completed = _run_command(command, config.stt_timeout)
        if output_path.exists():
            transcript = output_path.read_text(encoding="utf-8").strip()
        else:
            transcript = completed.stdout.strip()

        if not transcript:
            raise CommandError("STT command produced no transcript")
        return transcript


def run_stt_http(config: BridgeConfig, audio: bytes, language: str) -> str:
    """Run OpenAI-compatible or custom HTTP STT."""
    if not config.stt_api_key and config.stt_provider == "openai":
        raise CommandError("STT API key is not configured")

    boundary = "hermes-assist-boundary"
    fields = {
        "model": config.stt_model,
        "language": language,
    }
    body = _multipart_body(
        boundary,
        fields,
        "file",
        "audio.wav",
        "audio/wav",
        audio,
    )
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    if config.stt_api_key:
        headers["Authorization"] = f"Bearer {config.stt_api_key}"

    payload = _http_json(
        _join_url(config.stt_base_url, config.stt_endpoint),
        body,
        headers,
        config.stt_timeout,
    )
    text = _nested_value(payload, config.stt_response_text_field)
    if not isinstance(text, str) or not text.strip():
        raise CommandError("STT HTTP response did not include transcript text")
    return text.strip()


def run_tts_command(config: BridgeConfig, text: str, language: str, options: dict[str, Any]) -> bytes:
    """Run a Hermes-style TTS command template."""
    with tempfile.TemporaryDirectory(prefix="hermes-assist-tts-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / "input.txt"
        output_path = tmp_path / f"speech.{config.tts_format}"
        input_path.write_text(text, encoding="utf-8")

        command = _render_command(
            config.tts_command or "",
            {
                "input_path": input_path,
                "text_path": input_path,
                "output_path": output_path,
                "format": config.tts_format,
                "voice": str(options.get("voice") or config.tts_voice),
                "model": str(options.get("model") or config.tts_model),
                "speed": str(options.get("speed") or os.environ.get("HERMES_ASSIST_TTS_SPEED", "1.0")),
                "language": language,
            },
        )
        completed = _run_command(command, config.tts_timeout)
        if output_path.exists():
            audio = output_path.read_bytes()
        else:
            audio = completed.stdout.encode("utf-8")

        if not audio:
            raise CommandError("TTS command produced no audio")
        return audio


def run_tts_http(config: BridgeConfig, text: str, language: str, options: dict[str, Any]) -> bytes:
    """Run OpenAI-compatible or custom HTTP TTS."""
    if not config.tts_api_key and config.tts_provider == "openai":
        raise CommandError("TTS API key is not configured")

    payload = {
        "model": str(options.get("model") or config.tts_model),
        "input": text,
        "voice": str(options.get("voice") or config.tts_voice or "alloy"),
        "response_format": config.tts_format,
        "speed": float(options.get("speed") or os.environ.get("HERMES_ASSIST_TTS_SPEED", "1.0")),
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": _content_type(config.tts_format),
    }
    if config.tts_api_key:
        headers["Authorization"] = f"Bearer {config.tts_api_key}"

    return _http_bytes(
        _join_url(config.tts_base_url, config.tts_endpoint),
        json.dumps(payload).encode("utf-8"),
        headers,
        config.tts_timeout,
    )


def _run_command(command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "command failed").strip()
        raise CommandError(detail[:500])
    return completed


def _http_json(url: str, data: bytes, headers: dict[str, str], timeout: int) -> dict[str, Any]:
    raw = _http_bytes(url, data, headers, timeout)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise CommandError("HTTP response was not valid JSON") from err
    if not isinstance(payload, dict):
        raise CommandError("HTTP response JSON was not an object")
    return payload


def _http_bytes(url: str, data: bytes, headers: dict[str, str], timeout: int) -> bytes:
    http_request = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            result = response.read()
    except error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise CommandError(f"HTTP {err.code}: {detail[:500]}") from err
    except error.URLError as err:
        raise CommandError(f"HTTP request failed: {err.reason}") from err
    if not result:
        raise CommandError("HTTP response was empty")
    return result


def _multipart_body(
    boundary: str,
    fields: dict[str, str],
    file_field: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks)


def _nested_value(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _join_url(base_url: str, endpoint: str) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", endpoint.lstrip("/"))


def _render_command(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", _shell_quote(str(value)))
    return rendered


def _shell_quote(value: str) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline([value])
    return shlex.quote(value)


def _content_type(extension: str) -> str:
    return {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }.get(extension.lower(), "application/octet-stream")


def _active_tts_format(config: BridgeConfig) -> str:
    if config.tts_provider == "hermes":
        return _configured_tts_output_format(config)
    return config.tts_format


def _active_stt_base_url(config: BridgeConfig) -> str:
    if config.stt_provider == "hermes":
        return ""
    return _redacted_base_url(config.stt_base_url)


def _active_tts_base_url(config: BridgeConfig) -> str:
    if config.tts_provider == "hermes":
        return ""
    return _redacted_base_url(config.tts_base_url)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _stt_available(config: BridgeConfig) -> bool:
    if config.stt_provider == "hermes":
        stt_config = _load_hermes_section("stt")
        return _truthy(stt_config.get("enabled", True))
    if config.stt_provider == "command":
        return bool(config.stt_command)
    if config.stt_provider == "openai":
        return bool(config.stt_api_key)
    return config.stt_provider == "custom"


def _tts_available(config: BridgeConfig) -> bool:
    if config.tts_provider == "hermes":
        return True
    if config.tts_provider == "command":
        return bool(config.tts_command)
    if config.tts_provider == "openai":
        return bool(config.tts_api_key)
    return config.tts_provider == "custom"


def _provider_snapshot(provider: str, command_configured: bool, base_url: str, api_key_configured: bool) -> dict[str, Any]:
    return {
        "provider": provider,
        "remote": provider in {"openai", "custom"},
        "command_configured": command_configured,
        "base_url": _redacted_base_url(base_url),
        "api_key_configured": api_key_configured,
    }


def _redacted_base_url(base_url: str) -> str:
    return base_url.split("?")[0]


def _load_hermes_config() -> dict[str, Any]:
    """Load Hermes config using Hermes helpers when available."""
    try:
        from hermes_cli.config import load_config

        loaded = load_config()
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        pass

    config_path = Path(os.environ.get("HERMES_CONFIG", "~/.hermes/config.yaml")).expanduser()
    if not config_path.exists():
        return {}
    try:
        import yaml

        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _load_hermes_section(name: str) -> dict[str, Any]:
    section = _load_hermes_config().get(name, {})
    return section if isinstance(section, dict) else {}


def _configured_stt_provider() -> str:
    return str(_load_hermes_section("stt").get("provider") or "local")


def _configured_tts_provider() -> str:
    return str(_load_hermes_section("tts").get("provider") or "edge")


def _configured_stt_model(config: BridgeConfig) -> str:
    stt_config = _load_hermes_section("stt")
    provider = _configured_stt_provider()
    provider_config = _section(stt_config, provider)
    local_config = _section(stt_config, "local")
    return str(
        provider_config.get("model")
        or local_config.get("model")
        or stt_config.get("model")
        or config.stt_model
    )


def _configured_tts_model(config: BridgeConfig) -> str:
    tts_config = _load_hermes_section("tts")
    provider = _configured_tts_provider()
    provider_config = _get_named_tts_config(tts_config, provider)
    if str(provider_config.get("type") or "").lower() == "command":
        return str(provider_config.get("model") or "")
    return str(provider_config.get("model") or provider_config.get("model_id") or config.tts_model)


def _configured_tts_voice(config: BridgeConfig) -> str:
    tts_config = _load_hermes_section("tts")
    provider = _configured_tts_provider()
    provider_config = _get_named_tts_config(tts_config, provider)
    return str(
        provider_config.get("voice")
        or provider_config.get("voice_id")
        or config.tts_voice
    )


def _configured_tts_output_format(config: BridgeConfig) -> str:
    tts_config = _load_hermes_section("tts")
    provider = _configured_tts_provider()
    provider_config = _get_named_tts_config(tts_config, provider)
    return str(provider_config.get("output_format") or provider_config.get("format") or config.tts_format)


def _get_named_tts_config(tts_config: dict[str, Any], provider: str) -> dict[str, Any]:
    providers = _section(tts_config, "providers")
    provider_config = providers.get(provider)
    if isinstance(provider_config, dict):
        return provider_config
    return _section(tts_config, provider)


def _section(parent: dict[str, Any], name: str) -> dict[str, Any]:
    value = parent.get(name, {})
    return value if isinstance(value, dict) else {}


def _is_configured_voice_remote(kind: str) -> bool:
    provider = _configured_stt_provider() if kind == "stt" else _configured_tts_provider()
    provider_config = (
        _section(_load_hermes_section("stt"), provider)
        if kind == "stt"
        else _get_named_tts_config(_load_hermes_section("tts"), provider)
    )
    if str(provider_config.get("type") or "").lower() == "command":
        return False
    return provider.lower() in {
        "groq",
        "openai",
        "mistral",
        "xai",
        "elevenlabs",
        "minimax",
        "gemini",
    }


def _voice_provider_snapshot(config: BridgeConfig, kind: str) -> dict[str, Any]:
    if kind == "stt":
        provider = _configured_stt_provider()
        backend = config.stt_provider
        model = _configured_stt_model(config)
        manual = _provider_snapshot(
            config.stt_provider,
            bool(config.stt_command),
            config.stt_base_url,
            bool(config.stt_api_key),
        )
    else:
        provider = _configured_tts_provider()
        backend = config.tts_provider
        model = _configured_tts_model(config)
        manual = _provider_snapshot(
            config.tts_provider,
            bool(config.tts_command),
            config.tts_base_url,
            bool(config.tts_api_key),
        )

    if backend != "hermes":
        return manual

    return {
        "backend": "hermes",
        "provider": provider,
        "remote": _is_configured_voice_remote(kind),
        "model": model,
        "voice": _configured_tts_voice(config) if kind == "tts" else "",
        "format": _configured_tts_output_format(config) if kind == "tts" else "",
        "uses_hermes_config": True,
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}
    return bool(value)
