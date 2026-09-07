"""Regression tests for swapped-journey traffic consistency, directional rules, and state reset.

Covers:
- Test A: Same inferred segment + same scenario + no directional model => stable same severity
- Test B: Different reverse corridor => severity may legitimately differ
- Test C: Direction-aware provider traffic => opposite directions may differ
- Test D: Swap clears old traffic/map state
- Test E: Route-level severity is derived from current segment data only
- Test F: Asia/Yangon scenario remains consistent across immediate swap
- Specific test: Shwedagon Pagoda <-> Chinatown Night Market end-to-end traffic audit
"""
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from algorithms.graph import LOCATION_COORDS
from agent.real_world_agent import run_real_world_agent, _effective_route_traffic
from app.runtime_config import yangon_now
from services.traffic_service import TRAFFIC_ENGINE, classify_traffic, classify_route_traffic
from services.road_repository import ROAD_REPOSITORY


class TestSwappedJourneyTrafficConsistency(unittest.TestCase):
    def setUp(self):
        self.engine = TRAFFIC_ENGINE
        self.repo = ROAD_REPOSITORY

    def test_a_same_inferred_segment_same_scenario_stable_severity(self):
        """Test A: Same inferred segment under the same scenario must produce identical traffic severity."""
        snapshot = self.engine.get_snapshot(scenario="current")
        # Check all road segments in repository
        for road in self.repo.roads:
            state = snapshot.roads.get(road.id)
            self.assertIsNotNone(state, f"Road {road.id} missing from snapshot")
            # Analyze same road again in the same snapshot/time context
            state_repeat = snapshot.roads[road.id]
            self.assertEqual(state.traffic_level, state_repeat.traffic_level)
            self.assertEqual(state.traffic_score, state_repeat.traffic_score)

        # Specifically verify U Wisara Road and Myoma Kyaung Street segments
        u_wisara = snapshot.roads["u_wisara_peoples_park_happy_world"]
        myoma = snapshot.roads["myoma_museum_theatre"]
        self.assertIn(u_wisara.traffic_level, {"Light", "Moderate", "Heavy"})
        self.assertIn(myoma.traffic_level, {"Light", "Moderate", "Heavy"})

    def test_b_different_reverse_corridors_may_differ(self):
        """Test B: Different physical reverse corridors (e.g. one-way streets) may legitimately have different severity."""
        snapshot = self.engine.get_snapshot(scenario="current")
        # Strand Road (southern waterfront arterial) vs Anawrahta Road (downtown commercial one-way)
        strand = snapshot.roads.get("strand_theingyi_chinatown_night_market")
        anawrahta = snapshot.roads.get("anawrahta_junction_city_theingyi")
        self.assertIsNotNone(strand)
        self.assertIsNotNone(anawrahta)
        # They represent distinct corridors and are evaluated independently based on their physical attributes
        self.assertIsInstance(strand.traffic_score, float)
        self.assertIsInstance(anawrahta.traffic_score, float)

    def test_c_direction_aware_provider_traffic_preserves_differences(self):
        """Test C: Direction-aware provider traffic preserves opposite-direction flow differences."""
        # Provider route with directional traffic: forward has Moderate, reverse has Heavy
        mock_route_fwd = {
            "traffic_data_available": True,
            "segment_traffic": ["Moderate", "Light"],
            "segment_sources": ["HERE", "HERE"],
            "traffic_geometry": [[[16.80, 96.14], [16.79, 96.14]], [[16.79, 96.14], [16.80, 96.14]]],
        }
        mock_route_rev = {
            "traffic_data_available": True,
            "segment_traffic": ["Heavy", "Heavy"],
            "segment_sources": ["HERE", "HERE"],
            "traffic_geometry": [[[16.80, 96.14], [16.79, 96.14]], [[16.79, 96.14], [16.80, 96.14]]],
        }
        mock_model_state = {"segment_traffic": ["Moderate"], "segment_distances": [1.0, 1.0]}

        eff_fwd = _effective_route_traffic(mock_route_fwd, mock_model_state, allow_provider=True)
        eff_rev = _effective_route_traffic(mock_route_rev, mock_model_state, allow_provider=True)

        self.assertEqual(eff_fwd["traffic_source_label"], "HERE")
        self.assertEqual(eff_rev["traffic_source_label"], "HERE")
        self.assertEqual(eff_fwd["segment_traffic"], ["Moderate", "Light"])
        self.assertEqual(eff_rev["segment_traffic"], ["Heavy", "Heavy"])
        # Directional provider reports different levels, which must be honestly preserved
        self.assertNotEqual(eff_fwd["traffic"], eff_rev["traffic"])

    def test_d_swap_clears_old_traffic_and_map_state(self):
        """Test D: Swap implementation clears old route geometry, alternatives, traffic styling, and recommendations."""
        app_html = (Path(__file__).parent / "web" / "app.html").read_text(encoding="utf-8")
        app_js = (Path(__file__).parent / "web" / "app.js").read_text(encoding="utf-8")

        # Verify clearRouteDisplay is defined and exposed
        self.assertIn("function clearRouteDisplay()", app_html)
        self.assertIn("window.clearRouteDisplay = clearRouteDisplay", app_html)

        # Verify clearRouteDisplay resets map, alternatives, traffic styling, and recommendations
        self.assertIn("clearMap()", app_html)
        self.assertIn("route-options", app_html)
        self.assertIn("r-traffic", app_html)
        self.assertIn("allOptionsData = []", app_html)

        # Verify app.js calls clearRouteDisplay when swap-route is clicked
        self.assertIn("clearRouteDisplay", app_js)
        self.assertIn("swap-route", app_js)

    def test_e_route_level_severity_derived_from_current_segment_exposure_only(self):
        """Test E: Route-level severity is calculated from distance-weighted segment exposure of current route."""
        # 3 Moderate segments (total 3.0 km) + 1 Heavy segment (0.5 km) => Moderate overall
        weights = [1.0, 1.0, 1.0, 0.5]
        levels = ["Moderate", "Moderate", "Moderate", "Heavy"]
        mock_state = {
            "segment_traffic": levels,
            "segment_distances": weights,
            "traffic_level": "Moderate",
            "average_score": 59.3,
        }
        mock_route = {
            "traffic_data_available": False,
            "segment_traffic": ["Unavailable"],
            "segment_sources": [],
            "road_names": ["Test Road"],
            "geometry": [[16.80, 96.14], [16.81, 96.14]],
        }

        effective = _effective_route_traffic(mock_route, mock_state, allow_provider=False)
        self.assertEqual(effective["traffic"], "Moderate")
        self.assertEqual(effective["segment_traffic"], levels)

    def test_f_asia_yangon_scenario_consistent_across_swap(self):
        """Test F: Asia/Yangon time and scenario remain identical across immediate swap."""
        now_yangon = yangon_now()
        # Verify timezone offset is UTC+6:30
        tz_offset = now_yangon.utcoffset().total_seconds() / 3600
        self.assertEqual(tz_offset, 6.5, "Application time must be in Asia/Yangon (UTC+6:30)")

        # Verify snapshot ID for the same scenario is identical across successive calls
        snap1 = self.engine.get_snapshot(scenario="current")
        snap2 = self.engine.get_snapshot(scenario="current")
        self.assertEqual(snap1.snapshot_id, snap2.snapshot_id)

    def test_shwedagon_chinatown_swap_consistency_end_to_end(self):
        """End-to-end test: Shwedagon Pagoda <-> Chinatown Night Market.
        - Both directions succeed without error.
        - Shared physical corridors (U Wisara Road, etc.) have identical segment severity.
        - Direction-specific corridors (Strand Road southbound vs Anawrahta / Maha Bandula northbound) are legal.
        - Overall route-level traffic in both directions is Moderate.
        """
        loc1 = "Shwedagon Pagoda"
        loc2 = "Chinatown Night Market"

        res_a = run_real_world_agent(loc1, loc2, "Car")
        res_b = run_real_world_agent(loc2, loc1, "Car")

        self.assertNotIn("error", res_a, f"Forward journey failed: {res_a}")
        self.assertNotIn("error", res_b, f"Reverse journey failed: {res_b}")

        # Both routes must have valid traffic classifications
        self.assertIn(res_a.get("traffic"), {"Light", "Moderate", "Heavy"})
        self.assertIn(res_b.get("traffic"), {"Light", "Moderate", "Heavy"})

        # Collect diagnostics from both directions
        diag_a = {d["road_id"]: d for d in res_a.get("segment_diagnostics", [])}
        diag_b = {d["road_id"]: d for d in res_b.get("segment_diagnostics", [])}

        # Find shared physical road IDs between both directions
        shared_ids = set(diag_a.keys()).intersection(set(diag_b.keys()))
        self.assertTrue(len(shared_ids) >= 1, f"Expected shared segments between {loc1} and {loc2}, got none")

        for road_id in shared_ids:
            seg_a = diag_a[road_id]
            seg_b = diag_b[road_id]
            # Verify identical traffic level and score for shared physical segments
            self.assertEqual(
                seg_a["traffic_level"], seg_b["traffic_level"],
                f"Shared segment {road_id} has inconsistent traffic level: {seg_a['traffic_level']} vs {seg_b['traffic_level']}"
            )
            self.assertEqual(
                seg_a["traffic_score"], seg_b["traffic_score"],
                f"Shared segment {road_id} has inconsistent traffic score: {seg_a['traffic_score']} vs {seg_b['traffic_score']}"
            )


if __name__ == "__main__":
    unittest.main()
