# Xiaomi MiMo Conversation for Home Assistant

Custom Home Assistant integration for Xiaomi MiMo OpenAI-compatible chat completions.

## Features

- Conversation agent with streaming responses
- Optional Home Assistant Assist LLM tool control
- MiMo ASR via `mimo-v2.5-asr`
- MiMo TTS via `mimo-v2.5-tts`
- Configurable endpoint, API key, models, voice, and TTS style

## Install

Copy `custom_components/xiaomi_mimo_conversation` to your Home Assistant
`/config/custom_components/` directory, restart Home Assistant, then add
`Xiaomi MiMo Conversation` from Settings > Devices & services.

Default OpenAI-compatible endpoint:

```text
https://api.xiaomimimo.com/v1
```

Token Plan endpoint can also be used if your account provides one.

## Test

```bash
python3 -m pytest -q tests/test_client.py
python3 -m compileall -q custom_components tests
```
