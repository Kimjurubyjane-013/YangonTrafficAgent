"""Explainable hybrid traffic-agent orchestration."""
from datetime import datetime
from algorithms.graph import GRAPH
from algorithms.road_metadata import ROAD_METADATA, road_attributes
from algorithms.route_finder import find_all_simple_paths
from algorithms.vehicle import VEHICLE_SPEED, calculate_time
from services.route_decision_engine import RouteDecisionEngine
from services.traffic_service import TRAFFIC_ENGINE, get_time_period

TRAFFIC_MULTIPLIER = {"Light": 1.0, "Moderate": 1.4, "Heavy": 1.9}
MAX_CANDIDATES, MAX_ROUTE_OPTIONS = 24, 4
_ENGINE = None

def _decision_engine():
    global _ENGINE
    if _ENGINE is None: _ENGINE = RouteDecisionEngine()
    return _ENGINE

def _time_band(now=None):
    return "peak" if get_time_period(now or datetime.now()) in {"MORNING_RUSH", "EVENING_RUSH"} else "off_peak"

def _segment_traffic_for_edge(a, b, weight, now=None):
    # Custom/legacy graphs have no canonical road state. Keep their fallback
    # stable; production graph edges always use the shared TrafficSnapshot.
    return "Moderate"

def _build_candidate(cid, path, distance, vehicle, conditions, graph, metadata, traffic_snapshot=None):
    overrides, segments, levels = conditions.get("segment_traffic", {}), [], []
    for index, (start, end) in enumerate(zip(path, path[1:])):
        attrs = road_attributes(start, end, metadata)
        model_state = traffic_snapshot.roads.get(attrs.get("road_id")) if traffic_snapshot else None
        level = overrides.get((start,end)) or (model_state.traffic_level if model_state else None)
        level = level or _segment_traffic_for_edge(start,end,graph[start][end],conditions.get("now"))
        level = str(level).title(); level = level if level in TRAFFIC_MULTIPLIER else "Moderate"
        levels.append(level)
        segments.append({"index":index,"name":f"{start} -> {end}","start":start,"end":end,
            "road_class":attrs["road_class"],"preferred":bool(attrs["preferred"]),
            "one_way_ok":bool(attrs["one_way_ok"]),"traffic":level.lower()})
    multiplier = sum(TRAFFIC_MULTIPLIER[x] for x in levels) / len(levels)
    return {"candidate_id":cid,"route":list(path),"distance":round(distance,1),
        "time":round(calculate_time(distance,vehicle)*multiplier,1),
        "traffic":max(levels,key=TRAFFIC_MULTIPLIER.get),"segment_traffic":levels,"segments":segments}

def _recommendation(best, alternatives, diagnostic):
    d=best["decision"]; reasons=", ".join(d["reasons"]) or "lowest combined numeric and rule-based cost"
    return (f"Route Decision\n\nEngine: {d['engine']}\nSelected: {' -> '.join(best['route'])}\n"
        f"Score: {d['total_score']:.2f}\nReason: {reasons}.\nDistance: {best['distance']} km; "
        f"estimated time: {best['time']} min; traffic: {best['traffic'].lower()}.\n"
        f"{len(alternatives)} alternative route(s) retained.\n\nDiagnostic: {diagnostic}")

def run_traffic_agent(start, destination, vehicle, conditions=None, graph=None, road_metadata=None, decision_engine=None,
                      traffic_engine=None, traffic_snapshot=None):
    graph=graph or GRAPH; metadata=ROAD_METADATA if road_metadata is None else road_metadata
    conditions=dict(conditions or {}); conditions.setdefault("time_band",_time_band(conditions.get("now")))
    conditions.setdefault("weather","clear"); conditions.setdefault("incident","none")
    if not all(isinstance(x,str) for x in (start,destination,vehicle)):
        return {"error":"Start, destination, and vehicle must be text values."}
    if start==destination: return {"error":"Start and destination must be different."}
    if start not in graph or destination not in graph: return {"error":"Unknown location."}
    if vehicle not in VEHICLE_SPEED: return {"error":"Unknown vehicle type."}
    paths=find_all_simple_paths(graph,start,destination,max_depth=min(8,len(graph)),max_candidates=MAX_CANDIDATES)
    if not paths: return {"error":f"No route found between {start} and {destination}."}
    if graph is GRAPH and metadata is ROAD_METADATA:
        traffic_engine = traffic_engine or TRAFFIC_ENGINE
        traffic_snapshot = traffic_snapshot or traffic_engine.get_snapshot(conditions.get("now"))
    candidates=[_build_candidate(i,p,d,vehicle,conditions,graph,metadata,traffic_snapshot) for i,(p,d) in enumerate(paths)]
    engine=decision_engine or _decision_engine(); eligible,evaluated=engine.evaluate(candidates,vehicle,conditions)
    if not eligible: return {"error":"No eligible route satisfies the active restrictions.",
        "decision_engine":engine.engine_name,"diagnostic":engine.diagnostic,
        "rejected_candidates":[x["decision"] for x in evaluated]}
    options=eligible[:MAX_ROUTE_OPTIONS]
    for item in options: item.pop("segments",None); item.pop("candidate_id",None)
    best,alternatives=options[0],options[1:]
    return {"route":best["route"],"distance":best["distance"],"time":best["time"],
        "traffic":best["traffic"],"segment_traffic":best["segment_traffic"],"alternatives":alternatives,
        "decision":best["decision"],"decision_engine":engine.engine_name,"diagnostic":engine.diagnostic,
        "ai_message":_recommendation(best,alternatives,engine.diagnostic)}
