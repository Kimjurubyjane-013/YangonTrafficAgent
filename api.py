"""Validated pywebview API surface."""
import logging
from threading import RLock

from algorithms.graph import GRAPH, LOCATION_COORDS, get_locations
from algorithms.vehicle import VEHICLE_SPEED
from app.serialization import serialize_route_result
from app.validation import validate_route_request
from services.route_service import RouteService
from services.road_repository import ROAD_REPOSITORY
from services.traffic_service import TRAFFIC_ENGINE
from services.traffic_backend import TRAFFIC_BACKEND
from services.traffic_prediction import predict_traffic, prediction_series

LOGGER = logging.getLogger(__name__)


class Api:
    def __init__(self, route_service=None, traffic_engine=None, traffic_backend=None):
        self._last_result = None
        self._lock = RLock()
        self._traffic_engine = traffic_engine or TRAFFIC_ENGINE
        self._traffic_backend = traffic_backend or (None if traffic_engine is not None else TRAFFIC_BACKEND)
        self._route_service = route_service or RouteService(self._traffic_engine)

    def get_locations(self):
        return get_locations()

    def get_vehicles(self):
        return list(VEHICLE_SPEED)[:6]

    def get_graph_data(self):
        seen, edges = set(), []
        for start, neighbors in GRAPH.items():
            for end in neighbors:
                pair = tuple(sorted((start, end)))
                if pair not in seen:
                    seen.add(pair); edges.append([start, end])
        roads = [{
            "id": road.id, "road_name": road.road_name, "from": road.start, "to": road.end,
            "road_type": road.road_type, "distance_km": road.distance_km,
            "bidirectional": road.bidirectional,
            "context": {
                "commercial_activity": road.commercial_activity,
                "junction_complexity": road.junction_complexity,
                "rush_hour_sensitivity": road.rush_hour_sensitivity,
                "downtown_factor": road.downtown_factor,
                "school_university_factor": road.school_university_factor,
                "airport_corridor_factor": road.airport_corridor_factor,
            },
            "coordinates": [list(LOCATION_COORDS[road.start]), list(LOCATION_COORDS[road.end])],
        } for road in ROAD_REPOSITORY.roads]
        return {"coords": {name: list(coord) for name, coord in LOCATION_COORDS.items()}, "edges": edges, "roads": roads}

    @staticmethod
    def _validated_limit(limit, default=8, maximum=25):
        try:
            return max(1, min(maximum, int(limit)))
        except (TypeError, ValueError):
            return default

    def get_congestion_hotspots(self, limit=8):
        try:
            if self._traffic_backend is not None:
                return self._traffic_backend.hotspots(self._validated_limit(limit))
            snapshot = self._traffic_engine.get_snapshot()
            return {
                "snapshot_id": snapshot.snapshot_id,
                "source": "academic_simulation",
                "hotspots": self._traffic_engine.congestion_hotspots(
                    snapshot, self._validated_limit(limit)
                ),
            }
        except Exception:
            LOGGER.exception("Traffic hotspot analysis failed")
            return {"error": "Traffic hotspot analysis is temporarily unavailable.", "error_details": {"code": "traffic_analysis_error", "message": "Traffic hotspot analysis is temporarily unavailable."}}

    def get_best_flowing_roads(self, limit=8):
        try:
            if self._traffic_backend is not None:
                return self._traffic_backend.best_flowing(self._validated_limit(limit))
            snapshot = self._traffic_engine.get_snapshot()
            return {
                "snapshot_id": snapshot.snapshot_id,
                "source": "academic_simulation",
                "roads": self._traffic_engine.best_flowing_roads(
                    snapshot, self._validated_limit(limit)
                ),
            }
        except Exception:
            LOGGER.exception("Best-flow analysis failed")
            return {"error": "Best-flow analysis is temporarily unavailable.", "error_details": {"code": "traffic_analysis_error", "message": "Best-flow analysis is temporarily unavailable."}}

    def get_traffic_overview(self, force=False):
        try:
            if self._traffic_backend is not None:
                return self._traffic_backend.overview(force=bool(force))
            return self._traffic_engine.overview(force=bool(force))
        except Exception:
            LOGGER.exception("Traffic overview failed")
            return {"error": "Traffic analysis is temporarily unavailable.", "error_details": {"code": "traffic_analysis_error", "message": "Traffic analysis is temporarily unavailable."}}

    def get_traffic_prediction(self, period=None):
        try:
            if period:
                return predict_traffic(str(period), engine=self._traffic_engine)
            return prediction_series(engine=self._traffic_engine)
        except ValueError as exc:
            return {"error": str(exc), "error_details": {"code": "invalid_prediction_period", "message": str(exc)}}
        except Exception:
            LOGGER.exception("Traffic prediction failed")
            return {"error": "Traffic prediction is temporarily unavailable.", "error_details": {"code": "prediction_error", "message": "Traffic prediction is temporarily unavailable."}}

    def get_road_traffic(self, road_id):
        if not isinstance(road_id, str) or not road_id.strip():
            return {"error": "Road ID must be a non-empty text value.", "error_details": {"code": "invalid_road_id", "message": "Road ID must be a non-empty text value."}}
        try:
            if self._traffic_backend is not None:
                return self._traffic_backend.road(road_id.strip())
            snapshot = self._traffic_engine.get_snapshot()
            state = snapshot.road(road_id.strip())
            if state is None:
                return {"error": "Unknown road ID.", "error_details": {"code": "unknown_road", "message": "Unknown road ID."}}
            return {"snapshot_id": snapshot.snapshot_id, "model_type": "academic_simulation", **state.as_dict()}
        except Exception:
            LOGGER.exception("Road traffic lookup failed")
            return {"error": "Road traffic analysis failed.", "error_details": {"code": "traffic_analysis_error", "message": "Road traffic analysis failed."}}

    def find_route(self, vehicle, start, destination, conditions=None):
        request, error = validate_route_request(vehicle, start, destination, conditions)
        if error:
            LOGGER.warning("Rejected route request: %s", error.code)
            return error.as_dict()
        try:
            raw = self._route_service.find(request)
            result = serialize_route_result(raw)
        except Exception:
            LOGGER.exception("Unhandled route request failure")
            result = {"error": "An internal routing error occurred.", "error_details": {"code": "internal_error", "message": "An internal routing error occurred."}}
        if not result.get("error"):
            with self._lock:
                self._last_result = result
        return result

    def compare_route_scenario(self, vehicle, start, destination, scenario_type, affected_road=None):
        allowed = {"accident", "heavy_rain", "rush_hour", "road_closed", "major_event"}
        if scenario_type not in allowed:
            message = "Unknown scenario type."
            return {"error": message, "error_details": {"code": "invalid_scenario", "message": message}}
        if scenario_type in {"accident", "road_closed"} and not affected_road:
            message = "Select an affected road for this scenario."
            return {"error": message, "error_details": {"code": "invalid_scenario", "message": message}}
        before = self.find_route(vehicle, start, destination, {"traffic_scenario": "current"})
        if before.get("error"):
            return before
        conditions = {"traffic_scenario": "current", "scenario_type": scenario_type}
        if affected_road:
            conditions["affected_road"] = affected_road
        after = self.find_route(vehicle, start, destination, conditions)
        if after.get("error"):
            return after
        return {
            "ok": True,
            "scenario_type": scenario_type,
            "scenario_label": "SIMULATED",
            "is_live": False,
            "affected_road": affected_road,
            "before": before,
            "after": after,
            "changes": {
                "recommended_route_changed": before.get("route_id") != after.get("route_id"),
                "eta_change_minutes": round(float(after["time"]) - float(before["time"]), 2),
                "traffic_before": before.get("traffic"),
                "traffic_after": after.get("traffic"),
                "rules_before": before.get("rules_fired", []),
                "rules_after": after.get("rules_fired", []),
            },
        }

    def get_last_result(self):
        with self._lock:
            return self._last_result
