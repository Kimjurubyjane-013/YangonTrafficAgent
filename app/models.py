from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class RouteRequest:
    vehicle: str
    start: str
    destination: str
    conditions: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        # `error` remains for backward-compatible browser handling.
        return {"error": self.message, "error_details": {"code": self.code, "message": self.message}}


@dataclass(frozen=True)
class RoadSegment:
    id: str
    start: str
    end: str
    road_name: str
    road_type: str
    distance_km: float
    base_speed_kmh: float
    base_congestion: float
    capacity: int
    bidirectional: bool = True
    preferred: bool = False
    commercial_activity: float = 0.0
    junction_complexity: float = 0.0
    rush_hour_sensitivity: float = 1.0
    downtown_factor: float = 0.0
    school_university_factor: float = 0.0
    airport_corridor_factor: float = 0.0


@dataclass(frozen=True)
class RoadTrafficState:
    road_id: str
    road_name: str
    road_type: str
    start: str
    end: str
    coordinates: tuple[tuple[float, float], tuple[float, float]]
    traffic_score: float
    traffic_level: str
    average_speed_kmh: float
    vehicle_density: float
    congestion_pressure: float
    estimated_delay_minutes: float
    traffic_impact: float
    critical_congestion: bool
    time_period: str
    rush_hour: bool
    source: str
    score_change: float
    trend: str
    reasons: tuple[str, ...]
    summary_reason: str
    score_components: Mapping[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        data["coordinates"] = [list(point) for point in self.coordinates]
        data["reasons"] = list(self.reasons)
        return data


@dataclass(frozen=True)
class TrafficSnapshot:
    snapshot_id: str
    generated_at: str
    time_period: str
    rush_hour: bool
    roads: Mapping[str, RoadTrafficState]

    def road(self, road_id: str) -> RoadTrafficState | None:
        return self.roads.get(road_id)
