"""Base entity for A.O. Smith integration with dynamic mapping and multi-language support."""
import json
import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, BRAND

_LOGGER = logging.getLogger(__name__)


def extract_output_data(device_data: dict) -> dict:
    """Parse outputData from device status info."""
    if not device_data:
        return {}
    raw = device_data.get("statusInfo")
    if not raw:
        app_status = device_data.get("appDeviceStatusInfoEntity")
        if isinstance(app_status, dict):
            raw = app_status.get("statusInfo")
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    elif isinstance(raw, dict):
        parsed = raw
    else:
        return {}

    events = parsed.get("events")
    if isinstance(events, list):
        for event in events:
            if event.get("identifier") == "post":
                output = event.get("outputData")
                return output if isinstance(output, dict) else {}
    output = parsed.get("outputData")
    return output if isinstance(output, dict) else {}

class AOSmithEntity(CoordinatorEntity):
    """Base class for A.O. Smith entities."""

    def __init__(self, coordinator, device_id):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_id(self):
        """Return the device ID."""
        return self._device_id

    @property
    def device_data(self):
        """Return the device data from coordinator."""
        return self.coordinator.data.get(self._device_id, {})

    @property
    def device_info(self):
        """Return device information for HomeKit compatibility."""
        device_model = self.device_data.get("productModel", "Unknown Model")
        product_name = self.device_data.get("productName", "A.O. Smith Device")

        if device_model == "Unknown Model":
            device_model = self._get_device_model_from_other_sources()

        device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": product_name,
            "manufacturer": BRAND,
            "model": device_model,
            "sw_version": self._get_firmware_version(),
        }

        _LOGGER.debug(
            "Device info for %s: model=%s, name=%s", 
            self._device_id, device_model, product_name
        )
        return device_info

    def _get_device_model_from_other_sources(self):
        """Get device model from other possible sources."""
        status_model = self._get_model_from_status()
        if status_model:
            return status_model

        product_name = self.device_data.get("productName", "")
        if "燃气热水器" in product_name:
            return "燃气热水器"

        _LOGGER.warning(
            "Could not determine model for device %s. Available keys: %s", 
            self._device_id, list(self.device_data.keys())
        )
        return "Unknown Model"

    def _get_model_from_status(self):
        """Extract model from status info."""
        status_info = self._get_status_info()
        if not status_info:
            return None
        try:
            data = json.loads(status_info)
            profile = data.get("profile", {})
            return profile.get("deviceType") or profile.get("deviceModel")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error parsing status info for model: %s", e)
            return None

    def _get_firmware_version(self):
        """Extract firmware version from device data."""
        status_info = self._get_status_info()
        if not status_info:
            return None
        try:
            data = json.loads(status_info)
            profile = data.get("profile", {})
            firmware_list = profile.get("deviceFirmware", [])
            for firmware in firmware_list:
                if firmware.get("type") == "3":
                    return firmware.get("version")
            if firmware_list:
                return firmware_list[0].get("version")
            return None
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _LOGGER.debug("Error parsing firmware version: %s", e)
            return None

    def _get_status_info(self):
        """Return status info from known device data locations."""
        status_info = self.device_data.get("statusInfo")
        if status_info:
            return status_info
        app_status = self.device_data.get("appDeviceStatusInfoEntity")
        if isinstance(app_status, dict):
            return app_status.get("statusInfo")
        return None

    def _get_output_data(self) -> dict:
        """Return parsed output data from status info."""
        return extract_output_data(self.device_data)

    @property
    def translation(self):
        """Return current language translation mapping."""
        return getattr(self.coordinator, "translation", {})

    def get_unit_of_measurement(self, unit_key: str):
        """Get translated unit from JSON mapping."""
        return self.translation.get(unit_key, unit_key)

    def get_icon(self, sensor_key: str):
        """Get icon from JSON mapping."""
        sensor_info = self.translation.get("SENSOR_TYPES", {}).get(sensor_key)
        if sensor_info:
            return sensor_info[2]  # mdi icon
        return "mdi:information-outline"

    def get_translation(self, field_key: str):
        """Get translated sensor name from JSON mapping."""
        return self.translation.get("entity", {}).get("sensor", {}).get(field_key, field_key)

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        return getattr(self, "_attr_icon", None)
