"""Real-road route pipeline: provider geometry, hybrid traffic, symbolic ranking."""
import math
import re

from algorithms.graph import LOCATION_COORDS
from algorithms.vehicle import VEHICLE_SPEED, calculate_real_route_time
from app.runtime_config import traffic_mode, yangon_now
from app.traffic_config import SCENARIO_ETA_MULTIPLIERS
from services.here_traffic_service import fetch_traffic_aware_routes
from services.osrm_service import fetch_real_routes
from services.route_decision_engine import RouteDecisionEngine
from services.route_comparison import annotate_route_comparison
from services.traffic_service import TRAFFIC_ENGINE

_ENGINE = None
_GENERIC_ROAD_WORDS = {"road", "street", "avenue", "lane", "highway", "route"}
_TRAFFIC_SCORE = {"Light": 25.0, "Moderate": 55.0, "Heavy": 85.0}
_VALID_TRAFFIC = frozenset(_TRAFFIC_SCORE)
_SCENARIO_MULTIPLIERS = {"accident": 1.45, "heavy_rain": 1.22, "rush_hour": 1.18, "major_event": 1.30}


def _next_traffic_level(level):
    return {"Light": "Moderate", "Moderate": "Heavy", "Heavy": "Heavy", "Unknown": "Moderate"}.get(level, "Moderate")


def _scenario_effect(conditions, road_names, levels, sources):
    """Return deterministic route-specific scenario effects and honest provenance."""
    kind = str(conditions.get("scenario_type") or "none")
    affected = str(conditions.get("affected_road") or "").strip()
    matches = [index for index, name in enumerate(road_names) if _road_matches(affected, name)]
    applies = kind in {"heavy_rain", "rush_hour", "major_event"} or (kind == "accident" and bool(matches))
    if not applies:
        return 1.0, levels, sources, None
    changed = list(levels)
    indices = matches if kind == "accident" else list(range(len(changed)))
    for index in indices:
        if index < len(changed):
            changed[index] = "Heavy" if kind == "accident" else _next_traffic_level(changed[index])
    changed_sources = list(sources)
    for index in indices:
        if index < len(changed_sources):
            changed_sources[index] = "SIMULATED"
    description = {
        "accident": f"Simulated accident on {affected} increases delay on matching route sections.",
        "heavy_rain": "Simulated heavy rain reduces expected road speeds across the route.",
        "rush_hour": "Simulated rush-hour demand increases corridor pressure.",
        "major_event": "Simulated destination event demand increases approach-road pressure.",
    }[kind]
    return _SCENARIO_MULTIPLIERS[kind], changed, changed_sources, description


def _scenario_explanation(scenario, road_names, level):
    road = road_names[0] if road_names else "the mapped roads"
    if scenario == "off_peak":
        return f"Off-Peak conditions reduce inferred demand on {road}, resulting in {level} traffic and a scenario-adjusted ETA."
    if scenario == "peak":
        return f"Peak-Hour conditions increase inferred demand on {road}, resulting in {level} traffic and a scenario-adjusted ETA."
    return "Current Conditions use the active Asia/Yangon time window and the best available traffic evidence."


def _format_minutes(value):
    seconds = round(abs(float(value)) * 60)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes} min {seconds} sec" if seconds else f"{minutes} min"
def _practical_time_tolerance(eta_minutes):
    return max(1.0, min(3.0, eta_minutes * 0.1))

