"""Speech-to-text support for Xiaomi MiMo."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterable
import io
import wave

from homeassistant.components import stt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MiMoConfigEntry
from .client import first_delta
from .const import CONF_ASR_MODEL
from .conversation import _data


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MiMoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up STT entity."""
    async_add_entities([XiaomiMiMoSTTEntity(config_entry)])


class XiaomiMiMoSTTEntity(stt.SpeechToTextEntity):
    """Xiaomi MiMo speech-to-text entity."""

    _attr_has_entity_name = False
    _attr_name = "Xiaomi MiMo STT"

    def __init__(self, entry: MiMoConfigEntry) -> None:
        """Initialize STT entity."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_stt"

    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return ["zh-CN", "en-US"]

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        """Return supported formats."""
        return [stt.AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        """Return supported codecs."""
        return [stt.AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        """Return supported bit rates."""
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        """Return supported sample rates."""
        return [
            stt.AudioSampleRates.SAMPLERATE_16000,
            stt.AudioSampleRates.SAMPLERATE_24000,
            stt.AudioSampleRates.SAMPLERATE_48000,
        ]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        """Return supported channels."""
        return [stt.AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> stt.SpeechResult:
        """Process an audio stream."""
        audio = bytearray()
        async for chunk in stream:
            audio.extend(chunk)

        wav = io.BytesIO()
        with wave.open(wav, "wb") as wf:
            wf.setnchannels(metadata.channel.value)
            wf.setsampwidth(metadata.bit_rate.value // 8)
            wf.setframerate(metadata.sample_rate.value)
            wf.writeframes(bytes(audio))

        language = "zh" if metadata.language.startswith("zh") else "en"
        payload = {
            "model": _data(self._entry)[CONF_ASR_MODEL],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": "data:audio/wav;base64,"
                                + base64.b64encode(wav.getvalue()).decode()
                            },
                        }
                    ],
                }
            ],
            "asr_options": {"language": language},
        }
        text = ""
        async for chunk in self._entry.runtime_data.stream(payload):
            text += first_delta(chunk).get("content", "")
        if text:
            return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)
        return stt.SpeechResult(None, stt.SpeechResultState.ERROR)
