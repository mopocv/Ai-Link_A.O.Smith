"""The Ai-Link A.O. Smith integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .api import AOSmithAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["water_heater", "sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ai-Link A.O. Smith from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize API connection with provided tokens
    api = AOSmithAPI(
        access_token=entry.data["access_token"],
        user_id=entry.data["user_id"],
        family_id=entry.data["family_id"],
        mobile=entry.data.get("mobile")
    )
    
    await api.async_authenticate()
    hass.data[DOMAIN][entry.entry_id] = api
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    
    if unload_ok:
        api = hass.data[DOMAIN].pop(entry.entry_id)
        await api.close()
    
    return unload_ok