def _practical_distance_tolerance(dist_km):
    return max(0.4, min(2.0, dist_km * 0.1))


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
    delay_advantage = round(float(alternative.get("traffic_delay", 0)) - float(best.get("traffic_delay", 0)), 2)
    heavy_difference = int(best.get("heavy_segments", 0)) - int(alternative.get("heavy_segments", 0))
    dominated = bool(eta_advantage >= 0 and distance_difference >= 0 and heavy_difference <= 0)
    severity = {"Light": 1, "Moderate": 2, "Heavy": 3}
    best_level = str(best.get("traffic") or "Unknown")
    alternative_level = str(alternative.get("traffic") or "Unknown")
    traffic_improvement = severity.get(alternative_level, 2) - severity.get(best_level, 2)
    
    time_tol = _practical_time_tolerance(float(best["time"]))
    
    if traffic_improvement > 0:
        primary = "lower_congestion_with_practical_detour"
        if alternative_level == "Heavy":
            explanation = "The recommended route avoids heavy traffic with only a small detour."
        else:
            explanation = "The recommended route has lighter traffic with only a small increase in travel time."
    elif traffic_improvement < 0:
        primary = "avoid_unreasonable_detour"
        explanation = "The recommended route is selected because Alternative 1 requires a substantial detour despite having lighter traffic."
    else:
        if abs(eta_advantage) > time_tol:
            primary = "lower_travel_time"
            explanation = f"Both routes have similar traffic conditions, but the recommended route is {_format_minutes(eta_advantage)} faster."
        else:
            primary = "best_practical_traffic_balance"
            explanation = "Both routes have similar traffic conditions. The recommended route is the more direct option."
            
    return {
        "recommended_route_id": best_id, "primary_reason": primary,
        "eta_advantage_minutes": eta_advantage,
        "distance_difference_km": distance_difference,
        "heavy_segment_difference": heavy_difference,
        "delay_advantage_minutes": delay_advantage,
        "dominated_alternatives": dominated, "explanation": explanation,
    }


