"""The Ai-Link A.O. Smith integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, PLATFORMS, UPDATE_INTERVAL
from .api import AOSmithAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ai-Link A.O. Smith from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
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
    
    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # 记录详细的设备信息用于调试
    for device_id, device_data in coordinator.data.items():
        _LOGGER.info("=== Device %s Information ===", device_id)
        _LOGGER.info("Available keys: %s", list(device_data.keys()))
        _LOGGER.info("productModel: %s", device_data.get("productModel"))
        _LOGGER.info("productName: %s", device_data.get("productName"))
        _LOGGER.info("deviceCategory: %s", device_data.get("deviceCategory"))
        
        # 检查是否有 statusInfo
        if "statusInfo" in device_data:
            _LOGGER.info("Device has statusInfo")
        else:
            _LOGGER.warning("Device missing statusInfo")
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("A.O. Smith integration setup completed successfully")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.api.close()
        hass.data[DOMAIN].pop(entry.entry_id)
    
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
            devices = await self.api.async_get_devices()
            
            data = {}
            for device in devices:
                device_id = device.get("deviceId")
                if device_id:
                    # 记录原始设备数据用于调试
                    _LOGGER.debug("Raw device data for %s - productModel: %s, productName: %s", 
                                 device_id, 
                                 device.get("productModel"), 
                                 device.get("productName"))
                    
                    # Get device status
                    status = await self.api.async_get_device_status(device_id)
                    if status:
                        # 记录状态数据中的信息
                        if "productModel" in status:
                            _LOGGER.debug("Status data contains productModel: %s", status.get("productModel"))
                        
                        device.update(status)
                        _LOGGER.debug("Merged device data for %s", device_id)
                    
                    data[device_id] = device
            
            _LOGGER.debug("Updated data for %d devices", len(data))
            return data
        except Exception as err:
            _LOGGER.error("Error updating A.O. Smith data: %s", err)
            raise