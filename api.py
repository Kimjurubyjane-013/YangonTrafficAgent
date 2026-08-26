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

LOGGER = logging.getLogger(__name__)


class Api:
    def __init__(self, route_service=None, traffic_engine=None):
        self._last_result = None
        self._lock = RLock()
        self._traffic_engine = traffic_engine or TRAFFIC_ENGINE
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
            "coordinates": [list(LOCATION_COORDS[road.start]), list(LOCATION_COORDS[road.end])],
        } for road in ROAD_REPOSITORY.roads]
        return {"coords": {name: list(coord) for name, coord in LOCATION_COORDS.items()}, "edges": edges, "roads": roads}

    def get_traffic_overview(self):
        try:
            return self._traffic_engine.overview()
        except Exception:
            LOGGER.exception("Traffic overview failed")
            return {"error": "Traffic analysis is temporarily unavailable.", "error_details": {"code": "traffic_analysis_error", "message": "Traffic analysis is temporarily unavailable."}}

    def get_road_traffic(self, road_id):
        if not isinstance(road_id, str) or not road_id.strip():
            return {"error": "Road ID must be a non-empty text value.", "error_details": {"code": "invalid_road_id", "message": "Road ID must be a non-empty text value."}}
        try:
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

    def get_last_result(self):
        with self._lock:
            return self._last_result
