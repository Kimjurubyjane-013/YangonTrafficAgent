"""HERE Traffic API v7 flow snapshots mapped to the modeled Yangon roads."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
import os
from threading import RLock
import time

import requests

from app.runtime_config import traffic_cache_seconds, yangon_now
from app.traffic_config import ROAD_IMPORTANCE
from services.road_repository import ROAD_REPOSITORY, RoadRepository
from services.traffic_service import get_time_period, is_rush_hour, traffic_health_label


HERE_FLOW_URL = "https://data.traffic.hereapi.com/v7/flow"
YANGON_BBOX_PADDING_DEGREES = 0.015
MAX_MATCH_DISTANCE_KM = 0.40
MAX_HEADING_DIFFERENCE_DEGREES = 55.0


class HereFlowUnavailable(RuntimeError):
    pass


def classify_provider_flow(jam_factor, current_speed, free_flow_speed, traversability="open") -> str | None:
    """Convert HERE flow to the public three-level scale.

    HERE jam factor uses a 0-10 congestion scale. We classify Heavy at 8+
    (or <=35% of free flow), Moderate at 4+ (or <=70% of free flow), and
    otherwise Light. A closed/non-traversable segment is Heavy. Missing usable
    provider evidence remains unavailable rather than defaulting to Moderate.
    """
    if str(traversability or "open").lower() not in {"open", "unknown"}:
        return "Heavy"
    try:
        jam = float(jam_factor)
    except (TypeError, ValueError):
        jam = None
    try:
        speed = float(current_speed)
        free_flow = float(free_flow_speed)
        ratio = speed / free_flow if free_flow > 0 else None
    except (TypeError, ValueError):
        ratio = None
    if jam is None and ratio is None:
        return None
    if (jam is not None and jam >= 8.0) or (ratio is not None and ratio <= 0.35):
        return "Heavy"
    if (jam is not None and jam >= 4.0) or (ratio is not None and ratio <= 0.70):
        return "Moderate"
    return "Light"


def _km(a, b):
    latitude = math.radians((a[0] + b[0]) / 2)
    return math.hypot((a[0] - b[0]) * 111.0, (a[1] - b[1]) * 111.0 * math.cos(latitude))


def _xy(point, origin):
    latitude = math.radians(origin[0])
    return ((point[1] - origin[1]) * 111.0 * math.cos(latitude), (point[0] - origin[0]) * 111.0)


def _point_segment_distance(point, start, end):
    px, py = _xy(point, start)
    ex, ey = _xy(end, start)
    length_sq = ex * ex + ey * ey
    if length_sq <= 1e-12:
        return math.hypot(px, py)
    fraction = max(0.0, min(1.0, (px * ex + py * ey) / length_sq))
    return math.hypot(px - fraction * ex, py - fraction * ey)


def _heading(start, end):
    x, y = _xy(end, start)
    return math.degrees(math.atan2(y, x)) % 180.0


def _heading_difference(first, second):
    difference = abs(first - second) % 180.0
    return min(difference, 180.0 - difference)


def _shape_points(location):
    points = []
    for link in (location.get("shape") or {}).get("links", []):
        for point in link.get("points", []):
            try:
                coordinate = (float(point["lat"]), float(point["lng"]))
            except (KeyError, TypeError, ValueError):
                continue
            if not points or coordinate != points[-1]:
                points.append(coordinate)
    return points


def _observations(payload):
    observations = []
    for result in payload.get("results", []):
        location = result.get("location") or {}
        flow = result.get("currentFlow") or {}
        points = _shape_points(location)
        level = classify_provider_flow(
            flow.get("jamFactor"), flow.get("speed"), flow.get("freeFlow"), flow.get("traversability")
        )
        if len(points) < 2 or level is None:
            continue
        observations.append({
            "points": points, "level": level,
            "speed_mps": _number(flow.get("speed")),
            "free_flow_mps": _number(flow.get("freeFlow")),
            "jam_factor": _number(flow.get("jamFactor")),
            "confidence": _number(flow.get("confidence")),
            "description": str(location.get("description") or "").strip(),
        })
    return observations


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _observation_distance(road_start, road_end, observation):
    points = observation["points"]
    provider_heading = _heading(points[0], points[-1])
    if _heading_difference(_heading(road_start, road_end), provider_heading) > MAX_HEADING_DIFFERENCE_DEGREES:
        return None
    midpoint = ((road_start[0] + road_end[0]) / 2, (road_start[1] + road_end[1]) / 2)
    distances = [_point_segment_distance(point, road_start, road_end) for point in points]
    provider_distances = [
        _point_segment_distance(midpoint, start, end)
        for start, end in zip(points, points[1:])
    ]
    return min(min(distances), min(provider_distances))


def _level_score(level):
    return {"Light": 20.0, "Moderate": 55.0, "Heavy": 85.0}[level]


class HereFlowTrafficService:
    def __init__(self, repository: RoadRepository | None = None, request_get=None, clock=None):
        self.repository = repository or ROAD_REPOSITORY
        self._request_get = request_get or requests.get
        self._clock = clock or time.monotonic
        self._lock = RLock()
        self._cached = None
        self._cached_at = 0.0

    def _bbox(self):
        latitudes = [point[0] for point in self.repository.locations.values()]
        longitudes = [point[1] for point in self.repository.locations.values()]
        return (
            min(longitudes) - YANGON_BBOX_PADDING_DEGREES,
            min(latitudes) - YANGON_BBOX_PADDING_DEGREES,
            max(longitudes) + YANGON_BBOX_PADDING_DEGREES,
            max(latitudes) + YANGON_BBOX_PADDING_DEGREES,
        )

    def refresh(self, force=False):
        now = self._clock()
        with self._lock:
            if not force and self._cached is not None and now - self._cached_at < traffic_cache_seconds():
                return deepcopy(self._cached)
        snapshot = self._fetch()
        with self._lock:
            self._cached, self._cached_at = deepcopy(snapshot), self._clock()
        return snapshot

    def _fetch(self):
        key = os.getenv("HERE_API_KEY", "").strip()
        if not key:
            raise HereFlowUnavailable("HERE_API_KEY is not configured.")
        west, south, east, north = self._bbox()
        try:
            response = self._request_get(HERE_FLOW_URL, params={
                "apiKey": key,
                "in": f"bbox:{west:.6f},{south:.6f},{east:.6f},{north:.6f}",
                "locationReferencing": "shape",
            }, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError, TypeError) as exc:
            raise HereFlowUnavailable("HERE real-time flow could not be retrieved.") from exc
        observations = _observations(payload)
        if not observations:
            raise HereFlowUnavailable("HERE returned no usable real-time flow for Yangon.")
        local_now = yangon_now()
        provider_updated_at = payload.get("sourceUpdated")
        roads = [self._map_road(road, observations, local_now) for road in self.repository.roads]
        for road in roads:
            if road["matched"]:
                road["provider_updated_at"] = provider_updated_at
        matched = [road for road in roads if road["matched"]]
        return {
            "mode": "real", "available": bool(matched), "traffic_source": "HERE",
            "provider_updated_at": provider_updated_at,
            "yangon_local_time": local_now.isoformat(timespec="seconds"),
            "time_period": get_time_period(local_now), "rush_hour": is_rush_hour(local_now),
            "flow_record_count": len(observations), "matched_road_count": len(matched),
            "roads": roads,
        }

    def _map_road(self, road, observations, local_now):
        start, end = self.repository.locations[road.start], self.repository.locations[road.end]
        matches = []
        for observation in observations:
            distance = _observation_distance(start, end, observation)
            if distance is not None and distance <= MAX_MATCH_DISTANCE_KM:
                matches.append((distance, observation))
        base = {
            "road_id": road.id, "road_name": road.road_name, "road_type": road.road_type,
            "start": road.start, "end": road.end, "coordinates": [list(start), list(end)],
            "time_period": get_time_period(local_now), "rush_hour": is_rush_hour(local_now),
            "source": "HERE", "traffic_source": "HERE", "matched": False,
            "provider_match_distance_km": None, "provider_updated_at": None,
            "traffic_level": "Unavailable", "traffic_score": None,
            "average_speed_kmh": None, "free_flow_speed_kmh": None,
            "jam_factor": None, "estimated_delay_minutes": None,
            "traffic_impact": None, "critical_congestion": False,
            "vehicle_density": None, "congestion_pressure": None,
            "score_change": None, "trend": "unavailable", "reasons": [],
            "summary_reason": "No compatible HERE flow observation matched this modeled road.",
        }
        if not matches:
            return base
        matches.sort(key=lambda item: item[0])
        selected = matches[:8]
        weights = [1.0 / max(0.025, distance) for distance, _ in selected]
        def weighted(field):
            values = [(obs[field], weight) for weight, (_, obs) in zip(weights, selected) if obs[field] is not None]
            return sum(value * weight for value, weight in values) / sum(weight for _, weight in values) if values else None
        jam = weighted("jam_factor")
        speed = weighted("speed_mps")
        free_flow = weighted("free_flow_mps")
        level = classify_provider_flow(jam, speed, free_flow)
        if level is None:
            return base
        score_components = []
        if jam is not None:
            score_components.append(max(0.0, min(100.0, jam * 10.0)))
        if speed is not None and free_flow and free_flow > 0:
            score_components.append(max(0.0, min(100.0, (1.0 - speed / free_flow) * 100.0)))
        score = sum(score_components) / len(score_components) if score_components else _level_score(level)
        current_kmh = speed * 3.6 if speed is not None else None
        free_kmh = free_flow * 3.6 if free_flow is not None else None
        delay = None
        if current_kmh and free_kmh and current_kmh > 0 and free_kmh > 0:
            delay = max(0.0, road.distance_km / current_kmh * 60 - road.distance_km / free_kmh * 60)
        base.update({
            "matched": True, "traffic_level": level, "traffic_score": round(score, 1),
            "average_speed_kmh": round(current_kmh, 1) if current_kmh is not None else None,
            "free_flow_speed_kmh": round(free_kmh, 1) if free_kmh is not None else None,
            "jam_factor": round(jam, 2) if jam is not None else None,
            "estimated_delay_minutes": round(delay, 2) if delay is not None else None,
            "traffic_impact": round(score * ROAD_IMPORTANCE[road.road_type], 1),
            "critical_congestion": level == "Heavy" and score >= 90,
            "provider_match_distance_km": round(selected[0][0], 3),
            "reasons": [f"HERE jam factor {jam:.1f}" if jam is not None else "HERE speed observation"],
            "summary_reason": f"{road.road_name} is {level} from matched HERE real-time flow.",
        })
        return base


HERE_FLOW_SERVICE = HereFlowTrafficService()
