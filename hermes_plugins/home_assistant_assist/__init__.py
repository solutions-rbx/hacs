"""Home Assistant Assist companion plugin for Hermes Agent."""

from __future__ import annotations

import logging
from pathlib import Path

from . import schemas, server, tools

_LOGGER = logging.getLogger(__name__)


def _on_session_start(**kwargs) -> None:
    """Ensure the sidecar API is running when Hermes starts a session."""
    server.ensure_server()


def register(ctx) -> None:
    """Register plugin tools, hooks, skills, and sidecar API."""
    server.ensure_server()

    ctx.register_tool(
        name="home_assistant_assist_config",
        toolset="home_assistant_assist",
        schema=schemas.HOME_ASSISTANT_ASSIST_CONFIG,
        handler=tools.home_assistant_assist_config,
    )
    ctx.register_hook("on_session_start", _on_session_start)

    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)

    _LOGGER.info("Home Assistant Assist plugin registered")

