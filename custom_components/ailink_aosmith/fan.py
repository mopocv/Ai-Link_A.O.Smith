"""Support for A.O. Smith fan entities."""
from __future__ import annotations

import json
import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CRUISE_TIMER_MAX, CRUISE_TIMER_MIN, DEVICE_CATEGORY_WATER_HEATER, DOMAIN
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)


def _extract_output_data(device_data: dict) -> dict:
    """Parse outputData from device status info."""
    if not device_data:
        return {}
    raw = device_data.get("statusInfo")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw if isinstance(raw, dict) else {}
    events = parsed.get("events", []) if isinstance(parsed, dict) else []
    for event in events:
        if event.get("identifier") == "post":
            return event.get("outputData", {}) or {}
    return {}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fan entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            entities.append(AOSmithCruiseTimerFan(coordinator, device_id))

    _LOGGER.info("Setting up %d fan entities", len(entities))
    async_add_entities(entities, True)


class AOSmithCruiseTimerFan(AOSmithEntity, FanEntity):
    """Fan-style entity for cruise timer (零冷水循环时长)."""

    _attr_supported_features = FanEntityFeature.SET_SPEED

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id)

        translation = getattr(coordinator, "translation", {})
        fan_config = (
            translation.get("entity", {})
            .get("fan", {})
            .get("cruise_timer", {})
        )

        device_name = self.device_data.get("productName", "Water Heater")
        fan_name = fan_config.get("name", "Cruise Timer")

        self._attr_name = f"{device_name} {fan_name}"
        self._attr_unique_id = f"{device_id}_cruise_timer_fan"
        self._attr_icon = fan_config.get("icon")

    @property
    def percentage(self) -> int | None:
        """Return current cruise timer value as percentage."""
        cached_value = self.device_data.get("cruise_timer")
        if cached_value is not None:
            try:
                return int(float(cached_value))
            except (TypeError, ValueError):
                pass

        output = _extract_output_data(self.device_data)
        raw_value = (
            output.get("WaterCruiseTimer")
            or output.get("waterCruiseTimer")
            or output.get("cruiseTimer")
        )
        if raw_value is None:
            return None
        try:
            return int(float(raw_value))
        except (TypeError, ValueError):
            return None

    @property
    def is_on(self) -> bool:
        """Return if cruise mode is on."""
        output = _extract_output_data(self.device_data)
        return output.get("cruiseStatus") == "1"

    async def async_set_percentage(self, percentage: int) -> None:
        """Set cruise timer value."""
        minutes = max(CRUISE_TIMER_MIN, min(CRUISE_TIMER_MAX, int(percentage)))
        _LOGGER.info(
            "Setting cruise timer for %s to %s minutes",
            self.device_id,
            minutes,
        )

        self.device_data["cruise_timer"] = minutes
        self.async_write_ha_state()

        try:
            await self.coordinator.api.async_send_command(
                self.device_id,
                "WaterCruiseTimer",
                {"WaterCruiseTimer": str(minutes)},
            )
            _LOGGER.info("Cruise timer set command sent for %s", self.device_id)
        except Exception as err:
            _LOGGER.error(
                "Failed to set cruise timer for %s: %s",
                self.device_id,
                err,
            )
            self.device_data.pop("cruise_timer", None)
            self.async_write_ha_state()
