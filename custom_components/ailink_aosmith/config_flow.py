"""Config flow for Ai-Link A.O. Smith."""
import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_USER_ID, CONF_FAMILY_ID, CONF_ACCESS_TOKEN, CONF_MOBILE, CONF_COOKIE

_LOGGER = logging.getLogger(__name__)

class AOSmithConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ai-Link A.O. Smith."""
    
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            try:
                # Validate the provided credentials by trying to get devices
                devices = await self._get_devices(
                    user_input[CONF_ACCESS_TOKEN],
                    user_input[CONF_USER_ID],
                    user_input[CONF_FAMILY_ID],
                    user_input.get(CONF_COOKIE),
                    user_input.get(CONF_MOBILE)
                )
                
                if devices:
                    device_names = [f"{device.get('productName', 'Water Heater')} ({device.get('productModel', 'Unknown')})" 
                                  for device in devices]
                    
                    _LOGGER.info("Successfully authenticated, found %d devices: %s", 
                                len(devices), ", ".join(device_names))
                    
                    return self.async_create_entry(
                        title=f"Ai-Link A.O. Smith - {len(devices)} devices",
                        data=user_input
                    )
                else:
                    errors["base"] = "no_devices"
                    
            except Exception as e:
                _LOGGER.error("Authentication failed: %s", e)
                errors["base"] = "auth_error"
        
        data_schema = vol.Schema({
            vol.Required(CONF_ACCESS_TOKEN): str,
            vol.Required(CONF_USER_ID): str,
            vol.Required(CONF_FAMILY_ID): str,
            vol.Optional(CONF_COOKIE): str,
            vol.Optional(CONF_MOBILE): str,
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "access_token": "通常为: Bearer xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "cookie": "通常为: cna=xxxxxxx"
            }
        )
    
    async def _get_devices(self, access_token: str, user_id: str, family_id: str, cookie: str = None, mobile: str = None) -> list:
        """Get list of devices."""
        from .api import AOSmithAPI
        
        api = None
        try:
            api = AOSmithAPI(access_token, user_id, family_id, cookie, mobile)
            await api.async_authenticate()
            devices = await api.async_get_devices()
            return devices
        except Exception as e:
            _LOGGER.error("Failed to get devices: %s", e)
            raise
        finally:
            if api:
                await api.close()