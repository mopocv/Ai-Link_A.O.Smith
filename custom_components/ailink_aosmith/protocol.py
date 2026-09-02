"""Validated gas-water-heater protocol, based on the official GasWater UI."""
import json
import math

DURATION_PRESETS = (1, 5, 10, 15, 30, 60, 99)


def extract_output_data(device_data: dict) -> dict:
    """Prefer the detailed status over the older homepage snapshot."""
    nested = device_data.get("appDeviceStatusInfoEntity")
    raw = nested.get("statusInfo") if isinstance(nested, dict) else None
    raw = raw or device_data.get("statusInfo")
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    events = parsed.get("events", [])
    if isinstance(events, list):
        for event in events:
            if isinstance(event, dict) and event.get("identifier") == "post":
                output = event.get("outputData")
                return output if isinstance(output, dict) else {}
    output = parsed.get("outputData")
    return output if isinstance(output, dict) else {}


def numeric(output: dict, *keys: str) -> float | None:
    for key in keys:
        try:
            value = float(output[key])
            if math.isfinite(value):
                return value
        except (KeyError, ValueError, TypeError):
            pass
    return None


def flag(output: dict, *keys: str) -> bool | None:
    value = numeric(output, *keys)
    return None if value is None else value == 1


def validate_integer(value: float, minimum: int, maximum: int) -> int:
    value = float(value)
    if not math.isfinite(value) or not value.is_integer() or not minimum <= value <= maximum:
        raise ValueError(f"Value must be an integer between {minimum} and {maximum}")
    return int(value)


def temperature_limits(output: dict) -> tuple[float, float, float]:
    minimum = 37 if flag(output, "minTemp35") is False else 35
    step = 0.5 if flag(output, "halfTempSetFlag") else 1
    return minimum, 70, step


def temperature_command(output: dict, value: float) -> tuple[str, dict]:
    minimum, maximum, step = temperature_limits(output)
    value = float(value)
    actual_step = 1 if value >= 50 else step
    if not math.isfinite(value) or not minimum <= value <= maximum or value % actual_step:
        raise ValueError(f"Temperature must be {minimum}–{maximum} °C in supported steps")
    current = numeric(output, "waterTemp", "setTemp")
    in_use = flag(output, "haveWater") or flag(output, "haveWaterUp")
    if current is None:
        raise ValueError("Current target temperature is unavailable")
    if in_use and value > current and (current >= 50 or value > 50):
        raise ValueError("Cannot raise the water temperature above 50 °C while hot water is in use")
    if flag(output, "halfTempSetFlag"):
        return "SetHalfTempValue", {"waterTemp": str(int(value * 2))}
    return "WaterTempSet", {"waterTemp": str(int(value))}
