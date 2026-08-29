"""Mode-aware hybrid traffic facade used by desktop and HTTP APIs.

Source hierarchy:
  1. HERE real-time flow (when API key is present and data is available)
  2. Reality-based inferred traffic model (deterministic, time/road-context aware)
  3. Unknown only when road metadata is genuinely missing

The inferred fallback is NEVER called "Real-Time" or "Live". It is labelled
"Inferred Traffic" or "Inferred Traffic Model" throughout.
"""
from __future__ import annotations

from copy import deepcopy

from app.runtime_config import traffic_mode, yangon_now
from services.here_flow_service import HERE_FLOW_SERVICE, HereFlowUnavailable
from services.road_repository import ROAD_REPOSITORY
from services.traffic_service import TRAFFIC_ENGINE, get_time_period, is_rush_hour, traffic_health_label


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coverage(roads: list[dict]) -> dict:
    """Compute provider/inferred/unknown coverage percentages."""
    total = len(roads)
    if total == 0:
        return {"provider_coverage_percent": 0, "inferred_coverage_percent": 0, "unknown_coverage_percent": 100}
    provider = sum(1 for r in roads if str(r.get("source", "")).upper() == "HERE")
    inferred = sum(1 for r in roads if str(r.get("source", "")).upper() == "INFERRED")
    unknown = total - provider - inferred
    provider_percent = round(provider / total * 100, 1)
    inferred_percent = round(inferred / total * 100, 1)
    return {
        "provider_coverage_percent": provider_percent,
        "inferred_coverage_percent": inferred_percent,
        # Derive the final bucket so displayed coverage always totals 100%.
        "unknown_coverage_percent": round(max(0.0, 100.0 - provider_percent - inferred_percent), 1),
    }


def _traffic_mode_label(roads: list[dict]) -> str:
    cov = _coverage(roads)
    if cov["provider_coverage_percent"] == 100:
        return "Real-Time"
    if cov["provider_coverage_percent"] > 0:
        return "Mixed"
    return "Inferred"


def _rank_hotspots(roads, limit):
    available = [road for road in roads if road.get("traffic_level") not in (None, "Unavailable", "Unknown")]
    available.sort(key=lambda road: (-(road.get("traffic_impact") or 0), -(road.get("traffic_score") or 0), road["road_id"]))
    return available[:limit]


def _rank_best(roads, limit):
    available = [road for road in roads if road.get("traffic_level") not in (None, "Unavailable", "Unknown")]
    available.sort(key=lambda road: (road.get("traffic_score") if road.get("traffic_score") is not None else 101, -(road.get("average_speed_kmh") or 0), road["road_id"]))
    return available[:limit]


def _inferred_overview(engine, now, force=False):
    """Wrap the traffic engine output as an inferred-traffic response."""
    result = engine.overview(force=force)
    roads = result.get("roads", [])
    # Re-label source fields so the frontend knows this is inferred, not real.
    for road in roads:
        road["source"] = "INFERRED"
        road["traffic_source"] = "Inferred Traffic"
    hotspots = _rank_hotspots(roads, 8)
    best = _rank_best(roads, 8)
    coverage = _coverage(roads)
    return {
        **result,
        "mode": "inferred",
        "available": True,
        "status": "ok",
        "traffic_source": "Inferred Traffic",
        "traffic_mode_label": "Inferred",
        "source": "inferred_traffic",
        "provider_updated_at": None,
        "yangon_local_time": now.isoformat(timespec="seconds"),
        "snapshot_time": now.isoformat(timespec="seconds"),
        "time_period": get_time_period(now),
        "rush_hour": is_rush_hour(now),
        "fallback_active": True,
        "hotspots": hotspots,
        "most_congested": hotspots[:5],
        "best_flowing": best[:5],
        **coverage,
    }


