"""Helpers for loading translations and language configuration."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_LANGUAGE, DEFAULT_LANGUAGE, DOMAIN

_LOGGER = logging.getLogger(__name__)
TRANSLATIONS_DIRNAME = "translations"


def _translations_dir(hass: HomeAssistant) -> str:
    """Return the path to translations JSON."""
    try:
        path = hass.config.path("custom_components", DOMAIN, TRANSLATIONS_DIRNAME)
        if os.path.isdir(path):
            return path
    except Exception:
        _LOGGER.debug("Failed to resolve translations path from hass config.")
    return os.path.join(os.path.dirname(__file__), TRANSLATIONS_DIRNAME)


def get_language(hass: HomeAssistant, entry: ConfigEntry | None = None) -> str:
    """Determine language from options or Home Assistant config."""
    if entry:
        option_lang = entry.options.get(CONF_LANGUAGE)
        if option_lang and option_lang != "auto":
            return option_lang
    return hass.config.language or DEFAULT_LANGUAGE


def _load_json(translation_file: str) -> dict[str, Any]:
    """Load translation JSON from disk."""
    with open(translation_file, "r", encoding="utf-8") as handle:
        return json.load(handle)


async def async_load_translation(
    hass: HomeAssistant,
    entry: ConfigEntry | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Load translation configuration."""
    translations_dir = _translations_dir(hass)
    selected_language = language or get_language(hass, entry)
    translation_file = os.path.join(translations_dir, f"{selected_language}.json")

    if not os.path.exists(translation_file):
        _LOGGER.debug(
            "Translation file for %s not found at %s, falling back to %s.json",
            selected_language,
            translation_file,
            DEFAULT_LANGUAGE,
        )
        translation_file = os.path.join(translations_dir, f"{DEFAULT_LANGUAGE}.json")

    if not os.path.exists(translation_file):
        _LOGGER.warning("Translation file not found: %s", translation_file)
        return {}

    try:
        return await hass.async_add_executor_job(_load_json, translation_file)
    except Exception as err:
        _LOGGER.exception("Failed to load translation from %s: %s", translation_file, err)
        return {}
