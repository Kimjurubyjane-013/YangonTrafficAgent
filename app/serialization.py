from copy import deepcopy
from typing import Any

ROUTE_FIELDS = ("route", "display_route", "geometry", "road_names", "route_source", "distance", "time", "traffic", "segment_traffic", "eta_basis", "base_duration", "traffic_delay", "traffic_source", "traffic_data_available", "retrieved_at", "decision")


def _option(value: dict[str, Any]) -> dict[str, Any]:
    result = {key: deepcopy(value.get(key)) for key in ROUTE_FIELDS}
    result["route"] = result["route"] or []
    result["display_route"] = result["display_route"] or result["route"]
    result["geometry"] = result["geometry"] or []
    result["road_names"] = result["road_names"] or []
    result["segment_traffic"] = result["segment_traffic"] or []
    return result


def serialize_route_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("error"):
        message = str(result["error"])
        return {**result, "error": message, "error_details": result.get("error_details") or {"code": "routing_error", "message": message}}
    best = _option(result)
    response = {**result, **best}
    response["alternatives"] = [_option(item) for item in result.get("alternatives", [])]
    response["ok"] = True
    return response
