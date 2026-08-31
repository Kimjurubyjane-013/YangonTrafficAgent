from copy import deepcopy
from typing import Any

ROUTE_FIELDS = ("route_id", "route_type", "route", "display_route", "geometry", "traffic_geometry", "road_names", "major_roads", "route_source", "distance", "distance_km", "time", "traffic_adjusted_eta", "traffic_adjusted_eta_seconds", "free_flow_eta", "free_flow_eta_seconds", "traffic_delay", "overall_traffic", "traffic", "segment_traffic", "segment_sources", "eta_basis", "base_duration", "traffic_time", "route_duration_seconds", "base_duration_seconds", "traffic_delay_seconds", "provider", "provider_timestamp", "traffic_source", "traffic_source_label", "provider_coverage", "provider_coverage_percent", "inferred_coverage_percent", "unknown_coverage_percent", "provider_notice", "traffic_data_available", "traffic_model_available", "traffic_snapshot_id", "traffic_scenario", "scenario_explanation", "traffic_score", "route_cost", "recommendation_reason", "comparison_to_recommended", "segment_diagnostics", "direction_summary", "retrieved_at", "decision")


def _option(value: dict[str, Any]) -> dict[str, Any]:
    result = {key: deepcopy(value.get(key)) for key in ROUTE_FIELDS}
    result["route"] = result["route"] or []
    result["display_route"] = result["display_route"] or result["route"]
    result["geometry"] = result["geometry"] or []
    result["road_names"] = result["road_names"] or []
    result["segment_traffic"] = result["segment_traffic"] or []
    result["segment_sources"] = result["segment_sources"] or []
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
