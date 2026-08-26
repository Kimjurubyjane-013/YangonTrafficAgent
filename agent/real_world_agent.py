"""Real-road route pipeline: HERE traffic candidates + symbolic ranking."""
from datetime import datetime
import re

from algorithms.graph import LOCATION_COORDS
from algorithms.vehicle import VEHICLE_SPEED, calculate_real_route_time
from services.here_traffic_service import fetch_traffic_aware_routes
from services.osrm_service import fetch_real_routes
from services.route_decision_engine import RouteDecisionEngine
from services.traffic_service import TRAFFIC_ENGINE

_ENGINE = None
_GENERIC_ROAD_WORDS = {"road", "street", "avenue", "lane", "highway", "route"}


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
    hour = datetime.now().hour
    return "peak" if hour in {7,8,9,16,17,18,19} else "off_peak"


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
    traffic_engine = traffic_engine or TRAFFIC_ENGINE
    traffic_snapshot = traffic_snapshot or traffic_engine.get_snapshot()
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
        model_state = traffic_engine.route_state(
            start, destination, route.get("road_names", ()), traffic_snapshot
        )
        # Provider telemetry remains authoritative when genuinely available;
        # otherwise every route consumes the shared academic traffic snapshot.
        level = route.get("traffic_level") if has_real_traffic else model_state["traffic_level"]
        segment_traffic = route.get("segment_traffic") if has_real_traffic else model_state["segment_traffic"]
        eta_basis = (
            "HERE traffic-aware duration adjusted for the selected vehicle"
            if has_real_traffic else
            "Provider road duration adjusted by the shared academic traffic snapshot and vehicle type"
        )
        model_segments = []
        if has_real_traffic:
            model_segments.append({"index":0,"name":road_label,"road_class":"arterial",
                "traffic":str(level).lower(),"preferred":False,"one_way_ok":True})
        else:
            for index, road_id in enumerate(model_state["road_ids"]):
                road = traffic_engine.repository.by_id[road_id]
                state = traffic_snapshot.roads[road_id]
                model_segments.append({
                    "index": index, "name": road.road_name, "road_class": road.road_type,
                    "traffic": state.traffic_level.lower(), "preferred": road.preferred,
                    "one_way_ok": road.bidirectional,
                })
        if not model_segments:
            model_segments = [{"index":0,"name":road_label,"road_class":"arterial",
                "traffic":str(level).lower(),"preferred":False,"one_way_ok":True}]
        candidates.append({
            "candidate_id": route["provider_id"], "route": [start, destination],
            # Provider/corridor labels are internal metadata, not road names.
            "display_route": [start, *road_summary, destination],
            "distance": route["distance"],
            # HERE duration already includes traffic. Passing Light here avoids
            # applying a second synthetic congestion multiplier; vehicle
            # characteristics remain part of the existing domain model.
            "time": calculate_real_route_time(route["duration"], route["distance"], vehicle, "Light" if has_real_traffic else level),
            "traffic": level, "segment_traffic": segment_traffic or [level], "geometry": route["geometry"],
            "road_names": route["road_names"],
            "eta_basis": eta_basis,
            "route_source": route.get("source", "unknown-real-road-provider"),
            "base_duration": route.get("base_duration", route.get("duration")),
            "traffic_time": route.get("duration") if has_real_traffic else None,
            "traffic_delay": route.get("traffic_delay") if has_real_traffic else model_state["estimated_delay_minutes"],
            "traffic_source": "HERE Traffic" if has_real_traffic else "Academic Simulation",
            "provider_notice": None if has_real_traffic else "Real traffic provider unavailable; using the academic traffic model.",
            "traffic_data_available": has_real_traffic,
            "traffic_model_available": True,
            "traffic_snapshot_id": traffic_snapshot.snapshot_id,
            "traffic_score": route.get("traffic_score", model_state["average_score"]),
            "heavy_segments": (
                sum(str(item).lower() == "heavy" for item in (segment_traffic or [level]))
                if has_real_traffic else model_state["heavy_segments"]
            ),
            "critical_segments": route.get("critical_segments", model_state["critical_segments"] if not has_real_traffic else 0),
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
        "road_names":best["road_names"],"distance":best["distance"],"time":best["time"],
        "traffic":best["traffic"],"segment_traffic":best["segment_traffic"],"alternatives":alternatives,
        "eta_basis":best["eta_basis"],"route_source":best["route_source"],
        "base_duration":best.get("base_duration"),"traffic_delay":best.get("traffic_delay"),
        "traffic_time":best.get("traffic_time"),
        "traffic_source":best.get("traffic_source"),
        "provider_notice":best.get("provider_notice"),
        "traffic_data_available":best.get("traffic_data_available",False),
        "traffic_model_available":best.get("traffic_model_available",True),
        "traffic_snapshot_id":best.get("traffic_snapshot_id"),
        "traffic_score":best.get("traffic_score"),
        "retrieved_at":best.get("retrieved_at"),
        "decision":best["decision"],"decision_engine":engine.engine_name,"diagnostic":engine.diagnostic,
        "evaluation": evaluation,"recommendation_reason":recommendation_reason,
        "routing_mode":"real-world-only","ai_message":
        f"Real-world Route Decision\n\nSelected roads: {' → '.join(best['display_route'])}\n"
        f"Distance: {best['distance']} km\nEstimated time: {best['time']} min\n"
        f"ETA basis: {best['eta_basis']}; it remains an estimate, not a guarantee.\nReason: {reason}.\n"
        f"Engine: {engine.engine_name}\nProvider: {best.get('traffic_source') or best.get('route_source')}."}
