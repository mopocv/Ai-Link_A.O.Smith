"""Support for A.O. Smith number entities."""
from __future__ import annotations

import json
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CRUISE_TIMER_MAX,
    CRUISE_TIMER_MIN,
    CRUISE_TIMER_STEP,
    DEVICE_CATEGORY_WATER_HEATER,
    DOMAIN,
)
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
    """Set up number entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            entities.append(AOSmithCruiseTimer(coordinator, device_id))

    _LOGGER.info("Setting up %d number entities", len(entities))
    async_add_entities(entities, True)


class AOSmithCruiseTimer(AOSmithEntity, NumberEntity):
    """Number entity for cruise timer (零冷水循环时长)."""

    _attr_native_min_value = CRUISE_TIMER_MIN
    _attr_native_max_value = CRUISE_TIMER_MAX
    _attr_native_step = CRUISE_TIMER_STEP
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id)

        translation = getattr(coordinator, "translation", {})
        number_config = (
            translation.get("entity", {})
            .get("number", {})
            .get("cruise_timer", {})
        )

        device_name = self.device_data.get("productName", "Water Heater")
        number_name = number_config.get("name", "Cruise Timer")

        self._attr_name = f"{device_name} {number_name}"
        self._attr_unique_id = f"{device_id}_cruise_timer"
        self._attr_icon = number_config.get("icon")

    @property
    def native_value(self) -> float | None:
        """Return current cruise timer value."""
        cached_value = self.device_data.get("cruise_timer")
        if cached_value is not None:
            try:
                return float(cached_value)
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
            return float(raw_value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set cruise timer value."""
        minutes = int(round(value))
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
