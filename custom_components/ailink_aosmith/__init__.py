"""The Ai-Link A.O. Smith integration."""
import asyncio
import json
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS, UPDATE_INTERVAL
from .api import AOSmithAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ai-Link A.O. Smith from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    _LOGGER.info("Setting up A.O. Smith integration with user_id: %s", entry.data["user_id"])
    
    try:
        # Initialize API
        api = AOSmithAPI(
            access_token=entry.data["access_token"],
            user_id=entry.data["user_id"],
            family_id=entry.data["family_id"],
            cookie=entry.data.get("cookie"),
            mobile=entry.data.get("mobile")
        )
        
        await api.async_authenticate()
        
        # Create coordinator
        coordinator = AOSmithDataUpdateCoordinator(hass, api)
        # Attach the config entry to coordinator so entities can reference it
        coordinator.config_entry = entry
        
        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()
        
        # Store coordinator
        hass.data[DOMAIN][entry.entry_id] = coordinator
        
        # 记录详细的设备信息用于调试
        for device_id, device_data in coordinator.data.items():
            _LOGGER.info("=== Device %s Information ===", device_id)
            _LOGGER.info("Device Name: %s", device_data.get("productName"))
            _LOGGER.info("Device Model: %s", device_data.get("productModel"))
            _LOGGER.info("Device Category: %s", device_data.get("deviceCategory"))
            _LOGGER.info("Available keys: %s", list(device_data.keys()))
            
            # 检查状态信息
            if "statusInfo" in device_data:
                _LOGGER.debug("Device has statusInfo")
                try:
                    status_data = json.loads(device_data["statusInfo"])
                    _LOGGER.debug("Status info keys: %s", list(status_data.keys()))
                    if "events" in status_data:
                        for event in status_data["events"]:
                            if event.get("identifier") == "post":
                                output_data = event.get("outputData", {})
                                _LOGGER.debug("Output data keys: %s", list(output_data.keys()))
                                break
                except Exception as e:
                    _LOGGER.debug("Error parsing status info: %s", e)
            else:
                _LOGGER.warning("Device missing statusInfo")
        
        # Set up platforms
        _LOGGER.info("Setting up platforms: %s", PLATFORMS)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        _LOGGER.info("A.O. Smith integration setup completed successfully with %d devices", 
                    len(coordinator.data))
        return True
        
    except Exception as err:
        _LOGGER.error("Error setting up A.O. Smith integration: %s", err, exc_info=True)
        raise ConfigEntryNotReady(f"Failed to setup integration: {err}") from err

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.api.close()
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("A.O. Smith integration unloaded successfully")
    
    return unload_ok

class AOSmithDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching A.O. Smith data."""
    
    def __init__(self, hass, api):
        """Initialize global data updater."""
        self.api = api
        self.data = {}
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
    
    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            _LOGGER.debug("Updating A.O. Smith data")
            
            if not self.api.is_authenticated:
                _LOGGER.warning("API not authenticated, re-authenticating")
                await self.api.async_authenticate()
            
            devices = await self.api.async_get_devices()
            
            data = {}
            for device in devices:
                device_id = device.get("deviceId")
                if device_id:
                    _LOGGER.debug("Processing device %s: %s", device_id, device.get("productName"))
                    
                    # Get device status with timeout
                    try:
                        status = await asyncio.wait_for(
                            self.api.async_get_device_status(device_id),
                            timeout=10.0
                        )
                        if status:
                            # Merge device info with status
                            merged_data = {**device, **status}
                            data[device_id] = merged_data
                            _LOGGER.debug("Successfully updated status for device %s", device_id)
                        else:
                            # Use basic device info if status fetch failed
                            data[device_id] = device
                            _LOGGER.warning("Failed to get status for device %s, using basic info", device_id)
                    except asyncio.TimeoutError:
                        data[device_id] = device
                        _LOGGER.warning("Timeout getting status for device %s", device_id)
                    except Exception as status_err:
                        data[device_id] = device
                        _LOGGER.warning("Error getting status for device %s: %s", device_id, status_err)
            
            _LOGGER.debug("Updated data for %d devices", len(data))
            return data
            
        except asyncio.TimeoutError:
            error_msg = "Timeout updating A.O. Smith data"
            _LOGGER.error(error_msg)
            raise UpdateFailed(error_msg)
        except Exception as err:
            error_msg = f"Error updating A.O. Smith data: {err}"
            _LOGGER.error(error_msg)
            raise UpdateFailed(error_msg)