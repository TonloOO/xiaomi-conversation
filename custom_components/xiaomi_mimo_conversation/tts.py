"""Text-to-speech support for Xiaomi MiMo."""

from __future__ import annotations

import base64
from collections.abc import Mapping
import io
import wave
from typing import Any

from homeassistant.components.tts import (
    ATTR_PREFERRED_FORMAT,
    ATTR_VOICE,
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MiMoConfigEntry
from .const import BUILT_IN_VOICES, CONF_TTS_MODEL, CONF_TTS_STYLE, CONF_TTS_VOICE
from .conversation import _data

SAMPLE_RATE = 24000


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MiMoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up TTS entity."""
    async_add_entities([XiaomiMiMoTTSEntity(config_entry)])


def _wav(pcm: bytes) -> bytes:
    """Wrap 24kHz mono PCM16LE bytes in a wav container."""
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return out.getvalue()


class XiaomiMiMoTTSEntity(TextToSpeechEntity):
    """Xiaomi MiMo text-to-speech entity."""

    _attr_has_entity_name = False
    _attr_name = "Xiaomi MiMo TTS"
    _attr_default_language = "zh-CN"
    _attr_supported_languages = ["zh-CN", "en-US"]
    _attr_supported_options = [ATTR_VOICE, ATTR_PREFERRED_FORMAT]

    def __init__(self, entry: MiMoConfigEntry) -> None:
        """Initialize TTS entity."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tts"

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice]:
        """Return supported voices."""
        return [Voice(voice, voice) for voice in BUILT_IN_VOICES]

    @property
    def default_options(self) -> Mapping[str, Any]:
        """Return default options."""
        return {
            ATTR_VOICE: _data(self._entry)[CONF_TTS_VOICE],
            ATTR_PREFERRED_FORMAT: "wav",
        }

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Generate TTS audio."""
        data = _data(self._entry)
        style = data.get(CONF_TTS_STYLE) or "Natural and clear voice."
        voice = options.get(ATTR_VOICE) or data[CONF_TTS_VOICE]
        payload = {
            "model": data[CONF_TTS_MODEL],
            "messages": [
                {"role": "user", "content": style},
                {"role": "assistant", "content": message},
            ],
            "audio": {"format": "pcm16", "voice": voice},
            "stream": True,
        }
        pcm = bytearray()
        async for chunk in self._entry.runtime_data.stream(payload):
            audio = chunk.get("choices", [{}])[0].get("delta", {}).get("audio")
            if audio and audio.get("data"):
                pcm.extend(base64.b64decode(audio["data"]))
        return "wav", _wav(bytes(pcm))
