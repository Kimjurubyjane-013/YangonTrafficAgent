"""Backend-owned route comparison labels and confidence metadata."""

from __future__ import annotations

from collections.abc import Mapping


def _number(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence(route: Mapping) -> tuple[int, list[str]]:
    """Return a deterministic evidence-quality score, never observation certainty."""
    source = str(route.get("traffic_source_label") or "UNKNOWN").upper()
    provider = _number(route.get("provider_coverage_percent"))
    inferred = _number(route.get("inferred_coverage_percent"))
    unknown = _number(route.get("unknown_coverage_percent"), 100.0)
    geometry_points = len(route.get("geometry") or ())
    roads = len(route.get("road_names") or ())

    score = 35.0
    reasons = []
    if source == "HERE":
        score += 42.0
        reasons.append("Provider traffic covers the route")
    elif source == "MIXED":
        score += 24.0 + provider * 0.12
        reasons.append("Provider and inferred traffic are combined")
    elif source == "INFERRED":
        score += 25.0
        reasons.append("Deterministic road-context inference is available")
    else:
        reasons.append("Traffic evidence is limited")
    score += min(12.0, geometry_points / 25.0)
    score += min(8.0, roads * 2.0)
    score += min(8.0, inferred * 0.08)
    score -= min(35.0, unknown * 0.35)
    if geometry_points >= 20:
        reasons.append("Detailed provider road geometry is available")
    return round(max(20.0, min(96.0, score))), reasons


def annotate_route_comparison(routes: list[dict]) -> list[dict]:
    """Attach Route A/B/C and metric-derived characteristics in ranked order."""
    if not routes:
        return routes
    fastest = min(_number(route.get("time"), float("inf")) for route in routes)
    shortest = min(_number(route.get("distance"), float("inf")) for route in routes)
    congestion_keys = [(
        _number(route.get("traffic_score"), 100.0),
        int(route.get("heavy_segments") or 0),
        _number(route.get("traffic_delay"), float("inf")),
    ) for route in routes]
    least_congested = min(congestion_keys)

    for index, route in enumerate(routes):
        characteristics = []
        if abs(_number(route.get("time")) - fastest) <= 0.01:
            characteristics.append("FASTEST")
        if abs(_number(route.get("distance")) - shortest) <= 0.01:
            characteristics.append("SHORTEST")
            
        is_least = (congestion_keys[index] == least_congested)
        # Omit badge if all routes tie for least congested
        if is_least and len(routes) > 1:
            all_tied = all(key == least_congested for key in congestion_keys)
            if not all_tied:
                characteristics.append("LEAST_CONGESTED")
        elif is_least:
            characteristics.append("LEAST_CONGESTED")
            
        confidence, reasons = _confidence(route)
        route["route_label"] = f"Route {chr(65 + index)}"
        route["characteristics"] = characteristics
        route["confidence"] = confidence
        route["confidence_basis"] = reasons
    return routes
