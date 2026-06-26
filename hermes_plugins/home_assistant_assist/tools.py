"""Tool handlers for the Home Assistant Assist Hermes plugin."""

from __future__ import annotations

import json

from .server import config_snapshot


def home_assistant_assist_config(args: dict, **kwargs) -> str:
    """Return Home Assistant configuration details as JSON."""
    return json.dumps(config_snapshot(), indent=2)

