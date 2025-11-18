"""Config flow for Ai-Link A.O. Smith."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_USER_ID, CONF_FAMILY_ID, CONF_ACCESS_TOKEN, CONF_DEVICE_ID, CONF_MOBILE, CONF_COOKIE

class AOSmithConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ai-Link A.O. Smith."""
    
    VERSION = 1
    
    def __init__(self) -> None:
        """Initialize the config flow."""
        self._devices = None
        self._api = None
        
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Validate the provided credentials by trying to get devices
            self._devices = await self._get_devices(
                user_input[CONF_ACCESS_TOKEN],
                user_input[CONF_USER_ID],
                user_input[CONF_FAMILY_ID],
                user_input.get(CONF_COOKIE),
                user_input.get(CONF_MOBILE)
            )
            
            if self._devices:
                if len(self._devices) == 1:
                    # Auto-select if only one device
                    user_input[CONF_DEVICE_ID] = self._devices[0]["deviceId"]
                    return await self._async_create_entry(user_input)
                else:
                    # Show device selection
                    return await self.async_step_select_device(user_input)
            else:
                errors["base"] = "no_devices"
        
        data_schema = vol.Schema({
            vol.Required(CONF_ACCESS_TOKEN): str,
            vol.Required(CONF_USER_ID): str,
            vol.Required(CONF_FAMILY_ID): str,
            vol.Optional(CONF_COOKIE, default="cna=130fe055be754d199cb6efba84e9b020"): str,
            vol.Optional(CONF_MOBILE): str,
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "cookie_info": "通常为: cna=130fe055be754d199cb6efba84e9b020"
            }
        )
    
    async def async_step_select_device(self, user_input=None):
        """Let user select which device to add."""
        errors = {}
        
        if user_input is not None:
            # Get the full user_input from context
            context_user_input = self.context["user_input"]
            context_user_input[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID]
            return await self._async_create_entry(context_user_input)
        
        # Create device options
        device_options = {
            device["deviceId"]: f"{device.get('deviceName', 'Water Heater')} ({device.get('productModel', 'Unknown')})"
            for device in self._devices
        }
        
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(device_options),
            }),
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._devices))
            }
        )
    
    async def _async_create_entry(self, user_input):
        """Create the config entry."""
        # Find device name for title
        device_name = "Water Heater"
        if self._devices:
            for device in self._devices:
                if device["deviceId"] == user_input[CONF_DEVICE_ID]:
                    device_name = device.get("deviceName", "Water Heater")
                    break
        
        if self._api:
            await self._api.close()
        
        return self.async_create_entry(
            title=f"Ai-Link A.O. Smith - {device_name}",
            data=user_input
        )
    
    async def _get_devices(self, access_token: str, user_id: str, family_id: str, cookie: str = None, mobile: str = None) -> list:
        """Get list of devices."""
        from .api import AOSmithAPI
        
        try:
            self._api = AOSmithAPI(access_token, user_id, family_id, cookie, mobile)
            await self._api.async_authenticate()
            devices = await self._api.async_get_devices()
            return devices
        except Exception as e:
            _LOGGER.error("Failed to get devices: %s", e)
            return []