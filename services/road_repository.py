"""Validated loader for the project's single road and location data sources."""
from __future__ import annotations

import json
import logging
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
        roads, ids = [], set()
        for index, item in enumerate(raw_roads):
            try:
                road = self._road(item, locations)
                if road.id in ids:
                    raise RoadDataError(f"Duplicate road id: {road.id}")
            except RoadDataError as exc:
                self._record_error(f"road[{index}]: {exc}")
                continue
            ids.add(road.id); roads.append(road)
        if not roads:
            raise RoadDataError("No valid road segments are available.")
        return locations, tuple(roads)

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
            road = RoadSegment(
                id=str(item["id"]).strip(), start=start, end=end,
                road_name=str(item["road_name"]).strip(), road_type=road_type,
                distance_km=float(item["distance_km"]),
                base_speed_kmh=float(item.get("base_speed_kmh", defaults.typical_speed_kmh)),
                base_congestion=float(item["base_congestion"]),
                capacity=int(item.get("capacity", defaults.capacity)),
                bidirectional=bool(item.get("bidirectional", True)),
                preferred=bool(item.get("preferred", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RoadDataError("Malformed road segment data.") from exc
        if not road.id or not road.road_name or start == end or start not in locations or end not in locations:
            raise RoadDataError(f"Road {road.id or '<missing>'} has invalid endpoints or names.")
        if road.distance_km <= 0 or road.base_speed_kmh <= 0 or not 0 <= road.base_congestion <= 100 or road.capacity <= 0:
            raise RoadDataError(f"Road {road.id} contains out-of-range numeric data.")
        return road


ROAD_REPOSITORY = RoadRepository()
