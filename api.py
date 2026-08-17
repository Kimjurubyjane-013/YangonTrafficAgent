"""Validated pywebview API surface."""
import logging
from threading import RLock

from algorithms.graph import GRAPH, LOCATION_COORDS, get_locations
from algorithms.vehicle import VEHICLE_SPEED
from app.serialization import serialize_route_result
from app.validation import validate_route_request
from services.route_service import RouteService

LOGGER = logging.getLogger(__name__)


class Api:
    def __init__(self, route_service=None):
        self._last_result = None
        self._lock = RLock()
        self._route_service = route_service or RouteService()

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
        return {"coords": {name: list(coord) for name, coord in LOCATION_COORDS.items()}, "edges": edges}

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
