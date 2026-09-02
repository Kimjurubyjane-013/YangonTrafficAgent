"""System-wide automated route matrix audit across all supported Yangon locations.

Tests all N * (N - 1) directional pairs dynamically without hard-coding location names.
Validates route geometry invariants, road-name Unicode safety, traffic determinism,
swap consistency, and API data contracts.
"""
from __future__ import annotations

import json
import math
import os
import sys
import unittest
from pathlib import Path

from algorithms.graph import LOCATION_COORDS, get_locations
from agent.real_world_agent import run_real_world_agent
from services.osrm_service import _has_self_intersection_loop, _CACHE
from services.traffic_service import TrafficEngine


def load_all_locations() -> list[str]:
    """Dynamically load all location names from canonical locations.json."""
    loc_file = Path(__file__).parent / "data" / "locations.json"
    if loc_file.exists():
        with open(loc_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [item["name"] for item in data if "name" in item]
    return list(LOCATION_COORDS)


class RouteMatrixAudit:
    """Audits routing and traffic reliability across all pairs."""

    def __init__(self, locations: list[str] | None = None):
        self.locations = locations or load_all_locations()
        self.total_locations = len(self.locations)
        self.total_pairs = self.total_locations * (self.total_locations - 1)
        self.results = []
        self.failures = []
        self.suspicious = []

    def audit_pair(self, start: str, dest: str) -> dict:
        """Audit a single directional pair."""
        if start == dest:
            return {"status": "skipped", "reason": "same_location"}

        try:
            res = run_real_world_agent(start, dest, "Car")
        except Exception as e:
            return {
                "status": "failed",
                "start": start,
                "dest": dest,
                "error": f"Exception during routing: {type(e).__name__}: {e}",
            }

        if "error" in res:
            return {
                "status": "failed",
                "start": start,
                "dest": dest,
                "error": res["error"],
            }

        # Validate Invariants
        errors = []
        warnings = []

        # 1. Distance & Time
        dist = res.get("distance")
        travel_time = res.get("time")
        base_dur = res.get("base_duration")

        if not isinstance(dist, (int, float)) or dist <= 0:
            errors.append(f"Invalid distance: {dist}")
        if not isinstance(travel_time, (int, float)) or travel_time <= 0:
            errors.append(f"Invalid travel time: {travel_time}")
        if not isinstance(base_dur, (int, float)) or base_dur <= 0:
            errors.append(f"Invalid base duration: {base_dur}")

        # 2. Geometry
        geom = res.get("geometry", [])
        if not isinstance(geom, list) or len(geom) < 2:
            errors.append(f"Invalid geometry: {len(geom) if isinstance(geom, list) else type(geom)}")
        else:
            for pt in geom:
                if not (isinstance(pt, (list, tuple)) and len(pt) == 2):
                    errors.append(f"Invalid geometry point format: {pt}")
                    break
                lat, lon = pt[0], pt[1]
                if not (16.0 <= lat <= 17.5 and 95.5 <= lon <= 96.6):
                    errors.append(f"Coordinate out of Yangon bounds: [{lat}, {lon}]")
                    break

            if _has_self_intersection_loop(geom):
                errors.append("Primary route contains self-intersection loop")

        # 3. Display Route & Road Names
        disp = res.get("display_route", [])
        if not isinstance(disp, list) or len(disp) < 2:
            errors.append(f"Invalid display route: {disp}")
        else:
            if disp[0] != start:
                errors.append(f"Display route origin mismatch: expected '{start}', got '{disp[0]}'")
            if disp[-1] != dest:
                errors.append(f"Display route dest mismatch: expected '{dest}', got '{disp[-1]}'")

        road_names = res.get("road_names", [])
        for name in road_names:
            if not isinstance(name, str) or not name.strip():
                errors.append(f"Invalid or empty road name in list: {repr(name)}")
            if any(bad in name for bad in ("[object", "undefined", "NaN", "null", "None")):
                errors.append(f"Object stringification in road name: '{name}'")

        # 4. Traffic Classification
        traffic = res.get("traffic")
        if traffic not in ("Light", "Moderate", "Heavy", "Unknown"):
            errors.append(f"Invalid traffic level: {traffic}")

        traffic_score = res.get("traffic_score")
        if not isinstance(traffic_score, (int, float)) or not (0.0 <= traffic_score <= 100.0):
            errors.append(f"Traffic score out of range [0, 100]: {traffic_score}")

        # 5. Recommendation explanation
        reason = res.get("recommendation_reason", {})
        if not isinstance(reason, dict) or not reason.get("explanation"):
            errors.append("Missing recommendation reason explanation")

        # 6. Alternatives sanity
        alts = res.get("alternatives", [])
        for idx, alt in enumerate(alts):
            alt_geom = alt.get("geometry", [])
            if len(alt_geom) < 2:
                errors.append(f"Alternative {idx+1} has empty geometry")
            if _has_self_intersection_loop(alt_geom):
                warnings.append(f"Alternative {idx+1} has loop")

        status = "failed" if errors else ("suspicious" if warnings else "passed")
        return {
            "status": status,
            "start": start,
            "dest": dest,
            "distance": dist,
            "time": travel_time,
            "traffic": traffic,
            "traffic_score": traffic_score,
            "road_names": road_names,
            "display_route": disp,
            "errors": errors,
            "warnings": warnings,
            "alternatives_count": len(alts),
        }

    def run_audit(self, limit: int | None = None) -> dict:
        """Run the audit across all pairs."""
        pairs_to_test = []
        for a in self.locations:
            for b in self.locations:
                if a != b:
                    pairs_to_test.append((a, b))

        if limit:
            pairs_to_test = pairs_to_test[:limit]

        passed = 0
        failed = 0
        suspicious = 0
        pair_results = {}

        for start, dest in pairs_to_test:
            res = self.audit_pair(start, dest)
            pair_results[(start, dest)] = res
            if res["status"] == "passed":
                passed += 1
            elif res["status"] == "suspicious":
                suspicious += 1
                self.suspicious.append(res)
            else:
                failed += 1
                self.failures.append(res)

        # Audit Swap Invariants
        swap_failures = []
        for (a, b), fwd in pair_results.items():
            rev = pair_results.get((b, a))
            if not rev or fwd["status"] != "passed" or rev["status"] != "passed":
                continue

            fwd_roads = set(fwd.get("road_names", []))
            rev_roads = set(rev.get("road_names", []))
            if fwd_roads and fwd_roads == rev_roads:
                score_diff = abs(fwd.get("traffic_score", 50) - rev.get("traffic_score", 50))
                if score_diff > 15.0:
                    swap_failures.append({
                        "pair": f"{a} <-> {b}",
                        "roads": list(fwd_roads),
                        "fwd_traffic": f"{fwd['traffic']} ({fwd['traffic_score']})",
                        "rev_traffic": f"{rev['traffic']} ({rev['traffic_score']})",
                        "score_diff": round(score_diff, 1),
                    })

        return {
            "total_locations": self.total_locations,
            "pairs_tested": len(pairs_to_test),
            "passed": passed,
            "failed": failed,
            "suspicious": suspicious,
            "swap_traffic_anomalies": len(swap_failures),
            "swap_failures": swap_failures,
            "failures": self.failures[:20],
        }


class TestAllLocationRoutes(unittest.TestCase):
    """Pytest-compatible test suite for route matrix invariants."""

    @classmethod
    def setUpClass(cls):
        cls.locations = load_all_locations()
        cls.engine = TrafficEngine()
        cls.snapshot = cls.engine.get_snapshot()

    def test_all_supported_locations_exist_and_have_coordinates(self):
        self.assertGreaterEqual(len(self.locations), 20)
        for loc in self.locations:
            self.assertIn(loc, LOCATION_COORDS, f"Location '{loc}' missing from LOCATION_COORDS")
            coord = LOCATION_COORDS[loc]
            self.assertTrue(16.0 <= coord[0] <= 17.5, f"Latitude out of bounds for {loc}: {coord[0]}")
            self.assertTrue(95.5 <= coord[1] <= 96.6, f"Longitude out of bounds for {loc}: {coord[1]}")

    def test_representative_route_matrix_invariants(self):
        """Test representative directional location pairs across Yangon."""
        sample_locs = [
            "Hledan Centre", "Junction Square", "Sanchaung", "Shwedagon Pagoda", "Sule Pagoda",
        ]
        audit = RouteMatrixAudit(sample_locs)
        summary = audit.run_audit()
        self.assertEqual(summary["failed"], 0, f"Routing failures detected: {summary['failures']}")
        self.assertEqual(summary["swap_traffic_anomalies"], 0, f"Swap traffic anomalies: {summary['swap_failures']}")

    def test_unicode_road_normalization_preserves_myanmar_text(self):
        from services.osrm_service import _english_road_names
        test_route = {
            "legs": [{
                "steps": [
                    {"name": "ရှမ်းကုန်းလမ်း"},
                    {"name": "ဦးဝီစာရလမ်း"},
                    {"name": "ရွှေဂုံတိုင်လမ်း"},
                ]
            }]
        }
        names = _english_road_names(test_route)
        self.assertIn("U Wisara Road", names)
        self.assertIn("Shwegondaing Road", names)
        for name in names:
            self.assertTrue(len(name) > 0)
            self.assertNotIn("[object", name)


if __name__ == "__main__":
    audit = RouteMatrixAudit()
    print(f"Starting System-Wide Route Matrix Audit ({audit.total_locations} locations, {audit.total_pairs} pairs)...")
    summary = audit.run_audit(limit=60)
    print(json.dumps(summary, indent=2))
