"""Deterministic, explainable traffic analysis for all modelled roads.

The values produced here are academic simulation parameters, not live traffic
measurements. A time-bucketed snapshot keeps the dashboard, routing, map, and
simulation consistent during the same traffic state.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from threading import RLock

from algorithms.route_finder import find_all_simple_paths
from app.models import RoadTrafficState, TrafficSnapshot
from app.traffic_config import (
    BASE_CONGESTION_WEIGHT, CAPACITY_DENSITY_WEIGHT,
    DETERMINISTIC_VARIATION_LIMIT, MINIMUM_TRAFFIC_SPEED_KMH,
    ROAD_TYPES, RUSH_HOUR_PERIODS, RUSH_HOUR_SCORE_EFFECT,
    SNAPSHOT_MINUTES, TIME_DENSITY_EFFECT, TIME_PERIODS,
    TIME_SCORE_EFFECT, TRAFFIC_SPEED_MULTIPLIERS,
    VEHICLE_DENSITY_WEIGHT,
)
from services.road_repository import ROAD_REPOSITORY, RoadRepository


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def get_time_period(value: datetime | None = None) -> str:
    current = (value or datetime.now()).time()
    for name, start, end in TIME_PERIODS:
        if start < end and start <= current < end:
            return name
        if start > end and (current >= start or current < end):
            return name
    return "NIGHT"


def is_rush_hour(value: datetime | None = None) -> bool:
    return get_time_period(value) in RUSH_HOUR_PERIODS


def classify_traffic(score: float) -> str:
    score = clamp(score)
    if score <= 35:
        return "Light"
    if score <= 70:
        return "Moderate"
    return "Heavy"


def _road_name_key(value: str) -> str:
    text = str(value).casefold()
    text = re.sub(r"\brd\b", "road", text)
    text = re.sub(r"\bst\b", "street", text)
    text = re.sub(r"\bave\b", "avenue", text)
    return "".join(re.findall(r"[a-z0-9]+", text))


class TrafficEngine:
    def __init__(self, repository: RoadRepository | None = None):
        self.repository = repository or ROAD_REPOSITORY
        self._lock = RLock()
        self._snapshots: dict[str, TrafficSnapshot] = {}

    @staticmethod
    def _snapshot_key(at: datetime) -> str:
        minute = at.minute - at.minute % SNAPSHOT_MINUTES
        return at.replace(minute=minute, second=0, microsecond=0).isoformat(timespec="minutes")

    def get_snapshot(self, at: datetime | None = None, force: bool = False) -> TrafficSnapshot:
        at = at or datetime.now()
        key = self._snapshot_key(at)
        with self._lock:
            if not force and key in self._snapshots:
                return self._snapshots[key]
            period = get_time_period(at)
            states = {road.id: self.analyze_road(road.id, at, key) for road in self.repository.roads}
            snapshot = TrafficSnapshot(
                snapshot_id=key, generated_at=at.isoformat(timespec="seconds"),
                time_period=period, rush_hour=period in RUSH_HOUR_PERIODS,
                roads=states,
            )
            self._snapshots = {key: snapshot}
            return snapshot

    def analyze_road(self, road_id: str, at: datetime | None = None, snapshot_key: str | None = None) -> RoadTrafficState:
        road = self.repository.by_id.get(str(road_id))
        if road is None:
            raise KeyError(f"Unknown road id: {road_id}")
        at = at or datetime.now()
        period = get_time_period(at)
        rush = period in RUSH_HOUR_PERIODS
        defaults = ROAD_TYPES[road.road_type]
        key = snapshot_key or self._snapshot_key(at)
        digest = hashlib.sha256(f"{road.id}|{key}".encode("utf-8")).digest()
        normalized = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
        variation = (normalized * 2 - 1) * DETERMINISTIC_VARIATION_LIMIT
        capacity_pressure = max(0.0, 100.0 - road.capacity) * CAPACITY_DENSITY_WEIGHT
        density = clamp(
            road.base_congestion
            + TIME_DENSITY_EFFECT[period] * defaults.congestion_sensitivity
            + capacity_pressure + variation
        )
        score = clamp(
            road.base_congestion * BASE_CONGESTION_WEIGHT
            + density * VEHICLE_DENSITY_WEIGHT
            + TIME_SCORE_EFFECT[period]
            + (RUSH_HOUR_SCORE_EFFECT if rush else 0.0)
            + defaults.score_effect
        )
        level = classify_traffic(score)
        average_speed = max(
            MINIMUM_TRAFFIC_SPEED_KMH,
            road.base_speed_kmh * TRAFFIC_SPEED_MULTIPLIERS[level],
        )
        free_flow_minutes = road.distance_km / road.base_speed_kmh * 60.0
        congested_minutes = road.distance_km / average_speed * 60.0
        delay = max(0.0, congested_minutes - free_flow_minutes)
        reasons = self._reasons(road, period, rush, density, level, variation)
        return RoadTrafficState(
            road_id=road.id, road_name=road.road_name, road_type=road.road_type,
            start=road.start, end=road.end,
            coordinates=(self.repository.locations[road.start], self.repository.locations[road.end]),
            traffic_score=round(score, 1), traffic_level=level,
            average_speed_kmh=round(average_speed, 1), vehicle_density=round(density, 1),
            estimated_delay_minutes=round(delay, 2), time_period=period,
            rush_hour=rush, reasons=tuple(reasons),
        )

    @staticmethod
    def _reasons(road, period, rush, density, level, variation):
        reasons = []
        if rush:
            reasons.append("Morning rush-hour demand" if period == "MORNING_RUSH" else "Evening rush-hour demand")
        elif period == "NIGHT":
            reasons.append("Lower night-time demand")
        elif period == "EARLY_MORNING":
            reasons.append("Lower early-morning demand")
        else:
            reasons.append("Normal daytime demand")
        if road.base_congestion >= 70:
            reasons.append("High modelled baseline congestion")
        elif road.base_congestion <= 40:
            reasons.append("Low modelled baseline congestion")
        if density >= 71:
            reasons.append("High simulated vehicle density")
        elif density <= 35:
            reasons.append("Low simulated vehicle density")
        if road.road_type == "arterial":
            reasons.append("Arterial-road demand")
        elif road.road_type == "local":
            reasons.append("Lower-capacity local road")
        if abs(variation) >= 2.5:
            reasons.append("Repeatable local demand variation")
        if level == "Heavy" and not any("High" in reason for reason in reasons):
            reasons.append("Combined demand exceeds heavy-traffic threshold")
        return reasons

    def overview(self, at: datetime | None = None) -> dict:
        snapshot = self.get_snapshot(at)
        roads = [state.as_dict() for state in snapshot.roads.values()]
        counts = {level: sum(state.traffic_level == level for state in snapshot.roads.values()) for level in ("Light", "Moderate", "Heavy")}
        descending = sorted(roads, key=lambda item: (-item["traffic_score"], item["road_id"]))
        ascending = sorted(roads, key=lambda item: (item["traffic_score"], item["road_id"]))
        average = sum(item["traffic_score"] for item in roads) / len(roads) if roads else 0.0
        return {
            "snapshot_id": snapshot.snapshot_id, "generated_at": snapshot.generated_at,
            "time_period": snapshot.time_period, "rush_hour": snapshot.rush_hour,
            "model_type": "academic_simulation", "total_roads": len(roads),
            "light_count": counts["Light"], "moderate_count": counts["Moderate"],
            "heavy_count": counts["Heavy"], "average_traffic_score": round(average, 1),
            "most_congested": descending[:5], "best_flowing": ascending[:5], "roads": roads,
        }

    def route_state(self, start: str, destination: str, road_names=(), snapshot: TrafficSnapshot | None = None) -> dict:
        snapshot = snapshot or self.get_snapshot()
        paths = find_all_simple_paths(self._graph(), start, destination, max_depth=len(self.repository.locations), max_candidates=32)
        path = min(paths, key=lambda item: (item[1], tuple(item[0])))[0] if paths else [start, destination]
        states = []
        for a, b in zip(path, path[1:]):
            road = self.repository.by_edge.get((a, b))
            if road and road.id in snapshot.roads:
                states.append(snapshot.roads[road.id])
        requested_names = {_road_name_key(name) for name in road_names if name}
        named = [state for state in snapshot.roads.values() if _road_name_key(state.road_name) in requested_names]
        if named:
            states = named
        if not states:
            return {"traffic_level":"Moderate","segment_traffic":["Moderate"],"road_ids":[],"average_score":50.0,"estimated_delay_minutes":0.0,"snapshot_id":snapshot.snapshot_id}
        worst = max(states, key=lambda state: state.traffic_score).traffic_level
        return {
            "traffic_level": worst, "segment_traffic": [state.traffic_level for state in states],
            "road_ids": [state.road_id for state in states],
            "average_score": round(sum(state.traffic_score for state in states) / len(states), 1),
            "estimated_delay_minutes": round(sum(state.estimated_delay_minutes for state in states), 2),
            "snapshot_id": snapshot.snapshot_id,
        }

    def _graph(self):
        graph = {name: {} for name in self.repository.locations}
        for road in self.repository.roads:
            graph[road.start][road.end] = road.distance_km
            if road.bidirectional:
                graph[road.end][road.start] = road.distance_km
        return graph


TRAFFIC_ENGINE = TrafficEngine()
