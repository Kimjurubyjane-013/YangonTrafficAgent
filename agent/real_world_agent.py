"""Real-road route pipeline: provider geometry, hybrid traffic, symbolic ranking."""
import math
import re

from algorithms.graph import LOCATION_COORDS
from algorithms.vehicle import VEHICLE_SPEED, calculate_real_route_time
from app.runtime_config import traffic_mode, yangon_now
from services.here_traffic_service import fetch_traffic_aware_routes
from services.osrm_service import fetch_real_routes
from services.route_decision_engine import RouteDecisionEngine
from services.traffic_service import TRAFFIC_ENGINE

_ENGINE = None
_GENERIC_ROAD_WORDS = {"road", "street", "avenue", "lane", "highway", "route"}
_TRAFFIC_SCORE = {"Light": 25.0, "Moderate": 55.0, "Heavy": 85.0}
_VALID_TRAFFIC = frozenset(_TRAFFIC_SCORE)


def _format_minutes(value):
    seconds = round(abs(float(value)) * 60)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes} min {seconds} sec" if seconds else f"{minutes} min"


def _recommendation_reason(best, alternatives):
    best_id = str(best.get("candidate_id"))
    dominated = [
        str(item.get("candidate_id")) for item in alternatives
        if best_id in item.get("decision", {}).get("dominated_by", ())
    ]
    if not alternatives:
        return {
            "recommended_route_id": best_id, "primary_reason": "only_eligible_route",
            "eta_advantage_minutes": None, "distance_difference_km": None,
            "heavy_segment_difference": None, "delay_advantage_minutes": None,
            "dominated_alternatives": dominated,
            "explanation": "This is the only eligible real-road route returned for the journey.",
        }
    alternative = alternatives[0]
    eta_advantage = round(float(alternative["time"]) - float(best["time"]), 2)
    distance_difference = round(float(best["distance"]) - float(alternative["distance"]), 2)
    best_heavy = int(best.get("heavy_segments", best.get("segment_traffic", []).count("Heavy")))
    alt_heavy = int(alternative.get("heavy_segments", alternative.get("segment_traffic", []).count("Heavy")))
    heavy_difference = best_heavy - alt_heavy
    delay_advantage = round(float(alternative.get("traffic_delay") or 0) - float(best.get("traffic_delay") or 0), 2)
    if eta_advantage > 0:
        primary = "lowest_traffic_adjusted_eta"
    elif heavy_difference < 0:
        primary = "lower_severe_congestion"
    else:
        primary = "lower_route_cost"
    comparisons = []
    if abs(eta_advantage) > 0.01:
        comparisons.append(f"{_format_minutes(eta_advantage)} {'faster' if eta_advantage > 0 else 'slower'}")
    if abs(distance_difference) > 0.01:
        comparisons.append(f"{abs(distance_difference):.2f} km {'shorter' if distance_difference < 0 else 'longer'}")
    if comparisons:
        explanation = f"The recommended route is {' and '.join(comparisons)} than Alternative 1."
    else:
        explanation = "The recommended route has the lowest traffic-aware route cost among equivalent options."
    if heavy_difference < 0:
        explanation += f" It also contains {abs(heavy_difference)} fewer Heavy traffic segment(s)."
    return {
        "recommended_route_id": best_id, "primary_reason": primary,
        "eta_advantage_minutes": eta_advantage,
        "distance_difference_km": distance_difference,
        "heavy_segment_difference": heavy_difference,
        "delay_advantage_minutes": delay_advantage,
        "dominated_alternatives": dominated, "explanation": explanation,
    }


