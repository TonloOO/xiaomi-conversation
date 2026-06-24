"""Config flow for Xiaomi MiMo Conversation."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_PROMPT
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import MiMoAuthError, MiMoClient, MiMoError
from .const import (
    BUILT_IN_VOICES,
    CONF_ASR_MODEL,
    CONF_ENDPOINT,
    CONF_LLM_MODEL,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_TTS_MODEL,
    CONF_TTS_STYLE,
    CONF_TTS_VOICE,
    DEFAULT_NAME,
    DOMAIN,
    SUGGESTED_VALUES,
)


def _schema(values: dict[str, Any]) -> vol.Schema:
    """Return config/options schema."""
    llm_apis = [
        SelectOptionDict(value=api.id, label=api.name)
        for api in llm.async_get_apis(values["hass"])
    ]
    return vol.Schema(
        {
            vol.Required(CONF_ENDPOINT, default=values[CONF_ENDPOINT]): str,
            vol.Required(CONF_API_KEY, default=values.get(CONF_API_KEY, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_LLM_MODEL, default=values[CONF_LLM_MODEL]): str,
            vol.Required(CONF_ASR_MODEL, default=values[CONF_ASR_MODEL]): str,
            vol.Required(CONF_TTS_MODEL, default=values[CONF_TTS_MODEL]): str,
            vol.Required(CONF_TTS_VOICE, default=values[CONF_TTS_VOICE]): SelectSelector(
                SelectSelectorConfig(
                    options=list(BUILT_IN_VOICES),
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_TTS_STYLE, default=values[CONF_TTS_STYLE]): str,
            vol.Optional(CONF_PROMPT, default=values[CONF_PROMPT]): TemplateSelector(),
            vol.Optional(CONF_LLM_HASS_API, default=values[CONF_LLM_HASS_API]): SelectSelector(
                SelectSelectorConfig(
                    options=llm_apis,
                    multiple=True,
                    custom_value=False,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_MAX_TOKENS, default=values[CONF_MAX_TOKENS]): int,
            vol.Optional(CONF_TEMPERATURE, default=values[CONF_TEMPERATURE]): vol.Coerce(float),
            vol.Optional(CONF_TOP_P, default=values[CONF_TOP_P]): vol.Coerce(float),
        }
    )


def _values(hass, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge defaults with stored values."""
    return {"hass": hass, **SUGGESTED_VALUES, **(data or {})}


async def _validate(hass, data: dict[str, Any]) -> None:
    """Validate endpoint/key."""
    await MiMoClient(hass, data[CONF_ENDPOINT], data[CONF_API_KEY]).validate(
        data[CONF_LLM_MODEL]
    )


class XiaomiMiMoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Xiaomi MiMo config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _validate(self.hass, user_input)
            except MiMoAuthError:
                errors["base"] = "invalid_auth"
            except MiMoError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(_values(self.hass, user_input)),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return options flow."""
        return XiaomiMiMoOptionsFlow(config_entry)


class XiaomiMiMoOptionsFlow(OptionsFlow):
    """Handle options updates."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        data = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            merged = {**data, **user_input}
            try:
                await _validate(self.hass, merged)
            except MiMoAuthError:
                errors["base"] = "invalid_auth"
            except MiMoError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(_values(self.hass, data)),
            errors=errors,
        )
