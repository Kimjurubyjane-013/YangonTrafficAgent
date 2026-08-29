"""Mode-aware traffic facade used by desktop and HTTP APIs."""
from __future__ import annotations

from copy import deepcopy

from app.runtime_config import traffic_mode, yangon_now
from services.here_flow_service import HERE_FLOW_SERVICE, HereFlowUnavailable
from services.road_repository import ROAD_REPOSITORY
from services.traffic_service import TRAFFIC_ENGINE, get_time_period, is_rush_hour, traffic_health_label


def _unavailable(message):
    now = yangon_now()
    return {
        "mode": "real", "available": False, "status": "unavailable",
        "traffic_source": "unavailable", "source": "unavailable",
        "provider_updated_at": None, "yangon_local_time": now.isoformat(timespec="seconds"),
        "snapshot_time": now.isoformat(timespec="seconds"),
        "time_period": get_time_period(now), "rush_hour": is_rush_hour(now),
        "message": message, "total_roads": len(ROAD_REPOSITORY.roads),
        "matched_road_count": 0, "flow_record_count": 0,
        "traffic_health_score": None, "traffic_health_label": "Unavailable",
        "light_count": None, "moderate_count": None, "heavy_count": None,
        "critical_count": None, "average_traffic_score": None,
        "hotspots": [], "most_congested": [], "best_flowing": [], "roads": [],
        "trend_type": "unavailable",
    }


def _rank_hotspots(roads, limit):
    available = [road for road in roads if road.get("matched")]
    available.sort(key=lambda road: (-(road.get("traffic_impact") or 0), -(road.get("traffic_score") or 0), road["road_id"]))
    return available[:limit]


def _rank_best(roads, limit):
    available = [road for road in roads if road.get("matched")]
    available.sort(key=lambda road: (road.get("traffic_score") if road.get("traffic_score") is not None else 101, -(road.get("average_speed_kmh") or 0), road["road_id"]))
    return available[:limit]


def _real_overview(snapshot):
    roads = snapshot["roads"]
    available = [road for road in roads if road.get("matched")]
    if not available:
        return _unavailable("Real-time traffic data could not be matched to the modeled Yangon roads.")
    counts = {level: sum(road["traffic_level"] == level for road in available) for level in ("Light", "Moderate", "Heavy")}
    weights = [1.35 if road["road_type"] == "arterial" else 1.0 for road in available]
    average = sum(road["traffic_score"] * weight for road, weight in zip(available, weights)) / sum(weights)
    health = round(max(0.0, min(100.0, 100.0 - average)), 1)
    hotspots = _rank_hotspots(roads, 8)
    best = _rank_best(roads, 8)
    return {
        **snapshot, "status": "ok", "source": "here-traffic", "model_type": "real",
        "snapshot_time": snapshot.get("yangon_local_time"), "generated_at": snapshot.get("yangon_local_time"),
        "traffic_health_score": health, "traffic_health_label": traffic_health_label(health),
        "total_roads": len(roads), "light_count": counts["Light"],
        "moderate_count": counts["Moderate"], "heavy_count": counts["Heavy"],
        "critical_count": sum(road.get("critical_congestion", False) for road in available),
        "average_traffic_score": round(sum(road["traffic_score"] for road in available) / len(available), 1),
        "hotspots": hotspots, "most_congested": hotspots[:5], "best_flowing": best,
        "trend_type": "provider_snapshot",
    }


def _simulation_overview(engine, force=False, fallback=False):
    result = engine.overview(force=force)
    result.update({
        "mode": "simulation", "available": True, "status": "ok",
        "traffic_source": "Academic Simulation", "provider_updated_at": None,
        "yangon_local_time": result["generated_at"],
        "fallback_active": fallback,
    })
    return result


class TrafficBackend:
    def __init__(self, real_service=None, simulation_engine=None):
        self.real_service = real_service or HERE_FLOW_SERVICE
        self.simulation_engine = simulation_engine or TRAFFIC_ENGINE

    def overview(self, force=False):
        mode = traffic_mode()
        if mode == "simulation":
            return _simulation_overview(self.simulation_engine, force=force)
        try:
            return _real_overview(self.real_service.refresh(force=force))
        except HereFlowUnavailable as exc:
            if mode == "real_with_simulation_fallback":
                return _simulation_overview(self.simulation_engine, force=force, fallback=True)
            return _unavailable(str(exc))

    def road(self, road_id, force=False):
        if road_id not in ROAD_REPOSITORY.by_id:
            return {"error": "Unknown road ID.", "error_details": {"code": "unknown_road", "message": "Unknown road ID."}}
        overview = self.overview(force=force)
        for road in overview.get("roads", []):
            if road["road_id"] == road_id:
                return {
                    "mode": overview["mode"], "traffic_source": overview["traffic_source"],
                    "provider_updated_at": overview.get("provider_updated_at"),
                    "yangon_local_time": overview.get("yangon_local_time"), **deepcopy(road),
                }
        if overview["mode"] == "real":
            road = ROAD_REPOSITORY.by_id[road_id]
            return {
                "mode": "real", "traffic_source": "unavailable", "provider_updated_at": None,
                "yangon_local_time": overview["yangon_local_time"], "road_id": road.id,
                "road_name": road.road_name, "traffic_level": "Unavailable", "matched": False,
                "status": "unavailable", "message": overview.get("message"),
            }
        return {"error": "Traffic data is unavailable.", "error_details": {"code": "traffic_unavailable", "message": "Traffic data is unavailable."}}

    def hotspots(self, limit=8, force=False):
        overview = self.overview(force=force)
        return {
            "mode": overview["mode"], "traffic_source": overview["traffic_source"],
            "source": overview.get("source"),
            "provider_updated_at": overview.get("provider_updated_at"),
            "yangon_local_time": overview.get("yangon_local_time"),
            "status": overview["status"], "message": overview.get("message"),
            "hotspots": (overview.get("hotspots") or [])[:limit],
        }

    def best_flowing(self, limit=8, force=False):
        overview = self.overview(force=force)
        return {
            "mode": overview["mode"], "traffic_source": overview["traffic_source"],
            "source": overview.get("source"),
            "provider_updated_at": overview.get("provider_updated_at"),
            "yangon_local_time": overview.get("yangon_local_time"),
            "status": overview["status"], "message": overview.get("message"),
            "roads": (overview.get("best_flowing") or [])[:limit],
        }


TRAFFIC_BACKEND = TrafficBackend()