def _road_key(value):
    text = str(value or "").casefold()
    text = re.sub(r"\brd\b", "road", text)
    text = re.sub(r"\bst\b", "street", text)
    text = re.sub(r"\bave\b", "avenue", text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _road_matches(closed_road, road_name):
    requested = _road_key(closed_road)
    actual = _road_key(road_name)
    if not requested or not actual or requested in _GENERIC_ROAD_WORDS:
        return False
    return requested == actual or requested in actual or actual in requested


def _engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RouteDecisionEngine()
    return _ENGINE


def _real_route_provider(start_coord, destination_coord, alternatives=3):
    """Prefer HERE traffic, then retain honest real-road routing via OSRM."""
    try:
        return fetch_traffic_aware_routes(
            start_coord, destination_coord, alternatives=alternatives
        )
    except Exception:
        return fetch_real_routes(
            start_coord, destination_coord, alternatives=alternatives
        )


def _time_band(conditions):
    if conditions.get("time_band") in {"peak", "off_peak"}:
        return conditions["time_band"]
    hour = yangon_now().hour
    return "peak" if hour in {7,8,9,16,17,18,19} else "off_peak"


def _polyline_length(points):
    total = 0.0
    points = points or ()
    for first, second in zip(points, points[1:]):
        lat1, lon1 = map(math.radians, first[:2])
        lat2, lon2 = map(math.radians, second[:2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        total += 6371.0 * 2 * math.asin(min(1.0, math.sqrt(value)))
    return total


def _coverage_from_sources(sources):
    total = len(sources)
    if not total:
        return 0.0, 0.0, 100.0
    provider = round(sources.count("HERE") / total * 100, 1)
    inferred = round(sources.count("INFERRED") / total * 100, 1)
    return provider, inferred, round(max(0.0, 100.0 - provider - inferred), 1)


def _weighted_level(levels, traffic_geometry=None):
    valid = [(index, level) for index, level in enumerate(levels) if level in _VALID_TRAFFIC]
    if not valid:
        return "Unknown", None
    weights = []
    for index, _level in valid:
        geometry = traffic_geometry[index] if traffic_geometry and index < len(traffic_geometry) else ()
        weights.append(max(0.001, _polyline_length(geometry)))
    score = sum(_TRAFFIC_SCORE[level] * weight for (_, level), weight in zip(valid, weights)) / sum(weights)
    level = "Light" if score <= 35 else "Moderate" if score <= 70 else "Heavy"
    return level, round(score, 1)


def _effective_route_traffic(route, model_state):
    """Merge provider sections with inference and retain honest provenance."""
    provider_levels = list(route.get("segment_traffic") or ())
    provider_sources = [str(value).upper() for value in (route.get("segment_sources") or ())]
    complete_provider_response = bool(route.get("traffic_data_available") and not provider_sources)
    if complete_provider_response:
        provider_sources = ["HERE"] * max(1, len(provider_levels))
    inferred_levels = list(model_state.get("segment_traffic") or ())
    if provider_sources:
        size = max(len(provider_levels), len(provider_sources), 1)
    else:
        size = max(len(inferred_levels), 1)
    levels, sources = [], []
    for index in range(size):
        provider_level = provider_levels[index] if index < len(provider_levels) else None
        provider_source = provider_sources[index] if index < len(provider_sources) else "UNKNOWN"
        inferred_level = inferred_levels[index % len(inferred_levels)] if inferred_levels else None
        if provider_source == "HERE" and provider_level in _VALID_TRAFFIC:
            levels.append(provider_level); sources.append("HERE")
        elif inferred_level in _VALID_TRAFFIC:
            levels.append(inferred_level); sources.append("INFERRED")
        else:
            levels.append("Unknown"); sources.append("UNKNOWN")
    level, score = _weighted_level(levels, route.get("traffic_geometry"))
    provider, inferred, unknown = _coverage_from_sources(sources)
    label = "HERE" if provider == 100 else "INFERRED" if inferred == 100 else "UNKNOWN" if unknown == 100 else "MIXED"
    description = {"HERE": "HERE Real-Time Traffic", "INFERRED": "Inferred Traffic Model", "MIXED": "Mixed Traffic Data", "UNKNOWN": "Traffic Data Unavailable"}[label]
    return {"traffic": level, "traffic_score": score, "segment_traffic": levels,
            "segment_sources": sources, "traffic_source_label": label,
            "traffic_source": description, "provider_coverage_percent": provider,
            "inferred_coverage_percent": inferred, "unknown_coverage_percent": unknown}


def run_real_world_agent(start, destination, vehicle, conditions=None, route_provider=None, decision_engine=None,
                         traffic_engine=None, traffic_snapshot=None):
    conditions = dict(conditions or {})
    if not all(isinstance(value, str) for value in (start, destination, vehicle)):
        return {"error": "Start, destination, and vehicle must be text values."}
    if start == destination:
        return {"error": "Start and destination must be different."}
    if start not in LOCATION_COORDS or destination not in LOCATION_COORDS:
        return {"error": "Unknown location."}
    if vehicle not in VEHICLE_SPEED:
        return {"error": "Unknown vehicle type."}
    try:
        provider = route_provider or _real_route_provider
        routes = provider(LOCATION_COORDS[start], LOCATION_COORDS[destination], alternatives=3)
    except Exception as exc:
        return {"error": str(exc), "routing_mode": "real-world-only"}

    conditions["time_band"] = _time_band(conditions)
    conditions.setdefault("weather", "clear")
    conditions.setdefault("incident", "none")
    mode = traffic_mode()
    traffic_engine = traffic_engine or TRAFFIC_ENGINE
    # Always obtain inferred traffic snapshot — used as fallback for segments
    # without provider coverage, regardless of traffic mode setting.
    if traffic_snapshot is None:
        traffic_snapshot = traffic_engine.get_snapshot()
    candidates = []
    closure_rejections = []
    closed_road = conditions.get("closed_road", "").strip()
    for route in routes:
        matched_names = [name for name in route["road_names"] if _road_matches(closed_road, name)]
        if matched_names:
            closure_rejections.append({
                "candidate_id": route["provider_id"],
                "matched_road_names": matched_names,
                "reason": f"Route uses closed road: {matched_names[0]}",
            })
            continue
        road_label = route["road_names"][0] if route["road_names"] else "Mapped road route"
        road_summary = route["road_names"]
        has_real_traffic = bool(route.get("traffic_data_available"))

        # Always compute inferred model state — used as segment fallback even
        # when HERE provides the route-level traffic.
        model_state = traffic_engine.route_state(
            start, destination, route.get("road_names", ()), traffic_snapshot
        )

        effective = _effective_route_traffic(route, model_state)
        level = effective["traffic"]
        segment_traffic = effective["segment_traffic"]
        traffic_source_label = effective["traffic_source_label"]
        traffic_source_full = effective["traffic_source"]
        provider_notice = None if traffic_source_label == "HERE" else (
            "Some traffic sections use inferred estimates." if traffic_source_label == "MIXED"
            else "HERE traffic is unavailable; traffic is estimated from the inferred traffic model."
        )
        eta_basis = ("HERE traffic-aware duration adjusted for the selected vehicle" if traffic_source_label == "HERE"
                     else "Road duration adjusted by effective segment traffic and vehicle type")

        model_segments = []
        if has_real_traffic:
            model_segments.append({"index":0,"name":road_label,"road_class":"arterial",
                "traffic":str(level).lower(),"preferred":False,"one_way_ok":True})
        else:
            for index, road_id in enumerate(model_state.get("road_ids", [])):
                road = traffic_engine.repository.by_id.get(road_id)
                state = traffic_snapshot.roads.get(road_id)
                if road and state:
                    model_segments.append({
                        "index": index, "name": road.road_name, "road_class": road.road_type,
                        "traffic": state.traffic_level.lower(), "preferred": road.preferred,
                        "one_way_ok": road.bidirectional,
                    })
        if not model_segments:
            model_segments = [{"index":0,"name":road_label,"road_class":"arterial",
                "traffic":str(level).lower() if level in {"Light", "Moderate", "Heavy"} else "light",
                "preferred":False,"one_way_ok":True}]
        candidates.append({
            "candidate_id": route["provider_id"], "route": [start, destination],
            # Provider/corridor labels are internal metadata, not road names.
            "display_route": [start, *road_summary, destination],
            "distance": route["distance"],
            # HERE duration already includes traffic. For inferred traffic, apply
            # the inferred level multiplier; vehicle characteristics also apply.
            "time": calculate_real_route_time(
                route["duration"], route["distance"], vehicle,
                "Light" if has_real_traffic else level,
            ),
            "traffic": level,
            "segment_traffic": segment_traffic,
            "segment_sources": effective["segment_sources"],
            "geometry": route["geometry"],
            "traffic_geometry": route.get("traffic_geometry"),
            "road_names": route["road_names"],
            "eta_basis": eta_basis,
            "route_source": route.get("source", "unknown-real-road-provider"),
            "base_duration": route.get("base_duration", route.get("duration")),
            "traffic_time": route.get("duration") if has_real_traffic else None,
            "traffic_delay": route.get("traffic_delay") if has_real_traffic else model_state["estimated_delay_minutes"],
            "route_duration_seconds": route.get("route_duration_seconds", round(float(route["duration"]) * 60)),
            "base_duration_seconds": route.get("base_duration_seconds", round(float(route.get("base_duration", route["duration"])) * 60)),
            "traffic_delay_seconds": route.get("traffic_delay_seconds") if has_real_traffic else None,
            "provider": route.get("provider", route.get("source")),
            "provider_timestamp": route.get("provider_timestamp", route.get("retrieved_at")),
            "traffic_source": traffic_source_full,
            "traffic_source_label": traffic_source_label,
            "provider_coverage_percent": effective["provider_coverage_percent"],
            "inferred_coverage_percent": effective["inferred_coverage_percent"],
            "unknown_coverage_percent": effective["unknown_coverage_percent"],
            "provider_notice": provider_notice,
            "traffic_data_available": has_real_traffic,
            "traffic_model_available": True,  # Always true now — inferred is always computed
            "traffic_snapshot_id": traffic_snapshot.snapshot_id,
            "traffic_score": effective["traffic_score"] if effective["traffic_score"] is not None else model_state.get("average_score"),
            "heavy_segments": (
                sum(str(item).lower() == "heavy" for item in segment_traffic)
            ),
            "critical_segments": route.get("critical_segments", model_state["critical_segments"]),
            "cumulative_traffic_impact": route.get("cumulative_traffic_impact", model_state["cumulative_traffic_impact"]),
            "average_congestion_pressure": route.get("average_congestion_pressure", model_state["average_congestion_pressure"]),
            "retrieved_at": route.get("retrieved_at"),
            "segments": model_segments,
        })
    if not candidates:
        if closure_rejections:
            return {
                "error": f"All available real-road routes use the closed road '{closed_road}'. Remove the closure or try another destination.",
                "routing_mode": "real-world-only",
                "evaluation": {
                    "formula": "traffic_adjusted_eta + small safety/reliability exposure costs; lower is better",
                    "candidates_received": len(routes), "candidates_evaluated": 0,
                    "eligible_candidates": 0, "rejected_candidates": len(closure_rejections),
                    "closure": {"requested": closed_road, "matched_routes": len(closure_rejections),
                        "matched_road_names": sorted({name for item in closure_rejections for name in item["matched_road_names"]})},
                    "options": [],
                },
            }
        return {"error": "The real-road provider returned no usable routes.", "routing_mode": "real-world-only"}
    engine = decision_engine or _engine()
    eligible, evaluated = engine.evaluate(candidates, vehicle, conditions)
    if not eligible:
        return {"error":"No real-world route satisfies the active vehicle restrictions.",
            "rejected_candidates":[item["decision"] for item in evaluated],"routing_mode":"real-world-only"}
    options = eligible[:4]
    recommendation_reason = _recommendation_reason(options[0], options[1:])
    for item in options:
        item.pop("segments", None); item.pop("candidate_id", None)
    best, alternatives = options[0], options[1:]
    reason = ", ".join(best["decision"]["reasons"]) or "lowest real-road travel cost"
    evaluation = {
        "formula": "traffic_adjusted_eta + severe_congestion_exposure + delay_exposure + traffic_impact + vehicle_suitability + distance_tiebreak; lower is better",
        "candidates_received": len(routes), "candidates_evaluated": len(evaluated),
        "eligible_candidates": len(eligible),
        "rejected_candidates": len(evaluated) - len(eligible) + len(closure_rejections),
        "engine": engine.engine_name, "diagnostic": engine.diagnostic,
        "closure": {"requested": closed_road or None, "matched_routes": len(closure_rejections),
            "matched_road_names": sorted({name for item in closure_rejections for name in item["matched_road_names"]})},
        "options": [{
            "rank": index + 1, "route": item["display_route"], "distance": item["distance"],
            "time": item["time"], "traffic": item["traffic"], "decision": item["decision"],
        } for index, item in enumerate(options)],
    }
    return {"route":best["route"],"display_route":best["display_route"],"geometry":best["geometry"],
        "traffic_geometry":best.get("traffic_geometry"),
        "road_names":best["road_names"],"distance":best["distance"],"time":best["time"],
        "traffic":best["traffic"],"segment_traffic":best["segment_traffic"],
        "segment_sources":best.get("segment_sources",[]),"alternatives":alternatives,
        "eta_basis":best["eta_basis"],"route_source":best["route_source"],
        "base_duration":best.get("base_duration"),"traffic_delay":best.get("traffic_delay"),
        "traffic_time":best.get("traffic_time"),
        "traffic_source":best.get("traffic_source"),
        "traffic_source_label":best.get("traffic_source_label","INFERRED"),
        "provider_coverage_percent":best.get("provider_coverage_percent",0),
        "inferred_coverage_percent":best.get("inferred_coverage_percent",0),
        "unknown_coverage_percent":best.get("unknown_coverage_percent",0),
        "provider_notice":best.get("provider_notice"),
        "traffic_data_available":best.get("traffic_data_available",False),
        "traffic_model_available":best.get("traffic_model_available",True),
        "traffic_snapshot_id":best.get("traffic_snapshot_id"),
        "traffic_score":best.get("traffic_score"),
        "route_duration_seconds":best.get("route_duration_seconds"),
        "base_duration_seconds":best.get("base_duration_seconds"),
        "traffic_delay_seconds":best.get("traffic_delay_seconds"),
        "provider":best.get("provider"),"provider_timestamp":best.get("provider_timestamp"),
        "retrieved_at":best.get("retrieved_at"),
        "decision":best["decision"],"decision_engine":engine.engine_name,"diagnostic":engine.diagnostic,
        "evaluation": evaluation,"recommendation_reason":recommendation_reason,
        "routing_mode":"real-world-only","ai_message":
        f"Real-world Route Decision\n\nSelected roads: {' → '.join(best['display_route'])}\n"
        f"Distance: {best['distance']} km\nEstimated time: {best['time']} min\n"
        f"ETA basis: {best['eta_basis']}; it remains an estimate, not a guarantee.\nReason: {reason}.\n"
        f"Engine: {engine.engine_name}\nProvider: {best.get('traffic_source') or best.get('route_source')}."}
