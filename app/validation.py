from collections.abc import Mapping
import re
from typing import Any

from algorithms.graph import LOCATION_COORDS
from algorithms.vehicle import VEHICLE_SPEED
from app.models import RouteRequest, ValidationError

CANONICAL_SCENARIOS = {
    "current": "current",
    "heavy_rain": "heavy_rain",
    "peak": "peak",
    "off_peak": "off_peak",
}

SCENARIO_ALIASES = {
    "normal": "current",
    "normal_conditions": "current",
    "rush_hour": "peak",
    "offpeak": "off_peak",
}

SCENARIO_NORMALIZATION_MAP = {**CANONICAL_SCENARIOS, **SCENARIO_ALIASES}


def normalize_scenario_value(value: Any) -> str | None:
    if value is None:
        return "current"
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return SCENARIO_NORMALIZATION_MAP.get(cleaned)


ALLOWED_CONDITIONS = {"time_band", "traffic_scenario", "weather", "incident", "scenario_type", "scenario", "affected_road", "closed_road"}
CONDITION_VALUES = {
    "time_band": {"peak", "off_peak"},
    "traffic_scenario": {"current", "heavy_rain", "peak", "off_peak"},
    "weather": {"clear", "rain", "storm"},
    "incident": {"none", "minor", "major"},
    "scenario_type": {"none", "current", "heavy_rain", "peak", "off_peak", "rush_hour"},
}
ROAD_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 .,'()&/-]{2,80}$")


def validate_route_request(vehicle: Any, start: Any, destination: Any, conditions: Any = None):
    if not all(isinstance(value, str) for value in (vehicle, start, destination)):
        return None, ValidationError("invalid_type", "Vehicle, start, and destination must be text values.")
    vehicle, start, destination = vehicle.strip(), start.strip(), destination.strip()
    if vehicle not in VEHICLE_SPEED:
        return None, ValidationError("unknown_vehicle", "Unknown vehicle type.")
    if start not in LOCATION_COORDS or destination not in LOCATION_COORDS:
        return None, ValidationError("unknown_location", "Unknown start or destination.")
    if start == destination:
        return None, ValidationError("same_location", "Start and destination must be different.")
    if conditions is None:
        normalized = {}
    elif isinstance(conditions, str):
        scenario_norm = normalize_scenario_value(conditions)
        if scenario_norm is None:
            return None, ValidationError("invalid_scenario", "Unknown scenario type.")
        normalized = {"traffic_scenario": scenario_norm}
    elif not isinstance(conditions, Mapping):
        return None, ValidationError("invalid_conditions", "Conditions must be an object.")
    else:
        normalized = {key: conditions[key] for key in ALLOWED_CONDITIONS if key in conditions}
        raw_scenario = normalized.get("traffic_scenario") if "traffic_scenario" in normalized else normalized.get("scenario")
        if raw_scenario is not None:
            norm_scen = normalize_scenario_value(raw_scenario)
            if norm_scen is None:
                return None, ValidationError("invalid_scenario", "Unknown scenario type.")
            normalized["traffic_scenario"] = norm_scen
            normalized.pop("scenario", None)

        if "scenario_type" in normalized:
            raw_st = normalized["scenario_type"]
            if raw_st in {"none", "", None}:
                normalized["scenario_type"] = "none"
            else:
                norm_st = normalize_scenario_value(raw_st)
                if norm_st is None:
                    return None, ValidationError("invalid_scenario", "Unknown scenario type.")
                normalized["scenario_type"] = norm_st
                if "traffic_scenario" not in normalized:
                    normalized["traffic_scenario"] = norm_st

        if "time_band" in normalized:
            tb = str(normalized["time_band"]).strip().lower()
            if tb in {"peak", "rush_hour"}:
                normalized["time_band"] = "peak"
            elif tb in {"off_peak", "offpeak"}:
                normalized["time_band"] = "off_peak"

        for key, allowed in CONDITION_VALUES.items():
            if key in normalized and normalized[key] not in allowed:
                return None, ValidationError("invalid_conditions", f"Invalid {key.replace('_', ' ')} value.")
    return RouteRequest(vehicle, start, destination, normalized), None
