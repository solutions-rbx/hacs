# Hermes Assist

Hermes Assist is a HACS custom integration that adds Hermes Agent as a Home Assistant Assist conversation agent.

It does **not** provide STT or TTS. Home Assistant should use its normal Assist pipeline STT/TTS providers for microphones and speakers.

## Features

- Conversation agent provider for Home Assistant Assist
- HACS-only setup
- First-time setup can ask Hermes Agent to create a Home Assistant skill
- OpenAI-compatible Hermes `/v1/responses` support
- Optional `/v1/chat/completions` mode
- Provider-only behavior: it does not edit Assist pipelines automatically

## HACS Installation

1. In HACS, open **Custom repositories**.
2. Add this repository URL.
3. Select **Integration** as the category.
4. Install **Hermes Assist**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration** and search for **Hermes Assist**.

## Hermes Setup

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

## What Setup Tells Hermes

If enabled in the setup wizard, Hermes Assist sends Hermes Agent this first-time setup instruction:

```text
Create or update a Hermes Agent skill named `home-assistant-assist`.
The skill should teach Hermes how to work well as the conversation agent for Home Assistant Assist through the Hermes Assist HACS integration.
The integration sends user text from Home Assistant Assist to Hermes Agent and expects concise natural-language responses.
It does not provide STT or TTS.
Home Assistant handles microphones, speakers, STT, TTS, and Assist pipelines separately.
The skill should explain what Hermes can do: answer smart-home questions, reason about the user's request, call any Home Assistant tools or APIs already available to Hermes, summarize device state, ask a clarifying question when a command is ambiguous, and avoid claiming an action succeeded unless a tool/API confirms it.
The skill should explain how Hermes should behave: keep responses short for voice use, mention the room/device acted on, use the user's language when possible, preserve context across turns, and be honest when Home Assistant access is missing.
Also include examples: turning lights on/off, setting climate temperature, checking doors, explaining automations, creating reminders if Hermes has that tool, and asking which room when the target is unclear.
If you can write skills to disk, create the skill now. If you cannot write files, return the complete skill content and exact install instructions. Reply with a short summary of what you created or what the user must do next.
```

The goal is to give Hermes good context about what Home Assistant Assist can do and how Hermes should respond.

## Assist Pipeline Setup

After setup, open Home Assistant Assist pipeline settings and choose:

- Your preferred STT provider
- **Hermes Assist** as the conversation agent
- Your preferred TTS provider

Hermes Assist only handles the conversation-agent step.