def _comparison_to_recommended(best, alternative):
    """Build the user-facing comparison once from ranked backend metrics."""
    eta_delta = round(float(alternative["time"]) - float(best["time"]), 2)
    distance_delta = round(float(alternative["distance"]) - float(best["distance"]), 2)
    heavy_delta = int(alternative.get("heavy_segments", 0)) - int(best.get("heavy_segments", 0))
    
    time_tol = _practical_time_tolerance(float(best["time"]))
    dist_tol = _practical_distance_tolerance(float(best["distance"]))
    
    parts = []
    if abs(eta_delta) > time_tol:
        parts.append(f"{_format_minutes(eta_delta)} {'slower' if eta_delta > 0 else 'faster'}")
    if abs(distance_delta) > dist_tol:
        parts.append(f"{abs(distance_delta):.2f} km {'longer' if distance_delta > 0 else 'shorter'}")
        
    explanation = " and ".join(parts).capitalize() + "." if parts else ""
    if explanation:
        if heavy_delta < 0:
            explanation = explanation.rstrip(".") + f", but avoids {abs(heavy_delta)} Heavy segment(s)."
        elif heavy_delta > 0:
            explanation = explanation.rstrip(".") + f" and includes {heavy_delta} additional Heavy segment(s)."
            
    return {
        "eta_difference_minutes": eta_delta,
        "distance_difference_km": distance_delta,
        "heavy_segment_difference": heavy_delta,
        "explanation": explanation,
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


def _weighted_level(levels, traffic_geometry=None, segment_weights=None):
    valid = [(index, level) for index, level in enumerate(levels) if level in _VALID_TRAFFIC]
    if not valid:
        return "Unknown", None
    weights = []
    for index, _level in valid:
        geometry = traffic_geometry[index] if traffic_geometry and index < len(traffic_geometry) else ()
        fallback = segment_weights[index] if segment_weights and index < len(segment_weights) else 1.0
        weights.append(max(0.001, _polyline_length(geometry) or fallback))
    score = sum(_TRAFFIC_SCORE[level] * weight for (_, level), weight in zip(valid, weights)) / sum(weights)
    level = "Light" if score <= 35 else "Moderate" if score <= 70 else "Heavy"
    return level, round(score, 1)


def _effective_route_traffic(route, model_state, allow_provider=True):
    """Merge provider sections with inference and retain honest provenance."""
    provider_levels = list(route.get("segment_traffic") or ()) if allow_provider else []
    provider_sources = ([str(value).upper() for value in (route.get("segment_sources") or ())]
                        if allow_provider else [])
    complete_provider_response = bool(allow_provider and route.get("traffic_data_available") and not provider_sources)
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
    level, score = _weighted_level(levels, route.get("traffic_geometry"), model_state.get("segment_distances"))
    provider, inferred, unknown = _coverage_from_sources(sources)
    label = "HERE" if provider == 100 else "INFERRED" if inferred == 100 else "UNKNOWN" if unknown == 100 else "MIXED"
    description = {"HERE": "HERE Real-Time Traffic", "INFERRED": "Inferred Traffic Model", "MIXED": "Mixed Traffic Data", "UNKNOWN": "Traffic Data Unavailable"}[label]
    return {"traffic": level, "traffic_score": score, "segment_traffic": levels,
            "segment_sources": sources, "traffic_source_label": label,
            "traffic_source": description, "provider_coverage_percent": provider,
            "inferred_coverage_percent": inferred, "unknown_coverage_percent": unknown}


def _filter_practical_alternatives(candidates):
    if not candidates:
        return []
    primary = candidates[0]
    prim_dist = float(primary["distance"])
    prim_time = float(primary["time"])
    levels = {"Light": 1, "Moderate": 2, "Heavy": 3, "Unknown": 2}
    prim_level = levels.get(primary["overall_traffic"], 2)
    
    practical = [primary]
    
    for cand in candidates[1:]:
        cand_dist = float(cand["distance"])
        cand_time = float(cand["time"])
        dist_diff = cand_dist - prim_dist
        time_diff = cand_time - prim_time
        dist_ratio = cand_dist / max(0.1, prim_dist)
        time_ratio = cand_time / max(0.1, prim_time)
        
        cand_level = levels.get(cand["overall_traffic"], 2)
        traffic_advantage = prim_level - cand_level
        
        if cand_dist > prim_dist * 2.5:
            continue
            
        if prim_dist <= 3.0:
            if traffic_advantage <= 0:
                if dist_ratio > 1.25 or dist_diff > 0.5:
                    continue
                if time_ratio > 1.3 or time_diff > 2.0:
                    continue
            else:
                if dist_ratio > 1.6 or dist_diff > 1.5:
                    continue
                if time_ratio > 1.7 or time_diff > 4.0:
                    continue
        else:
            if traffic_advantage <= 0:
                if dist_ratio > 1.15 or dist_diff > 2.0:
                    continue
                if time_ratio > 1.2 or time_diff > 3.0:
                    continue
            else:
                if dist_ratio > 1.4 or dist_diff > 4.0:
                    continue
                if time_ratio > 1.5 or time_diff > 6.0:
                    continue
                    
        practical.append(cand)
    return practical

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
    scenario = str(conditions.get("traffic_scenario") or conditions.get("time_band") or "current").lower()
    if scenario not in {"current", "off_peak", "peak"}:
        scenario = "current"
    hypothetical = scenario != "current"
    try:
        # HERE represents present conditions only. Hypothetical scenarios use
        # mapped-road geometry plus our explicitly labelled inference model.
        provider = route_provider or (fetch_real_routes if hypothetical else _real_route_provider)
        routes = provider(LOCATION_COORDS[start], LOCATION_COORDS[destination], alternatives=3)
    except Exception as exc:
        return {"error": str(exc), "routing_mode": "real-world-only"}

    conditions["traffic_scenario"] = scenario
    conditions["time_band"] = scenario if hypothetical else _time_band(conditions)
    # Real weather is intentionally not part of normal routing.  Only the
    # explicit Heavy Rain what-if scenario may activate a weather rule.
    conditions["weather"] = "storm" if str(conditions.get("scenario_type") or "none") == "heavy_rain" else "clear"
    conditions.setdefault("incident", "none")
    scenario_type = str(conditions.get("scenario_type") or "none")
    if scenario_type == "rush_hour":
        conditions["time_band"] = "peak"
    elif scenario_type == "heavy_rain":
        conditions["weather"] = "storm"
    elif scenario_type in {"accident", "major_event"}:
        conditions["incident"] = "major"
    if scenario_type == "road_closed" and conditions.get("affected_road"):
        conditions["closed_road"] = conditions["affected_road"]
    traffic_engine = traffic_engine or TRAFFIC_ENGINE
    # Always obtain inferred traffic snapshot — used as fallback for segments
    # without provider coverage, regardless of traffic mode setting.
    if traffic_snapshot is None or getattr(traffic_snapshot, "scenario", "current") != scenario:
        traffic_snapshot = traffic_engine.get_snapshot(scenario=scenario)
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
        has_real_traffic = bool(route.get("traffic_data_available")) and not hypothetical

        # Always compute inferred model state — used as segment fallback even
        # when HERE provides the route-level traffic.
        model_state = traffic_engine.route_state(
            start, destination, route.get("road_names", ()), traffic_snapshot, route.get("geometry", ())
        )

        effective = _effective_route_traffic(route, model_state, allow_provider=not hypothetical)
        level = effective["traffic"]
        segment_traffic = effective["segment_traffic"]
        scenario_multiplier, segment_traffic, segment_sources, scenario_detail = _scenario_effect(
            conditions, road_summary, segment_traffic, effective["segment_sources"]
        )
        if scenario_detail:
            level, scenario_score = _weighted_level(segment_traffic, route.get("traffic_geometry"), model_state.get("segment_distances"))
            effective["traffic_score"] = scenario_score
            effective["segment_sources"] = segment_sources
            effective["traffic_source_label"] = "SIMULATED" if all(source == "SIMULATED" for source in segment_sources) else "MIXED"
            effective["traffic_source"] = "Simulated Scenario" if effective["traffic_source_label"] == "SIMULATED" else "Mixed Observed/Inferred and Simulated Scenario"
        traffic_source_label = effective["traffic_source_label"]
        traffic_source_full = effective["traffic_source"]
        segment_diagnostics = []
        for index, diagnostic in enumerate(model_state.get("segment_diagnostics", [])):
            provider_road = road_summary[min(index, len(road_summary) - 1)] if road_summary else None
            segment_diagnostics.append({
                **diagnostic,
                "road_name": provider_road or diagnostic.get("road_name"),
                "model_reference_road": (diagnostic.get("road_name")
                                         if provider_road and provider_road != diagnostic.get("road_name") else None),
            })
        provider_notice = (scenario_detail if scenario_detail else f"{scenario.replace('_', '-').title()} scenario uses inferred traffic conditions."
                           if hypothetical else None if traffic_source_label == "HERE" else (
            "Some traffic sections use inferred estimates." if traffic_source_label == "MIXED"
            else "HERE traffic is unavailable; traffic is estimated from the inferred traffic model."
        ))
        eta_basis = ("Scenario-adjusted mapped-road duration" if scenario_detail else "HERE traffic-aware duration adjusted for the selected vehicle" if traffic_source_label == "HERE"
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
        traffic_eta = calculate_real_route_time(
            route["duration"], route["distance"], vehicle,
            "Light" if has_real_traffic else level,
        )
        if hypothetical:
            traffic_eta = round(traffic_eta * SCENARIO_ETA_MULTIPLIERS[scenario], 2)
        if scenario_multiplier > 1.0:
            traffic_eta = round(traffic_eta * scenario_multiplier, 2)
        calculated_free_flow = calculate_real_route_time(
            route.get("base_duration", route["duration"]), route["distance"], vehicle, "Light"
        )
        free_flow_eta = round(min(traffic_eta, calculated_free_flow), 2)
        effective_delay = round(max(0.0, traffic_eta - free_flow_eta), 2)
        candidates.append({
            "candidate_id": route["provider_id"], "route": [start, destination],
            # Provider/corridor labels are internal metadata, not road names.
            "display_route": [start, *road_summary, destination],
            "distance": route["distance"],
            # HERE duration already includes traffic. For inferred traffic, apply
            # the inferred level multiplier; vehicle characteristics also apply.
            "time": traffic_eta,
            "traffic_adjusted_eta": traffic_eta,
            "free_flow_eta": free_flow_eta,
            "traffic": level,
            "overall_traffic": level,
            "segment_traffic": segment_traffic,
            "segment_sources": effective["segment_sources"],
            "geometry": route["geometry"],
            "traffic_geometry": route.get("traffic_geometry"),
            "road_names": route["road_names"],
            "eta_basis": eta_basis,
            "route_source": route.get("source", "unknown-real-road-provider"),
            "base_duration": route.get("base_duration", route.get("duration")),
            "traffic_time": route.get("duration") if has_real_traffic else None,
            "traffic_delay": effective_delay,
            "route_duration_seconds": route.get("route_duration_seconds", round(float(route["duration"]) * 60)),
            "base_duration_seconds": route.get("base_duration_seconds", round(float(route.get("base_duration", route["duration"])) * 60)),
            "traffic_delay_seconds": round(effective_delay * 60),
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
            "provider_coverage": effective["provider_coverage_percent"],
            "traffic_score": effective["traffic_score"] if effective["traffic_score"] is not None else model_state.get("average_score"),
            "heavy_segments": (
                sum(str(item).lower() == "heavy" for item in segment_traffic)
            ),
            "critical_segments": route.get("critical_segments", model_state["critical_segments"]),
            "cumulative_traffic_impact": route.get("cumulative_traffic_impact", model_state["cumulative_traffic_impact"]),
            "average_congestion_pressure": route.get("average_congestion_pressure", model_state["average_congestion_pressure"]),
            "retrieved_at": route.get("retrieved_at"),
            "segment_diagnostics": segment_diagnostics,
            "traffic_scenario": scenario,
            "scenario_explanation": scenario_detail or _scenario_explanation(scenario, road_summary, level),
            "scenario_type": scenario_type,
            "segments": model_segments,
        })
    candidates = _filter_practical_alternatives(candidates)
    if not candidates:
        if closure_rejections:
            return {
                "error": f"All available real-road routes use the closed road '{closed_road}'. Remove the closure or try another destination.",
                "routing_mode": "real-world-only",
                "evaluation": {
                    "formula": "travel_time + traffic_exposure + rule_penalties + bounded_detour_cost; lower is better",
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
    options = annotate_route_comparison(eligible[:3])
    recommendation_reason = _recommendation_reason(options[0], options[1:])
    recommended = options[0]
    for index, item in enumerate(options):
        item["route_id"] = str(item.get("candidate_id"))
        item["route_type"] = "recommended" if index == 0 else "alternative"
        item["major_roads"] = list(item.get("road_names", []))
        item["distance_km"] = item["distance"]
        item["free_flow_eta_seconds"] = round(float(item.get("free_flow_eta") or 0) * 60)
        item["traffic_adjusted_eta_seconds"] = round(float(item.get("traffic_adjusted_eta") or item["time"]) * 60)
        item["route_cost"] = item.get("decision", {}).get("route_cost")
        item["rules_fired"] = list(item.get("decision", {}).get("rules_fired", []))
        item["comparison_to_recommended"] = None if index == 0 else _comparison_to_recommended(recommended, item)
        item["recommendation_reason"] = (
            recommendation_reason if index == 0 else {
                "primary_reason": "provider_alternative",
                "explanation": "A distinct real-road alternative returned by the routing provider.",
            }
        )
        item["direction_summary"] = {
            "origin": start, "destination": destination,
            "major_roads": list(item.get("road_names", [])),
            "provider_geometry_is_direction_specific": True,
        }
        item.pop("segments", None); item.pop("candidate_id", None)
    best, alternatives = options[0], options[1:]
    reason = ", ".join(best["decision"]["reasons"]) or "lowest real-road travel cost"
    evaluation = {
        "formula": "travel_time + traffic_exposure + rule_penalties + bounded_detour_cost; lower is better",
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
        "overall_traffic":best.get("overall_traffic",best["traffic"]),
        "segment_sources":best.get("segment_sources",[]),"alternatives":alternatives,
        "eta_basis":best["eta_basis"],"route_source":best["route_source"],
        "traffic_adjusted_eta":best.get("traffic_adjusted_eta",best["time"]),
        "free_flow_eta":best.get("free_flow_eta"),
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
        "traffic_scenario": scenario,
        "scenario_type": scenario_type,
        "scenario_explanation": best.get("scenario_explanation"),
        "provider_coverage":best.get("provider_coverage"),
        "route_id":best.get("route_id"),"route_cost":best.get("route_cost"),
        "route_label":best.get("route_label"),
        "characteristics":best.get("characteristics",[]),
        "confidence":best.get("confidence"),
        "confidence_basis":best.get("confidence_basis",[]),
        "rules_fired":best.get("rules_fired",[]),
        "route_type":best.get("route_type"),"major_roads":best.get("major_roads",[]),
        "distance_km":best.get("distance_km"),
        "free_flow_eta_seconds":best.get("free_flow_eta_seconds"),
        "traffic_adjusted_eta_seconds":best.get("traffic_adjusted_eta_seconds"),
        "comparison_to_recommended":best.get("comparison_to_recommended"),
        "segment_diagnostics":best.get("segment_diagnostics",[]),
        "direction_summary":best.get("direction_summary"),
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
        f"Distance: {best['distance']} km\nTravel time: {best['time']} min\n"
        f"Travel-time basis: {best['eta_basis']}; it remains an estimate, not a guarantee.\nReason: {reason}.\n"
        f"Engine: {engine.engine_name}\nProvider: {best.get('traffic_source') or best.get('route_source')}."}
