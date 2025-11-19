"""Base entity for A.O. Smith integration."""
import json
import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, BRAND

_LOGGER = logging.getLogger(__name__)

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
        # 从设备数据获取型号
        device_model = self.device_data.get("productModel", "Unknown Model")
        product_name = self.device_data.get("productName", "A.O. Smith Device")
        
        # 如果 productModel 是 "Unknown Model"，尝试从其他来源获取
        if device_model == "Unknown Model":
            device_model = self._get_device_model_from_other_sources()
        
        device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": product_name,
            "manufacturer": BRAND,
            "model": device_model,
            "sw_version": self._get_firmware_version(),
            # 设备通过 hub（配置条目）连接
            "via_device": (DOMAIN, self.coordinator.config_entry.entry_id),
        }
        
        _LOGGER.debug("Device info for %s: model=%s, name=%s", 
                     self._device_id, device_model, product_name)
        return device_info
    
    def _get_device_model_from_other_sources(self):
        """Get device model from other possible sources."""
        # 1. 从 statusInfo 中的 profile.deviceType 获取
        status_model = self._get_model_from_status()
        if status_model:
            return status_model
        
        # 2. 从 productName 推断
        product_name = self.device_data.get("productName", "")
        if "燃气热水器" in product_name:
            return "燃气热水器"
        
        # 3. 记录调试信息
        _LOGGER.warning("Could not determine model for device %s. Available keys: %s", 
                       self._device_id, list(self.device_data.keys()))
        return "Unknown Model"
    
    def _get_model_from_status(self):
        """Extract model from status info."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
            
        try:
            data = json.loads(status_info)
            profile = data.get("profile", {})
            
            # 从 profile 获取设备型号
            device_type = profile.get("deviceType")
            if device_type:
                return device_type
            
            # 从设备数据获取
            device_model = profile.get("deviceModel")
            if device_model:
                return device_model
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error parsing status info for model: %s", e)
            
        return None
    
    def _get_firmware_version(self):
        """Extract firmware version from device data."""
        status_info = self.device_data.get("statusInfo")
        if not status_info:
            return None
            
        try:
            data = json.loads(status_info)
            profile = data.get("profile", {})
            firmware_list = profile.get("deviceFirmware", [])
            
            # 查找主固件版本
            for firmware in firmware_list:
                if firmware.get("type") == "3":  # Main firmware
                    return firmware.get("version")
            
            # 如果没有找到主固件，返回第一个可用的固件版本
            if firmware_list:
                return firmware_list[0].get("version")
            
            return None
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error parsing firmware version: %s", e)
            return None
    
    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        # 基类不设置图标，由具体实体类设置
        return None