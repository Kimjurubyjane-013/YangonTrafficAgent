from collections.abc import Mapping
import re
from typing import Any

from algorithms.graph import LOCATION_COORDS
from algorithms.vehicle import VEHICLE_SPEED
from app.models import RouteRequest, ValidationError

ALLOWED_CONDITIONS = {"time_band", "traffic_scenario", "weather", "incident", "closed_road", "scenario_type", "affected_road"}
CONDITION_VALUES = {
    "time_band": {"peak", "off_peak"},
    "traffic_scenario": {"current", "peak", "off_peak"},
    "weather": {"clear", "rain", "storm"},
    "incident": {"none", "minor", "major"},
    "scenario_type": {"none", "accident", "heavy_rain", "rush_hour", "road_closed", "major_event"},
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
    elif not isinstance(conditions, Mapping):
        return None, ValidationError("invalid_conditions", "Conditions must be an object.")
    else:
        normalized = {key: conditions[key] for key in ALLOWED_CONDITIONS if key in conditions}
        for key, allowed in CONDITION_VALUES.items():
            if key in normalized and normalized[key] not in allowed:
                return None, ValidationError("invalid_conditions", f"Invalid {key.replace('_', ' ')} value.")
        for road_field in ("closed_road", "affected_road"):
            if road_field not in normalized:
                continue
            closed_road = normalized[road_field]
            if not isinstance(closed_road, str) or not ROAD_NAME_PATTERN.fullmatch(closed_road.strip()):
                return None, ValidationError(
                    "invalid_closed_road",
                    "Scenario road must be a valid English road name (2-80 characters).",
                )
            normalized[road_field] = closed_road.strip()
    return RouteRequest(vehicle, start, destination, normalized), None
