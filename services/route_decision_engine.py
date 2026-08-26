"""Hybrid numeric + symbolic route decision engine.

Formula: total_score = distance_km + 0.35 * estimated_minutes + rule_penalty.
Lower is better. Python owns graph/numeric work; Prolog or the deterministic
fallback owns eligibility and explainable policy penalties.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock


DISTANCE_WEIGHT = 1.0
TIME_WEIGHT = 0.35
VALID_VEHICLES = {"car", "bus", "taxi", "ambulance", "fire_truck", "police", "motorcycle", "bicycle", "walking"}
VALID_TRAFFIC = {"light", "moderate", "heavy"}
VALID_ROADS = {"local", "secondary", "main", "arterial", "highway", "restricted"}
VALID_TIME_BANDS = {"off_peak", "peak"}
VALID_WEATHER = {"clear", "rain", "storm"}
VALID_INCIDENTS = {"none", "minor", "major"}
_LOCK = RLock()


def _atom(value, allowed, default):
    atom = str(value).strip().lower().replace(" ", "_")
    return atom if atom in allowed else default


def _python_rules(candidate, vehicle, conditions):
    penalties = {"congestion": 0.0, "vehicle_restriction": 0.0, "time": 0.0, "weather": 0.0, "incident": 0.0, "preference": 0.0}
    rejection = []
    reasons = []
    congestion = {"light": 0, "moderate": 3, "heavy": 9}
    for segment in candidate["segments"]:
        road = segment["road_class"]
        traffic = segment["traffic"]
        if not segment["one_way_ok"]:
            rejection.append(f"one_way_restriction({segment['index']})")
        if road == "restricted" and vehicle not in {"ambulance", "fire_truck", "police"}:
            rejection.append("vehicle_prohibited_on_restricted_road")
        if vehicle in {"bus", "fire_truck"} and road == "local":
            penalties["vehicle_restriction"] += 7
        if vehicle == "bicycle" and road == "highway":
            rejection.append("bicycle_prohibited_on_highway")
        if vehicle == "walking" and road in {"highway", "restricted"}:
            rejection.append("walking_prohibited_on_highway" if road == "highway" else "walking_prohibited_on_restricted_road")
        penalties["congestion"] += congestion[traffic]
        if conditions["time_band"] == "peak" and road == "arterial":
            penalties["time"] += 4
        if segment["preferred"]:
            penalties["preference"] -= 1.5
    penalties["weather"] = {"clear": 0, "rain": 4, "storm": 12}[conditions["weather"]]
    penalties["incident"] = {"none": 0, "minor": 6, "major": 18}[conditions["incident"]]
    if penalties["congestion"]: reasons.append("congestion_penalty")
    if penalties["vehicle_restriction"]: reasons.append("vehicle_road_suitability_penalty")
    if penalties["preference"] < 0: reasons.append("preferred_road_benefit")
    return penalties, sorted(set(rejection)), reasons


class RouteDecisionEngine:
    def __init__(self, prefer_prolog=True):
        self._prolog = None
        self.diagnostic = "Python fallback active: SWI-Prolog/PySwip unavailable."
        if prefer_prolog:
            try:
                from pyswip import Prolog
                self._prolog = Prolog()
                self._prolog.consult(str(Path(__file__).parents[1] / "prolog" / "traffic_rules.pl"))
                self.diagnostic = "SWI-Prolog rule engine active."
            except Exception as exc:
                self.diagnostic = f"Python fallback active: {type(exc).__name__}: {exc}"

    @property
    def engine_name(self):
        return "prolog" if self._prolog is not None else "python-fallback"

    def evaluate(self, candidates, vehicle, conditions=None):
        vehicle_atom = _atom(vehicle, VALID_VEHICLES, "car")
        supplied = conditions or {}
        normalized = {
            "time_band": _atom(supplied.get("time_band", "off_peak"), VALID_TIME_BANDS, "off_peak"),
            "weather": _atom(supplied.get("weather", "clear"), VALID_WEATHER, "clear"),
            "incident": _atom(supplied.get("incident", "none"), VALID_INCIDENTS, "none"),
        }
        evaluated = []
        for candidate in candidates:
            penalties, rejection, reasons = self._evaluate_rules(candidate, vehicle_atom, normalized)
            distance_cost = candidate["distance"] * DISTANCE_WEIGHT
            time_cost = candidate["time"] * TIME_WEIGHT
            rule_penalty = round(sum(penalties.values()), 3)
            total = round(distance_cost + time_cost + rule_penalty, 3)
            item = dict(candidate)
            item["decision"] = {
                "total_score": total, "distance_cost": round(distance_cost, 3),
                "estimated_time_cost": round(time_cost, 3), "rule_penalty": rule_penalty,
                "congestion_penalty": penalties["congestion"],
                "vehicle_restriction_penalty": penalties["vehicle_restriction"],
                "other_rule_penalties": {k: v for k, v in penalties.items() if k not in {"congestion", "vehicle_restriction"}},
                "rejection_reasons": rejection, "reasons": reasons,
                "eligible": not rejection, "engine": self.engine_name,
            }
            evaluated.append(item)
        eligible = [item for item in evaluated if item["decision"]["eligible"]]
        eligible.sort(key=lambda item: (item["decision"]["total_score"], item["distance"], item["time"], tuple(item["route"])))
        return eligible, evaluated

    def _evaluate_rules(self, candidate, vehicle, conditions):
        if self._prolog is None:
            return _python_rules(candidate, vehicle, conditions)
        try:
            return self._prolog_rules(candidate, vehicle, conditions)
        except Exception as exc:
            self.diagnostic = f"Python fallback active after Prolog error: {type(exc).__name__}: {exc}"
            self._prolog = None
            return _python_rules(candidate, vehicle, conditions)

    def _prolog_rules(self, candidate, vehicle, conditions):
        # Only allowlisted atoms and numeric values reach these fixed templates.
        with _LOCK:
            p = self._prolog
            try:
                p.assertz(f"request_vehicle({vehicle})")
                p.assertz(f"request_condition({conditions['time_band']},{conditions['weather']},{conditions['incident']})")
                for index, segment in enumerate(candidate["segments"]):
                    road = _atom(segment["road_class"], VALID_ROADS, "arterial")
                    traffic = _atom(segment["traffic"], VALID_TRAFFIC, "moderate")
                    preferred = "true" if segment["preferred"] else "false"
                    direction = "true" if segment["one_way_ok"] else "false"
                    p.assertz(f"request_segment({index},{road},{traffic},{preferred},{direction})")
                row = next(iter(p.query("request_evaluation(C,V,T,W,I,P,Rejections,Reasons)")), None)
                if row is None:
                    raise RuntimeError("Prolog produced no evaluation")
                penalties = {"congestion": float(row["C"]), "vehicle_restriction": float(row["V"]), "time": float(row["T"]), "weather": float(row["W"]), "incident": float(row["I"]), "preference": float(row["P"])}
                return penalties, [str(x) for x in row["Rejections"]], [str(x) for x in row["Reasons"]]
            finally:
                list(p.query("clear_request"))
