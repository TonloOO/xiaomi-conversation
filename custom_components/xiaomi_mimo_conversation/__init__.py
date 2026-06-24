"""The Xiaomi MiMo Conversation integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant

from .client import MiMoClient
from .const import CONF_ENDPOINT, DOMAIN

PLATFORMS = (Platform.CONVERSATION, Platform.STT, Platform.TTS)

type MiMoConfigEntry = ConfigEntry[MiMoClient]


async def async_setup_entry(hass: HomeAssistant, entry: MiMoConfigEntry) -> bool:
    """Set up Xiaomi MiMo from a config entry."""
    data = {**entry.data, **entry.options}
    entry.runtime_data = MiMoClient(
        hass,
        data[CONF_ENDPOINT],
        data[CONF_API_KEY],
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MiMoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: MiMoConfigEntry) -> None:
    """Reload entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
