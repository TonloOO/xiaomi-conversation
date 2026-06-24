"""Conversation support for Xiaomi MiMo."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Literal

import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent, llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MiMoConfigEntry
from .client import MiMoError, first_delta
from .const import (
    CONF_LLM_MODEL,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DOMAIN,
)

MAX_TOOL_ITERATIONS = 10


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MiMoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up conversation entity."""
    async_add_entities([XiaomiMiMoConversationEntity(config_entry)])


def _data(entry: MiMoConfigEntry) -> dict[str, Any]:
    """Return config data merged with options."""
    return {**entry.data, **entry.options}


def _tool_schema(tool: llm.Tool, api: llm.APIInstance) -> dict[str, Any]:
    """Return an OpenAI-compatible tool schema."""
    try:
        parameters = convert(tool.parameters, custom_serializer=api.custom_serializer)
    except (TypeError, vol.Invalid, ValueError):
        parameters = {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": parameters,
        },
    }


def _message(content: conversation.Content) -> dict[str, Any] | None:
    """Convert HA chat content to OpenAI-compatible messages."""
    if isinstance(content, conversation.SystemContent):
        return {"role": "system", "content": content.content} if content.content else None
    if isinstance(content, conversation.UserContent):
        return {"role": "user", "content": content.content}
    if isinstance(content, conversation.ToolResultContent):
        return {
            "role": "tool",
            "tool_call_id": content.tool_call_id,
            "name": content.tool_name,
            "content": json.dumps(content.tool_result),
        }
    if isinstance(content, conversation.AssistantContent):
        message: dict[str, Any] = {
            "role": "assistant",
            "content": content.content or "",
        }
        if content.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.tool_name,
                        "arguments": json.dumps(call.tool_args),
                    },
                }
                for call in content.tool_calls
            ]
        return message
    return None


def _payload(data: dict[str, Any], chat_log: conversation.ChatLog) -> dict[str, Any]:
    """Build a MiMo chat-completions payload."""
    payload: dict[str, Any] = {
        "model": data[CONF_LLM_MODEL],
        "messages": [
            message for content in chat_log.content if (message := _message(content))
        ],
        "max_completion_tokens": data[CONF_MAX_TOKENS],
        "temperature": data[CONF_TEMPERATURE],
        "top_p": data[CONF_TOP_P],
        "stream": True,
    }
    if chat_log.llm_api and chat_log.llm_api.tools:
        payload["tools"] = [
            _tool_schema(tool, chat_log.llm_api) for tool in chat_log.llm_api.tools
        ]
        payload["tool_choice"] = "auto"
    return payload


async def _delta_stream(
    entry: MiMoConfigEntry, payload: dict[str, Any]
) -> AsyncIterator[conversation.AssistantContentDeltaDict]:
    """Convert MiMo stream chunks into HA chat-log deltas."""
    tool_calls: dict[int, dict[str, str]] = {}
    yield {"role": "assistant"}
    async for chunk in entry.runtime_data.stream(payload):
        delta = first_delta(chunk)
        if content := delta.get("content"):
            yield {"content": content}
        if thinking := delta.get("reasoning_content"):
            yield {"thinking_content": thinking}
        for call in delta.get("tool_calls") or []:
            item = tool_calls.setdefault(
                call.get("index", len(tool_calls)),
                {"id": "", "name": "", "arguments": ""},
            )
            if call.get("id"):
                item["id"] = call["id"]
            function = call.get("function") or {}
            if function.get("name"):
                item["name"] = function["name"]
            if function.get("arguments"):
                item["arguments"] += function["arguments"]

    if tool_calls:
        yield {
            "tool_calls": [
                llm.ToolInput(
                    id=call["id"],
                    tool_name=call["name"],
                    tool_args=json.loads(call["arguments"] or "{}"),
                )
                for call in tool_calls.values()
                if call["id"] and call["name"]
            ]
        }


class XiaomiMiMoConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """Xiaomi MiMo conversation agent."""

    _attr_has_entity_name = False
    _attr_supports_streaming = True

    def __init__(self, entry: MiMoConfigEntry) -> None:
        """Initialize the agent."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_conversation"
        self._attr_name = entry.title
        if _data(entry).get(CONF_LLM_HASS_API):
            self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register as conversation agent."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister conversation agent."""
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process user input with MiMo."""
        data = _data(self._entry)
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                data.get(CONF_LLM_HASS_API),
                data.get(CONF_PROMPT),
                user_input.extra_system_prompt,
            )
            for _ in range(MAX_TOOL_ITERATIONS):
                async for _content in chat_log.async_add_delta_content_stream(
                    self.entity_id or DOMAIN,
                    _delta_stream(self._entry, _payload(data, chat_log)),
                ):
                    pass
                if not chat_log.unresponded_tool_results:
                    break
        except conversation.ConverseError as err:
            return err.as_conversation_result()
        except MiMoError as err:
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_error(intent.IntentResponseErrorCode.UNKNOWN, str(err))
            return conversation.ConversationResult(
                response=response,
                conversation_id=chat_log.conversation_id,
            )

        return conversation.async_get_result_from_chat_log(user_input, chat_log)
