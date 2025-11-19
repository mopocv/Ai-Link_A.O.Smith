"""Base entity for A.O. Smith integration."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, BRAND

class AOSmithEntity(CoordinatorEntity):
    """Base class for A.O. Smith entities."""
    
    def __init__(self, coordinator, device_id):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
    
    @property
    def device_data(self):
        """Return the device data from coordinator."""
        return self.coordinator.data.get(self._device_id, {})
    
    @property
    def device_info(self):
        """Return device information for HomeKit compatibility."""
        device_model = self.device_data.get("deviceModel", "Unknown Model")
        product_name = self.device_data.get("productName", "A.O. Smith Device")
        
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": product_name,
            "manufacturer": BRAND,
            "model": device_model,
            "sw_version": self._get_firmware_version(),
            # 设备通过 hub（配置条目）连接
            "via_device": (DOMAIN, self.coordinator.config_entry.entry_id),
        }
    
    def _get_firmware_version(self):
        """Extract firmware version from device data."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
            
        try:
            import json
            data = json.loads(status_info)
            profile = data.get("profile", {})
            firmware_list = profile.get("deviceFirmware", [])
            
            for firmware in firmware_list:
                if firmware.get("type") == "3":  # Main firmware
                    return firmware.get("version")
            
            return None
        except:
            return None