def _unknown_overview(now, message="Traffic evidence is temporarily unavailable."):
    roads = [{
        "road_id": road.id, "road_name": road.road_name, "road_type": road.road_type,
        "traffic_level": "Unknown", "traffic_score": None, "average_speed_kmh": None,
        "estimated_delay_minutes": None, "traffic_impact": None,
        "critical_congestion": False, "source": "UNKNOWN", "matched": False,
    } for road in ROAD_REPOSITORY.roads]
    return {
        "mode": "unknown", "available": False, "status": "degraded",
        "traffic_source": "Traffic Data Unavailable", "traffic_mode_label": "Unknown",
        "source": "UNKNOWN", "message": message, "provider_updated_at": None,
        "yangon_local_time": now.isoformat(timespec="seconds"),
        "snapshot_time": now.isoformat(timespec="seconds"),
        "time_period": get_time_period(now), "rush_hour": is_rush_hour(now),
        "traffic_health_score": None, "traffic_health_label": "Unknown",
        "total_roads": len(roads), "light_count": 0, "moderate_count": 0,
        "heavy_count": 0, "critical_count": 0, "hotspots": [],
        "most_congested": [], "best_flowing": [], "roads": roads,
        **_coverage(roads),
    }


def _real_overview(snapshot, now, inference_engine):
    """Build overview from HERE provider snapshot, filling gaps with inferred data."""
    roads = snapshot["roads"]
    matched = [road for road in roads if road.get("matched")]
    unmatched_ids = {road["road_id"] for road in roads if not road.get("matched")}

    # Enrich unmatched roads with inferred traffic
    if unmatched_ids:
        try:
            inferred_snapshot = inference_engine.get_snapshot()
        except Exception:
            inferred_snapshot = None
        for road in roads:
            if road["road_id"] in unmatched_ids:
                state = inferred_snapshot.roads.get(road["road_id"]) if inferred_snapshot else None
                if state:
                    road.update({
                        "traffic_level": state.traffic_level,
                        "traffic_score": round(state.traffic_score, 1),
                        "average_speed_kmh": round(state.average_speed_kmh, 1),
                        "estimated_delay_minutes": round(state.estimated_delay_minutes, 2),
                        "traffic_impact": round(state.traffic_impact, 1),
                        "critical_congestion": state.critical_congestion,
                        "source": "INFERRED",
                        "traffic_source": "Inferred Traffic",
                        "matched": False,
                        "inferred": True,
                    })

    for road in roads:
        if road.get("matched") and str(road.get("source", "")).upper() != "INFERRED":
            road["source"] = "HERE"
        elif road.get("traffic_level") in (None, "Unavailable", "Unknown"):
            road["source"] = "UNKNOWN"

    effective = [road for road in roads if road.get("traffic_level") not in (None, "Unavailable", "Unknown")]
    if not effective:
        return None  # Caller should fall back to pure inferred

    counts = {level: sum(road["traffic_level"] == level for road in effective) for level in ("Light", "Moderate", "Heavy")}
    weights = [1.35 if road.get("road_type") == "arterial" else 1.0 for road in effective]
    average = sum(road["traffic_score"] * weight for road, weight in zip(effective, weights) if road.get("traffic_score") is not None) / sum(weights)
    health = round(max(0.0, min(100.0, 100.0 - average)), 1)
    hotspots = _rank_hotspots(roads, 8)
    best = _rank_best(roads, 8)
    coverage = _coverage(roads)
    mode_label = _traffic_mode_label(roads)
    if coverage["provider_coverage_percent"] == 100:
        traffic_source = "Real-Time Traffic"
        response_mode = "real"
    elif coverage["provider_coverage_percent"] > 0:
        traffic_source = "Mixed Traffic Data"
        response_mode = "hybrid"
    else:
        traffic_source = "Inferred Traffic"
        response_mode = "inferred"
    return {
        **snapshot,
        "status": "ok",
        "available": True,
        "source": "hybrid",
        "model_type": "hybrid",
        "mode": response_mode,
        "traffic_source": traffic_source,
        "traffic_mode_label": mode_label,
        "snapshot_time": snapshot.get("yangon_local_time"),
        "generated_at": snapshot.get("yangon_local_time"),
        "traffic_health_score": health,
        "traffic_health_label": traffic_health_label(health),
        "total_roads": len(roads),
        "light_count": counts["Light"],
        "moderate_count": counts["Moderate"],
        "heavy_count": counts["Heavy"],
        "critical_count": sum(road.get("critical_congestion", False) for road in effective),
        "average_traffic_score": round(sum(road["traffic_score"] for road in effective if road.get("traffic_score") is not None) / len(effective), 1),
        "hotspots": hotspots,
        "most_congested": hotspots[:5],
        "best_flowing": best[:5],
        "trend_type": "provider_snapshot",
        "roads": roads,
        **coverage,
    }


# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------

class TrafficBackend:
    def __init__(self, real_service=None, simulation_engine=None):
        self.real_service = real_service or HERE_FLOW_SERVICE
        self.simulation_engine = simulation_engine or TRAFFIC_ENGINE

    def overview(self, force=False):
        mode = traffic_mode()
        now = yangon_now()

        # Pure simulation mode
        if mode == "simulation":
            return _inferred_overview(self.simulation_engine, now, force=force)

        # Try HERE provider
        try:
            snapshot = self.real_service.refresh(force=force)
            result = _real_overview(snapshot, now, self.simulation_engine)
            if result is not None:
                return result
            # HERE returned data but nothing matched — fall through to inferred
        except HereFlowUnavailable:
            pass

        # All modes except pure simulation fall back to inferred traffic
        # (real, real_with_simulation_fallback, and unrecognised modes)
        try:
            return _inferred_overview(self.simulation_engine, now, force=force)
        except Exception:
            return _unknown_overview(now)

    def road(self, road_id, force=False):
        if road_id not in ROAD_REPOSITORY.by_id:
            return {"error": "Unknown road ID.", "error_details": {"code": "unknown_road", "message": "Unknown road ID."}}
        overview = self.overview(force=force)
        for road in overview.get("roads", []):
            if road["road_id"] == road_id:
                return {
                    "mode": overview["mode"],
                    "traffic_source": overview["traffic_source"],
                    "provider_updated_at": overview.get("provider_updated_at"),
                    "yangon_local_time": overview.get("yangon_local_time"),
                    **deepcopy(road),
                }
        road = ROAD_REPOSITORY.by_id[road_id]
        return {
            "mode": overview.get("mode", "inferred"),
            "traffic_source": "Inferred Traffic",
            "provider_updated_at": None,
            "yangon_local_time": overview.get("yangon_local_time"),
            "road_id": road.id,
            "road_name": road.road_name,
            "traffic_level": "Unknown",
            "matched": False,
            "status": "inferred_unavailable",
        }

    def hotspots(self, limit=8, force=False):
        overview = self.overview(force=force)
        return {
            "mode": overview["mode"],
            "traffic_source": overview["traffic_source"],
            "traffic_mode_label": overview.get("traffic_mode_label"),
            "source": overview.get("source"),
            "provider_updated_at": overview.get("provider_updated_at"),
            "yangon_local_time": overview.get("yangon_local_time"),
            "status": overview["status"],
            "message": overview.get("message"),
            "hotspots": (overview.get("hotspots") or [])[:limit],
        }

    def best_flowing(self, limit=8, force=False):
        overview = self.overview(force=force)
        return {
            "mode": overview["mode"],
            "traffic_source": overview["traffic_source"],
            "traffic_mode_label": overview.get("traffic_mode_label"),
            "source": overview.get("source"),
            "provider_updated_at": overview.get("provider_updated_at"),
            "yangon_local_time": overview.get("yangon_local_time"),
            "status": overview["status"],
            "message": overview.get("message"),
            "roads": (overview.get("best_flowing") or [])[:limit],
        }


TRAFFIC_BACKEND = TrafficBackend()
