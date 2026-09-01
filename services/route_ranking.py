"""Practical traffic-avoidance ranking with explicit lower-is-better semantics."""
from __future__ import annotations

from collections.abc import Mapping


ETA_WEIGHT = 1.0
DISTANCE_WEIGHT = 0.02
MODERATE_EXPOSURE_COST = 1.2
HEAVY_EXPOSURE_COST = 4.0
CONGESTION_POLICY_WEIGHT = 0.10
MAX_CONGESTION_POLICY_COST = 1.5
DETOUR_POLICY_WEIGHT = 0.5
HEAVY_SEGMENT_WEIGHT = 0.12
CRITICAL_SEGMENT_WEIGHT = 0.35
DELAY_EXPOSURE_WEIGHT = 0.08
TRAFFIC_IMPACT_WEIGHT = 0.002
VEHICLE_SUITABILITY_WEIGHT = 0.20
PREFERENCE_WEIGHT = 0.03
MAX_DELAY_EXPOSURE_COST = 0.5
MAX_TRAFFIC_IMPACT_COST = 0.5
MAX_PREFERENCE_BENEFIT = 0.1
EMERGENCY_VEHICLES = frozenset({"ambulance", "fire_truck", "police"})
MEANINGFUL_SCORE_ADVANTAGE = 10.0
EPSILON = 1e-9


def candidate_metrics(candidate: Mapping) -> dict:
    segment_levels = [str(level).strip().lower() for level in candidate.get("segment_traffic", ())]
    if not segment_levels:
        segment_levels = [str(candidate.get("traffic", "moderate")).strip().lower()]
    heavy_segments = int(candidate.get("heavy_segments", segment_levels.count("heavy")))
    moderate_segments = segment_levels.count("moderate")
    segment_count = max(1, len(segment_levels))
    critical_segments = int(candidate.get("critical_segments", 0))
    delay = max(0.0, float(candidate.get("traffic_delay") or 0.0))
    impact = max(0.0, float(candidate.get("cumulative_traffic_impact") or 0.0))
    pressure = max(0.0, float(candidate.get("average_congestion_pressure") or 0.0))
    score = max(0.0, float(candidate.get("traffic_score") or 0.0))
    return {
        "eta_minutes": max(0.0, float(candidate.get("time") or 0.0)),
        "distance_km": max(0.0, float(candidate.get("distance") or 0.0)),
        "heavy_segments": heavy_segments,
        "moderate_segments": moderate_segments,
        "segment_count": segment_count,
        "critical_segments": critical_segments,
        "traffic_delay_minutes": delay,
        "cumulative_traffic_impact": impact,
        "average_congestion_pressure": pressure,
        "average_traffic_score": score,
        "worst_traffic_level": str(candidate.get("traffic", "Moderate")),
    }


def has_meaningful_traffic_advantage(route_a: Mapping, route_b: Mapping) -> bool:
    """Return whether A has a material congestion/safety advantage over B."""
    a, b = candidate_metrics(route_a), candidate_metrics(route_b)
    if a["critical_segments"] < b["critical_segments"]:
        return True
    severity = {"light": 0, "moderate": 1, "heavy": 2}
    fewer_heavy = a["heavy_segments"] < b["heavy_segments"]
    materially_lower_score = a["average_traffic_score"] + MEANINGFUL_SCORE_ADVANTAGE <= b["average_traffic_score"]
    lower_worst_level = severity.get(a["worst_traffic_level"].lower(), 1) < severity.get(b["worst_traffic_level"].lower(), 1)
    avoids_multiple_heavy_segments = b["heavy_segments"] - a["heavy_segments"] >= 2
    return fewer_heavy and (materially_lower_score or lower_worst_level or avoids_multiple_heavy_segments)


def is_route_dominated(route_a: Mapping, route_b: Mapping) -> bool:
    """A is dominated when B is both faster and shorter without losing safety."""
    a, b = candidate_metrics(route_a), candidate_metrics(route_b)
    return (
        a["eta_minutes"] > b["eta_minutes"] + EPSILON
        and a["distance_km"] > b["distance_km"] + EPSILON
        and not has_meaningful_traffic_advantage(route_a, route_b)
    )


def route_cost(candidate: Mapping, penalties: Mapping[str, float], vehicle: str) -> tuple[float, dict]:
    """Calculate a lower-is-better cost without reapplying full traffic delay.

    ETA already contains provider or simulated traffic. Extra terms are small
    reliability/safety exposure adjustments, not a second travel-time model.
    """
    metrics = candidate_metrics(candidate)
    emergency = str(vehicle).lower() in EMERGENCY_VEHICLES
    heavy_weight = 0.05 if emergency else HEAVY_SEGMENT_WEIGHT
    critical_weight = 0.15 if emergency else CRITICAL_SEGMENT_WEIGHT
    components = {
        "eta_cost": metrics["eta_minutes"] * ETA_WEIGHT,
        "traffic_avoidance_cost": (
            metrics["heavy_segments"] * HEAVY_EXPOSURE_COST
            + metrics["moderate_segments"] * MODERATE_EXPOSURE_COST
        ) / metrics["segment_count"],
        "congestion_policy_cost": min(
            MAX_CONGESTION_POLICY_COST,
            max(0.0, float(penalties.get("congestion", 0.0))) * CONGESTION_POLICY_WEIGHT,
        ),
        "detour_policy_cost": max(0.0, float(penalties.get("detour", 0.0))) * DETOUR_POLICY_WEIGHT,
        "severe_congestion_cost": (
            metrics["heavy_segments"] * heavy_weight
            + metrics["critical_segments"] * critical_weight
        ),
        "delay_exposure_cost": min(MAX_DELAY_EXPOSURE_COST, metrics["traffic_delay_minutes"] * DELAY_EXPOSURE_WEIGHT),
        "traffic_impact_cost": min(MAX_TRAFFIC_IMPACT_COST, metrics["cumulative_traffic_impact"] * TRAFFIC_IMPACT_WEIGHT),
        "vehicle_suitability_cost": max(0.0, float(penalties.get("vehicle_restriction", 0.0))) * VEHICLE_SUITABILITY_WEIGHT,
        "distance_tiebreak_cost": metrics["distance_km"] * DISTANCE_WEIGHT,
        "preference_tiebreak": max(-MAX_PREFERENCE_BENEFIT, float(penalties.get("preference", 0.0)) * PREFERENCE_WEIGHT),
    }
    return round(sum(components.values()), 3), {key: round(value, 3) for key, value in components.items()}


def domination_map(routes: list[Mapping]) -> dict[str, list[str]]:
    result = {str(route.get("candidate_id")): [] for route in routes}
    for route_a in routes:
        a_id = str(route_a.get("candidate_id"))
        for route_b in routes:
            if route_a is route_b:
                continue
            if is_route_dominated(route_a, route_b):
                result[a_id].append(str(route_b.get("candidate_id")))
    return result
