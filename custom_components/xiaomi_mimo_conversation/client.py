"""Small MiMo API client."""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator, Iterable
from typing import Any

from .const import DEFAULT_ENDPOINT


class MiMoError(Exception):
    """MiMo API error."""


class MiMoAuthError(MiMoError):
    """MiMo authentication error."""


def chat_url(endpoint: str) -> str:
    """Return the chat completions URL for a MiMo endpoint."""
    endpoint = (endpoint or DEFAULT_ENDPOINT).rstrip("/")
    if endpoint.endswith("/chat/completions"):
        return endpoint
    return f"{endpoint}/chat/completions"


def message_text(response: dict[str, Any]) -> str:
    """Extract assistant text from a chat completion response."""
    content = response["choices"][0]["message"].get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return ""


def message_audio(response: dict[str, Any]) -> bytes:
    """Extract assistant audio bytes from a TTS chat completion response."""
    audio = response["choices"][0]["message"].get("audio") or {}
    data = audio.get("data")
    if not data:
        raise MiMoError("MiMo response did not include audio data")
    return base64.b64decode(data)


def stream_json(line: str) -> dict[str, Any] | None:
    """Parse one OpenAI-compatible server-sent event line."""
    if not line.startswith("data:"):
        return None
    data = line.removeprefix("data:").strip()
    if not data or data == "[DONE]":
        return None
    return json.loads(data)


def first_delta(chunk: dict[str, Any]) -> dict[str, Any]:
    """Return the first streaming delta, if this chunk has one."""
    choices = chunk.get("choices") or []
    if not choices:
        return {}
    return choices[0].get("delta") or {}


def delta_content(chunk: dict[str, Any]) -> str:
    """Return text content from a streaming chunk."""
    return first_delta(chunk).get("content") or ""


class MiMoClient:
    """Minimal async client for Xiaomi MiMo chat-completions APIs."""

    def __init__(self, hass, endpoint: str, api_key: str) -> None:
        """Initialize the client."""
        from homeassistant.helpers.httpx_client import get_async_client

        self._client = get_async_client(hass)
        self._url = chat_url(endpoint)
        self._api_key = api_key

    async def post(self, payload: dict[str, Any], timeout: float = 60.0) -> dict[str, Any]:
        """Post to MiMo chat completions."""
        response = await self._client.post(
            self._url,
            headers={"api-key": self._api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        if response.status_code in (401, 403):
            raise MiMoAuthError(response.text)
        if response.is_error:
            raise MiMoError(response.text)
        return response.json()

    async def stream(
        self, payload: dict[str, Any], timeout: float = 60.0
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream MiMo chat completions."""
        async with self._client.stream(
            "POST",
            self._url,
            headers={"api-key": self._api_key, "Content-Type": "application/json"},
            json={**payload, "stream": True},
            timeout=timeout,
        ) as response:
            if response.status_code in (401, 403):
                raise MiMoAuthError((await response.aread()).decode())
            if response.is_error:
                raise MiMoError((await response.aread()).decode())
            async for line in response.aiter_lines():
                if chunk := stream_json(line):
                    yield chunk

    async def validate(self, model: str) -> None:
        """Validate endpoint/key with a tiny request."""
        async for _chunk in self.stream(
            {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_completion_tokens": 1,
            },
            timeout=10.0,
        ):
            break
