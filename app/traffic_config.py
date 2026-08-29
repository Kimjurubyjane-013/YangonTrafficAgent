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
TIME_DENSITY_EFFECT = {"EARLY_MORNING":-14.0,"MORNING_RUSH":10.0,"DAYTIME":0.0,"EVENING_RUSH":12.0,"NIGHT":-20.0,"OFF_PEAK":-10.0,"PEAK":11.0}
TIME_SCORE_EFFECT = {"EARLY_MORNING":-5.0,"MORNING_RUSH":3.0,"DAYTIME":0.0,"EVENING_RUSH":4.0,"NIGHT":-5.0,"OFF_PEAK":-4.0,"PEAK":3.5}
SCENARIO_ETA_MULTIPLIERS = {"current": 1.0, "off_peak": 0.94, "peak": 1.18}
# Time and road context already affect density. The direct period adjustment is
# deliberately small so the same demand is not counted a second time.
RUSH_HOUR_SCORE_EFFECT = 0.0
VEHICLE_DENSITY_WEIGHT = 0.22
BASE_CONGESTION_WEIGHT = 0.30
CONGESTION_PRESSURE_WEIGHT = 0.10
# A bounded overload term preserves genuine high-pressure congestion without
# making ordinary arterial roads Heavy merely because several correlated
# inputs describe the same demand.
PRESSURE_OVERLOAD_START = 0.85
PRESSURE_OVERLOAD_WEIGHT = 18.0
MAX_PRESSURE_OVERLOAD_SCORE = 8.0
SCORE_SPREAD_FACTOR = 1.40
CAPACITY_DENSITY_WEIGHT = 0.04
DETERMINISTIC_VARIATION_LIMIT = 4.0
CRITICAL_CONGESTION_SCORE = 90.0
MAX_CONGESTION_PRESSURE = 1.5
ROAD_IMPORTANCE = {"arterial":1.35,"main":1.10,"secondary":0.85,"local":0.65}
CONTEXT_DENSITY_EFFECTS = {
    "EARLY_MORNING": {"commercial":1.0,"downtown":1.0,"university":1.0,"airport":5.0},
    "MORNING_RUSH": {"commercial":4.0,"downtown":6.0,"university":9.0,"airport":6.0},
    "DAYTIME": {"commercial":7.0,"downtown":6.0,"university":3.0,"airport":4.0},
    "EVENING_RUSH": {"commercial":8.0,"downtown":9.0,"university":7.0,"airport":7.0},
    "NIGHT": {"commercial":2.0,"downtown":2.0,"university":0.0,"airport":6.0},
    "OFF_PEAK": {"commercial":3.0,"downtown":2.0,"university":2.0,"airport":4.0},
    "PEAK": {"commercial":6.0,"downtown":8.0,"university":8.0,"airport":6.0},
}
JUNCTION_DENSITY_EFFECT = 3.0
HOTSPOT_WEIGHTS = {"impact":0.55,"score":0.30,"pressure":0.15}
BEST_FLOW_WEIGHTS = {"score":0.55,"delay":0.30,"speed_loss":0.15}
TREND_STABLE_THRESHOLD = 2.0
HEALTH_LABELS = ((85,"Excellent"),(70,"Good"),(50,"Moderate"),(30,"Poor"),(0,"Severe"))
