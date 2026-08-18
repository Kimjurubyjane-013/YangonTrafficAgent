"""Real-road route pipeline: HERE traffic candidates + symbolic ranking."""
from datetime import datetime
import re

from algorithms.graph import LOCATION_COORDS
from algorithms.vehicle import VEHICLE_SPEED, calculate_real_route_time
from services.here_traffic_service import fetch_traffic_aware_routes
from services.osrm_service import fetch_real_routes
from services.route_decision_engine import RouteDecisionEngine

_ENGINE = None
_GENERIC_ROAD_WORDS = {"road", "street", "avenue", "lane", "highway", "route"}


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


def run_real_world_agent(start, destination, vehicle, conditions=None, route_provider=None, decision_engine=None):
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
        # A real-road provider without traffic telemetry must not be presented
        # as if it supplied live congestion data.
        level = route.get("traffic_level") if has_real_traffic else "Unavailable"
        eta_basis = (
            "HERE traffic-aware duration adjusted for the selected vehicle"
            if has_real_traffic else
            "Provider road duration adjusted for vehicle type and selected traffic scenario"
        )
        candidates.append({
            "candidate_id": route["provider_id"], "route": [start, destination],
            # Provider/corridor labels are internal metadata, not road names.
            "display_route": [start, *road_summary, destination],
            "distance": route["distance"],
            # HERE duration already includes traffic. Passing Light here avoids
            # applying a second synthetic congestion multiplier; vehicle
            # characteristics remain part of the existing domain model.
            "time": calculate_real_route_time(route["duration"], route["distance"], vehicle, "Light"),
            "traffic": level, "segment_traffic": route.get("segment_traffic", [level]), "geometry": route["geometry"],
            "road_names": route["road_names"],
            "eta_basis": eta_basis,
            "route_source": route.get("source", "unknown-real-road-provider"),
            "base_duration": route.get("base_duration"),
            "traffic_delay": route.get("traffic_delay"),
            "traffic_source": route.get("traffic_source"),
            "traffic_data_available": has_real_traffic,
            "retrieved_at": route.get("retrieved_at"),
            "segments": [{"index":0,"name":road_label,"road_class":"arterial",
                "traffic":level.lower() if has_real_traffic else "light",
                "preferred":False,"one_way_ok":True}],
        })
    if not candidates:
        if closure_rejections:
            return {
                "error": f"All available real-road routes use the closed road '{closed_road}'. Remove the closure or try another destination.",
                "routing_mode": "real-world-only",
                "evaluation": {
                    "formula": "distance_km + 0.35 x estimated_minutes + rule_penalty",
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
    for item in options:
        item.pop("segments", None); item.pop("candidate_id", None)
    best, alternatives = options[0], options[1:]
    reason = ", ".join(best["decision"]["reasons"]) or "lowest real-road travel cost"
    evaluation = {
        "formula": "distance_km + 0.35 x estimated_minutes + rule_penalty",
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
        "traffic_source":best.get("traffic_source"),
        "traffic_data_available":best.get("traffic_data_available",False),
        "retrieved_at":best.get("retrieved_at"),
        "decision":best["decision"],"decision_engine":engine.engine_name,"diagnostic":engine.diagnostic,
        "evaluation": evaluation,
        "routing_mode":"real-world-only","ai_message":
        f"Real-world Route Decision\n\nSelected roads: {' → '.join(best['display_route'])}\n"
        f"Distance: {best['distance']} km\nEstimated time: {best['time']} min\n"
        f"ETA basis: {best['eta_basis']}; it remains an estimate, not a guarantee.\nReason: {reason}.\n"
        f"Engine: {engine.engine_name}\nProvider: {best.get('traffic_source') or best.get('route_source')}."}
