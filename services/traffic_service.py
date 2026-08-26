"""Deterministic, explainable city-wide traffic intelligence.

All values are academic simulation outputs unless a route provider explicitly
reports otherwise. Stable 15-minute snapshots keep maps, routes, explanations,
and future Prolog facts internally consistent.
"""
from __future__ import annotations

import hashlib
import heapq
import re
from dataclasses import replace
from datetime import datetime, timedelta
from threading import RLock

from app.models import RoadTrafficState, TrafficSnapshot
from app.traffic_config import (
    BASE_CONGESTION_WEIGHT, BEST_FLOW_WEIGHTS, CAPACITY_DENSITY_WEIGHT,
    CONGESTION_PRESSURE_WEIGHT, CONTEXT_DENSITY_EFFECTS,
    CRITICAL_CONGESTION_SCORE, DETERMINISTIC_VARIATION_LIMIT,
    HEALTH_LABELS, HOTSPOT_WEIGHTS, JUNCTION_DENSITY_EFFECT,
    MAX_CONGESTION_PRESSURE, MINIMUM_TRAFFIC_SPEED_KMH, ROAD_IMPORTANCE,
    ROAD_TYPES, RUSH_HOUR_PERIODS, RUSH_HOUR_SCORE_EFFECT,
    SNAPSHOT_MINUTES, TIME_DENSITY_EFFECT, TIME_PERIODS, TIME_SCORE_EFFECT,
    TRAFFIC_SPEED_MULTIPLIERS, TREND_STABLE_THRESHOLD,
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


def traffic_health_label(score: float) -> str:
    score = clamp(score)
    return next(label for threshold, label in HEALTH_LABELS if score >= threshold)


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
        self._graph_cache = self._build_graph()

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
            previous_at = at - timedelta(minutes=SNAPSHOT_MINUTES)
            previous_key = self._snapshot_key(previous_at)
            previous = {road.id: self._analyze(road.id, previous_at, previous_key) for road in self.repository.roads}
            states = {}
            for road in self.repository.roads:
                current = self._analyze(road.id, at, key)
                change = round(current.traffic_score - previous[road.id].traffic_score, 1)
                trend = "worsening" if change > TREND_STABLE_THRESHOLD else "improving" if change < -TREND_STABLE_THRESHOLD else "stable"
                states[road.id] = replace(current, score_change=change, trend=trend)
            period = get_time_period(at)
            snapshot = TrafficSnapshot(
                snapshot_id=key, generated_at=at.isoformat(timespec="seconds"),
                time_period=period, rush_hour=period in RUSH_HOUR_PERIODS,
                roads=states,
            )
            # Retain current and deterministic previous windows only.
            self._snapshots = {key: snapshot}
            return snapshot

    def analyze_road(self, road_id: str, at: datetime | None = None) -> RoadTrafficState:
        return self.get_snapshot(at).roads.get(str(road_id)) or self._unknown_road(road_id)

    @staticmethod
    def _unknown_road(road_id):
        raise KeyError(f"Unknown road id: {road_id}")

    def _analyze(self, road_id: str, at: datetime, snapshot_key: str) -> RoadTrafficState:
        road = self.repository.by_id.get(str(road_id))
        if road is None:
            raise KeyError(f"Unknown road id: {road_id}")
        period = get_time_period(at)
        rush = period in RUSH_HOUR_PERIODS
        defaults = ROAD_TYPES[road.road_type]
        digest = hashlib.sha256(f"{road.id}|{snapshot_key}".encode("utf-8")).digest()
        normalized = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
        variation = (normalized * 2 - 1) * DETERMINISTIC_VARIATION_LIMIT
        context = CONTEXT_DENSITY_EFFECTS[period]
        context_demand = (
            road.commercial_activity * context["commercial"]
            + road.downtown_factor * context["downtown"]
            + road.school_university_factor * context["university"]
            + road.airport_corridor_factor * context["airport"]
            + road.junction_complexity * JUNCTION_DENSITY_EFFECT
        )
        time_demand = TIME_DENSITY_EFFECT[period] * defaults.congestion_sensitivity
        if rush:
            time_demand *= road.rush_hour_sensitivity
        capacity_density = max(0.0, 100.0 - road.capacity) * CAPACITY_DENSITY_WEIGHT
        density = clamp(road.base_congestion + time_demand + context_demand + capacity_density + variation)
        pressure = min(MAX_CONGESTION_PRESSURE, density / road.capacity)
        pressure_percent = clamp(pressure / MAX_CONGESTION_PRESSURE * 100.0)
        context_score = (context_demand * 0.22) + defaults.score_effect
        score = clamp(
            road.base_congestion * BASE_CONGESTION_WEIGHT
            + density * VEHICLE_DENSITY_WEIGHT
            + pressure_percent * CONGESTION_PRESSURE_WEIGHT
            + TIME_SCORE_EFFECT[period]
            + (RUSH_HOUR_SCORE_EFFECT if rush else 0.0)
            + context_score
        )
        level = classify_traffic(score)
        average_speed = max(MINIMUM_TRAFFIC_SPEED_KMH, road.base_speed_kmh * TRAFFIC_SPEED_MULTIPLIERS[level])
        free_flow_minutes = road.distance_km / road.base_speed_kmh * 60.0
        congested_minutes = road.distance_km / average_speed * 60.0
        delay = max(0.0, congested_minutes - free_flow_minutes)
        importance = ROAD_IMPORTANCE[road.road_type]
        delay_factor = min(1.0, delay / 15.0)
        impact = clamp(score * importance * (0.65 + 0.35 * delay_factor))
        speed_ratio = average_speed / road.base_speed_kmh
        reasons = self._reasons(road, period, rush, density, pressure, level, speed_ratio, variation)
        return RoadTrafficState(
            road_id=road.id, road_name=road.road_name, road_type=road.road_type,
            start=road.start, end=road.end,
            coordinates=(self.repository.locations[road.start], self.repository.locations[road.end]),
            traffic_score=round(score, 1), traffic_level=level,
            average_speed_kmh=round(average_speed, 1), vehicle_density=round(density, 1),
            congestion_pressure=round(pressure, 3), estimated_delay_minutes=round(delay, 2),
            traffic_impact=round(impact, 1), critical_congestion=score >= CRITICAL_CONGESTION_SCORE,
            time_period=period, rush_hour=rush, source="academic_simulation",
            score_change=0.0, trend="stable", reasons=tuple(reasons),
            summary_reason=self._summary_reason(road.road_name, level, reasons),
        )

    @staticmethod
    def _reasons(road, period, rush, density, pressure, level, speed_ratio, variation):
        reasons = []
        if rush:
            label = "Morning" if period == "MORNING_RUSH" else "Evening"
            reasons.append(f"{label} rush hour increased corridor demand")
        elif period == "NIGHT": reasons.append("Night-time demand is lower")
        elif period == "EARLY_MORNING": reasons.append("Early-morning demand is lower")
        else: reasons.append("Normal daytime travel demand is active")
        if road.commercial_activity >= 0.75 and period in {"DAYTIME", "EVENING_RUSH"}:
            reasons.append("Commercial activity increased traffic demand")
        if road.downtown_factor >= 0.7:
            reasons.append("Downtown junction activity increased road demand")
        if road.school_university_factor >= 0.7 and period in {"MORNING_RUSH", "EVENING_RUSH"}:
            reasons.append("University-area travel increased corridor demand")
        if road.airport_corridor_factor >= 0.7:
            reasons.append("Airport-corridor travel contributed to demand")
        if pressure >= 1.0:
            reasons.append("Simulated demand is at or above modelled road capacity")
        elif pressure >= 0.8:
            reasons.append("Simulated demand is approaching modelled road capacity")
        if road.base_congestion >= 70:
            reasons.append("The corridor has high modelled baseline congestion")
        if density >= 71: reasons.append("Simulated vehicle density is high")
        elif density <= 35: reasons.append("Simulated vehicle density is low")
        if road.road_type == "arterial": reasons.append("This is an important arterial corridor")
        elif road.road_type == "local" and pressure >= 0.8: reasons.append("Local-road capacity is limited")
        if speed_ratio < 0.45: reasons.append("Average speed fell below 45% of free-flow speed")
        if abs(variation) >= 2.5: reasons.append("Repeatable local demand variation affected this window")
        if level == "Heavy" and len(reasons) < 3: reasons.append("Combined demand exceeded the heavy-traffic threshold")
        return reasons

    @staticmethod
    def _summary_reason(name, level, reasons):
        evidence = "; ".join(reason[0].lower() + reason[1:] for reason in reasons[:2])
        return f"{name} is {level} because {evidence}."

    def congestion_hotspots(self, snapshot: TrafficSnapshot | None = None, limit: int = 8) -> list[dict]:
        snapshot = snapshot or self.get_snapshot()
        records = []
        for state in snapshot.roads.values():
            rank = (
                state.traffic_impact * HOTSPOT_WEIGHTS["impact"]
                + state.traffic_score * HOTSPOT_WEIGHTS["score"]
                + clamp(state.congestion_pressure / MAX_CONGESTION_PRESSURE * 100) * HOTSPOT_WEIGHTS["pressure"]
            )
            item = state.as_dict(); item["hotspot_rank_score"] = round(rank, 2); records.append(item)
        records.sort(key=lambda item: (-item["hotspot_rank_score"], -item["estimated_delay_minutes"], item["road_id"]))
        return records[:max(0, int(limit))]

    def best_flowing_roads(self, snapshot: TrafficSnapshot | None = None, limit: int = 8) -> list[dict]:
        snapshot = snapshot or self.get_snapshot()
        records = []
        for state in snapshot.roads.values():
            road = self.repository.by_id[state.road_id]
            delay_score = clamp(state.estimated_delay_minutes / 15.0 * 100)
            speed_loss = clamp((1 - state.average_speed_kmh / road.base_speed_kmh) * 100)
            rank = state.traffic_score * BEST_FLOW_WEIGHTS["score"] + delay_score * BEST_FLOW_WEIGHTS["delay"] + speed_loss * BEST_FLOW_WEIGHTS["speed_loss"]
            item = state.as_dict(); item["flow_rank_score"] = round(rank, 2); records.append(item)
        records.sort(key=lambda item: (item["flow_rank_score"], -item["average_speed_kmh"], item["road_id"]))
        return records[:max(0, int(limit))]

    def overview(self, at: datetime | None = None) -> dict:
        snapshot = self.get_snapshot(at)
        roads = [state.as_dict() for state in snapshot.roads.values()]
        counts = {level: sum(state.traffic_level == level for state in snapshot.roads.values()) for level in ("Light", "Moderate", "Heavy")}
        weighted_total = sum(state.traffic_score * ROAD_IMPORTANCE[state.road_type] for state in snapshot.roads.values())
        weight = sum(ROAD_IMPORTANCE[state.road_type] for state in snapshot.roads.values()) or 1.0
        weighted_average = weighted_total / weight
        health = round(clamp(100.0 - weighted_average), 1)
        hotspots = self.congestion_hotspots(snapshot)
        best = self.best_flowing_roads(snapshot)
        return {
            "snapshot_id": snapshot.snapshot_id, "snapshot_time": snapshot.generated_at,
            "generated_at": snapshot.generated_at, "time_period": snapshot.time_period,
            "rush_hour": snapshot.rush_hour, "model_type": "academic_simulation",
            "source": "academic_simulation", "trend_type": "simulated_adjacent_window",
            "traffic_health_score": health, "traffic_health_label": traffic_health_label(health),
            "total_roads": len(roads), "light_count": counts["Light"],
            "moderate_count": counts["Moderate"], "heavy_count": counts["Heavy"],
            "critical_count": sum(state.critical_congestion for state in snapshot.roads.values()),
            "average_traffic_score": round(sum(item["traffic_score"] for item in roads) / len(roads), 1) if roads else 0.0,
            "most_congested": hotspots[:5], "best_flowing": best[:5],
            "hotspots": hotspots, "roads": roads,
        }

    def route_state(self, start: str, destination: str, road_names=(), snapshot: TrafficSnapshot | None = None) -> dict:
        snapshot = snapshot or self.get_snapshot()
        path = self._shortest_path(start, destination)
        states = []
        for a, b in zip(path, path[1:]):
            road = self.repository.by_edge.get((a, b))
            if road and road.id in snapshot.roads: states.append(snapshot.roads[road.id])
        requested_names = {_road_name_key(name) for name in road_names if name}
        named = [state for state in snapshot.roads.values() if _road_name_key(state.road_name) in requested_names]
        if named: states = named
        if not states:
            return {"traffic_level":"Moderate","segment_traffic":["Moderate"],"road_ids":[],
                "average_score":50.0,"estimated_delay_minutes":0.0,"heavy_segments":0,
                "critical_segments":0,"cumulative_traffic_impact":0.0,
                "average_congestion_pressure":0.0,"snapshot_id":snapshot.snapshot_id,
                "source":"academic_simulation"}
        worst = max(states, key=lambda state: state.traffic_score).traffic_level
        return {
            "traffic_level": worst, "segment_traffic": [state.traffic_level for state in states],
            "road_ids": [state.road_id for state in states],
            "average_score": round(sum(state.traffic_score for state in states) / len(states), 1),
            "estimated_delay_minutes": round(sum(state.estimated_delay_minutes for state in states), 2),
            "heavy_segments": sum(state.traffic_level == "Heavy" for state in states),
            "critical_segments": sum(state.critical_congestion for state in states),
            "cumulative_traffic_impact": round(sum(state.traffic_impact for state in states), 1),
            "average_congestion_pressure": round(sum(state.congestion_pressure for state in states) / len(states), 3),
            "snapshot_id": snapshot.snapshot_id, "source":"academic_simulation",
        }

    def _build_graph(self):
        graph = {name: {} for name in self.repository.locations}
        for road in self.repository.roads:
            graph[road.start][road.end] = road.distance_km
            if road.bidirectional: graph[road.end][road.start] = road.distance_km
        return graph

    def _shortest_path(self, start, destination):
        if start not in self._graph_cache or destination not in self._graph_cache: return [start, destination]
        queue, best = [(0.0, (start,), start)], {start: 0.0}
        while queue:
            distance, path, node = heapq.heappop(queue)
            if node == destination: return list(path)
            if distance > best.get(node, float("inf")): continue
            for neighbor, weight in sorted(self._graph_cache[node].items()):
                candidate = distance + weight
                if candidate < best.get(neighbor, float("inf")):
                    best[neighbor] = candidate
                    heapq.heappush(queue, (candidate, path + (neighbor,), neighbor))
        return [start, destination]


TRAFFIC_ENGINE = TrafficEngine()
