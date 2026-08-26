"""Central configuration for the academic Yangon traffic simulation."""
from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class RoadTypeDefaults:
    typical_speed_kmh: float
    congestion_sensitivity: float
    capacity: int
    score_effect: float


ROAD_TYPES = {
    "arterial": RoadTypeDefaults(45.0, 1.15, 90, 5.0),
    "main": RoadTypeDefaults(38.0, 1.00, 75, 2.0),
    "secondary": RoadTypeDefaults(32.0, 0.82, 58, -1.0),
    "local": RoadTypeDefaults(25.0, 0.65, 40, -4.0),
}

TRAFFIC_THRESHOLDS = {"Light": (0, 35), "Moderate": (36, 70), "Heavy": (71, 100)}
TRAFFIC_SPEED_MULTIPLIERS = {"Light": 0.90, "Moderate": 0.65, "Heavy": 0.40}
MINIMUM_TRAFFIC_SPEED_KMH = 4.0
SNAPSHOT_MINUTES = 15
TIME_PERIODS = (
    ("EARLY_MORNING", time(5, 0), time(7, 0)),
    ("MORNING_RUSH", time(7, 0), time(9, 30)),
    ("DAYTIME", time(9, 30), time(16, 0)),
    ("EVENING_RUSH", time(16, 0), time(19, 30)),
    ("NIGHT", time(19, 30), time(5, 0)),
)
RUSH_HOUR_PERIODS = frozenset({"MORNING_RUSH", "EVENING_RUSH"})
TIME_DENSITY_EFFECT = {"EARLY_MORNING":-12.0,"MORNING_RUSH":14.0,"DAYTIME":2.0,"EVENING_RUSH":16.0,"NIGHT":-18.0}
TIME_SCORE_EFFECT = {"EARLY_MORNING":-5.0,"MORNING_RUSH":7.0,"DAYTIME":1.0,"EVENING_RUSH":8.0,"NIGHT":-9.0}
RUSH_HOUR_SCORE_EFFECT = 3.0
BASE_CONGESTION_WEIGHT = 0.55
VEHICLE_DENSITY_WEIGHT = 0.35
CAPACITY_DENSITY_WEIGHT = 0.08
DETERMINISTIC_VARIATION_LIMIT = 4.0
