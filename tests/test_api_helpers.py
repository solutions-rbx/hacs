"""Tests for Hermes API helper parsing."""

from custom_components.hermes_assist.api import _extract_text


def test_extract_text_from_simple_response() -> None:
    """Extract text from simple response payload."""
    assert _extract_text({"response": "hello"}) == "hello"
    assert _extract_text({"text": "turn on lights"}) == "turn on lights"


def test_extract_text_from_openai_shape() -> None:
    """Extract text from OpenAI-like response payload."""
    payload = {"choices": [{"message": {"content": "done"}}]}
    assert _extract_text(payload) == "done"


def test_extract_text_from_responses_shape() -> None:
    """Extract text from OpenAI Responses API payload."""
    payload = {
        "output": [
            {"type": "function_call", "name": "ha_list_entities"},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "The lights are on."}],
            },
        ]
    }
    assert _extract_text(payload) == "The lights are on."

