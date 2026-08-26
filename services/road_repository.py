"""Validated loader for the project's single road and location data sources."""
from __future__ import annotations

import json
import logging
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT
from app.models import RoadSegment
from app.traffic_config import ROAD_TYPES

LOGGER = logging.getLogger(__name__)


class RoadDataError(ValueError):
    pass


class RoadRepository:
    def __init__(self, road_file: Path | None = None, location_file: Path | None = None):
        self.road_file = road_file or PROJECT_ROOT / "data" / "roads.json"
        self.location_file = location_file or PROJECT_ROOT / "data" / "locations.json"
        self.errors = []
        self.locations, self.roads = self._load()
        self.by_id = {road.id: road for road in self.roads}
        self.by_edge = {}
        for road in self.roads:
            self.by_edge[(road.start, road.end)] = road
            if road.bidirectional:
                self.by_edge[(road.end, road.start)] = road

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RoadDataError(f"Unable to load valid road data from {path.name}: {exc}") from exc

    def _load(self):
        raw_locations = self._read_json(self.location_file)
        raw_roads = self._read_json(self.road_file)
        if not isinstance(raw_locations, list) or not raw_locations:
            raise RoadDataError("Location data must be a non-empty list.")
        if not isinstance(raw_roads, list) or not raw_roads:
            raise RoadDataError("Road data must be a non-empty list.")
        locations = {}
        for index, item in enumerate(raw_locations):
            try:
                name = str(item["name"]).strip()
                lat, lon = float(item["lat"]), float(item["lon"])
                if not name or not (-90 <= lat <= 90 and -180 <= lon <= 180) or name in locations:
                    raise RoadDataError(f"Invalid or duplicate location: {name or '<blank>'}")
            except (KeyError, TypeError, ValueError, RoadDataError) as exc:
                self._record_error(f"location[{index}]: {exc}")
                continue
            locations[name] = (lat, lon)
        if not locations:
            raise RoadDataError("No valid locations are available.")
        roads, ids, directed_edges = [], set(), set()
        for index, item in enumerate(raw_roads):
            try:
                road = self._road(item, locations)
                if road.id in ids:
                    raise RoadDataError(f"Duplicate road id: {road.id}")
                edge_keys = {(road.start, road.end)}
                if road.bidirectional:
                    edge_keys.add((road.end, road.start))
                if directed_edges.intersection(edge_keys):
                    raise RoadDataError(f"Duplicate road connection: {road.start} -> {road.end}")
            except RoadDataError as exc:
                self._record_error(f"road[{index}]: {exc}")
                continue
            ids.add(road.id); directed_edges.update(edge_keys); roads.append(road)
        if not roads:
            raise RoadDataError("No valid road segments are available.")
        self._validate_connected(locations, roads)
        return locations, tuple(roads)

    @staticmethod
    def _validate_connected(locations, roads):
        adjacency = {name: set() for name in locations}
        for road in roads:
            adjacency[road.start].add(road.end)
            adjacency[road.end].add(road.start)
        pending = [next(iter(locations))]
        visited = set()
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            pending.extend(adjacency[node] - visited)
        missing = sorted(set(locations) - visited)
        if missing:
            raise RoadDataError(f"Road network is disconnected: {', '.join(missing)}")

    def _record_error(self, message):
        self.errors.append(message)
        LOGGER.warning("Skipping malformed traffic-model data: %s", message)

    @staticmethod
    def _road(item, locations):
        if not isinstance(item, dict):
            raise RoadDataError("Every road must be an object.")
        road_type = str(item.get("road_type", "")).strip().lower()
        if road_type not in ROAD_TYPES:
            raise RoadDataError(f"Unknown road type: {road_type or '<missing>'}")
        defaults = ROAD_TYPES[road_type]
        try:
            start, end = str(item["from"]).strip(), str(item["to"]).strip()
            raw_bidirectional = item.get("bidirectional", True)
            raw_preferred = item.get("preferred", False)
            if not isinstance(raw_bidirectional, bool) or not isinstance(raw_preferred, bool):
                raise RoadDataError("Road direction and preference flags must be boolean values.")
            road = RoadSegment(
                id=str(item["id"]).strip(), start=start, end=end,
                road_name=str(item["road_name"]).strip(), road_type=road_type,
                distance_km=float(item["distance_km"]),
                base_speed_kmh=float(item.get("base_speed_kmh", defaults.typical_speed_kmh)),
                base_congestion=float(item["base_congestion"]),
                capacity=int(item.get("capacity", defaults.capacity)),
                bidirectional=raw_bidirectional,
                preferred=raw_preferred,
                commercial_activity=float(item.get("commercial_activity", 0.0)),
                junction_complexity=float(item.get("junction_complexity", 0.0)),
                rush_hour_sensitivity=float(item.get("rush_hour_sensitivity", 1.0)),
                downtown_factor=float(item.get("downtown_factor", 0.0)),
                school_university_factor=float(item.get("school_university_factor", 0.0)),
                airport_corridor_factor=float(item.get("airport_corridor_factor", 0.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RoadDataError("Malformed road segment data.") from exc
        if not road.id or not road.road_name or start == end or start not in locations or end not in locations:
            raise RoadDataError(f"Road {road.id or '<missing>'} has invalid endpoints or names.")
        if road.distance_km <= 0 or road.base_speed_kmh <= 0 or not 0 <= road.base_congestion <= 100 or road.capacity <= 0:
            raise RoadDataError(f"Road {road.id} contains out-of-range numeric data.")
        straight_line_km = RoadRepository._distance_km(locations[start], locations[end])
        if road.distance_km < straight_line_km * 0.95:
            raise RoadDataError(f"Road {road.id} is shorter than its geographic endpoints allow.")
        if road.distance_km > max(2.0, straight_line_km * 6.0):
            raise RoadDataError(f"Road {road.id} is an implausible direct connection.")
        context_values = (
            road.commercial_activity, road.junction_complexity, road.downtown_factor,
            road.school_university_factor, road.airport_corridor_factor,
        )
        if any(not 0 <= value <= 1 for value in context_values) or not 0.5 <= road.rush_hour_sensitivity <= 2:
            raise RoadDataError(f"Road {road.id} contains invalid context factors.")
        return road

    @staticmethod
    def _distance_km(start, end):
        lat1, lon1 = map(radians, start)
        lat2, lon2 = map(radians, end)
        delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
        value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        return 6371.0 * 2 * asin(sqrt(value))


ROAD_REPOSITORY = RoadRepository()
