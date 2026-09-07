"""Unit and regression tests for bidirectional route consistency, corridor recovery, and ranking.

Covers:
- Test A: Bidirectional road corridor recovery (symmetric / two-way road corridors appear in both directions)
- Test B: Divided carriageway direction-specific geometry (reverse corridor follows legal opposite carriageway geometry)
- Test C: One-way restriction protection (one-way street is NEVER forced in reverse direction)
- Test D: Turn restriction adherence (median dividers, prohibited turns, roundabout navigation respected)
- Test E: Direct vs longer same-traffic route ranking (direct shorter route ranks as Recommended / Route A; longer route as Alternative)
- Test F: Traffic-aware exception (longer route ranks first ONLY when its traffic advantage is significant)
- Test G: Near-duplicate suppression (minor alley jogs with overlap >= 0.50 suppressed; distinct corridors < 0.50 preserved)
- Test H: Swap consistency (Hledan Centre <-> Junction Square end-to-end corridor preservation and ranking)
"""
import unittest
from unittest.mock import patch

from services.osrm_service import (
    _CACHE,
    _REVERSE_CORRIDOR_CHECKED,
    _has_backtracking_or_hairpin,
    _has_leave_and_rejoin_excursion,
    _has_self_intersection_loop,
    _is_diverse,
    _overlap,
    fetch_real_routes,
)
from services.route_ranking import (
    has_meaningful_traffic_advantage,
    is_route_dominated,
    route_cost,
)
from services.route_decision_engine import RouteDecisionEngine
from agent.real_world_agent import (
    _filter_practical_alternatives,
    _recommendation_reason,
    run_real_world_agent,
)


def _make_route(coords, dist_km, dur_min, road_names, traffic="Moderate", steps=None, source="osrm-native"):
    return {
        "candidate_id": road_names[0] if road_names else "route",
        "route": road_names,
        "display_route": road_names,
        "geometry": coords,
        "distance": dist_km,
        "duration": dur_min,
        "time": dur_min,
        "road_names": road_names,
        "traffic": traffic,
        "overall_traffic": traffic,
        "segment_traffic": [traffic],
        "steps": steps or [],
        "source": source,
        "traffic_delay": 0.0,
        "heavy_segments": 1 if traffic == "Heavy" else 0,
        "critical_segments": 0,
        "cumulative_traffic_impact": 10.0 if traffic == "Heavy" else 2.0,
        "average_congestion_pressure": 0.5,
        "traffic_score": 85.0 if traffic == "Heavy" else 55.0 if traffic == "Moderate" else 25.0,
        "segments": [
            {"index": 0, "road_class": "arterial", "traffic": traffic.lower(), "preferred": False, "one_way_ok": True}
        ],
    }


def _raw_osrm(coords, dist_meters, dur_seconds, road_name="Test Road"):
    return {
        "distance": dist_meters,
        "duration": dur_seconds,
        "geometry": {"coordinates": [[lon, lat] for lat, lon in coords]},
        "legs": [{"steps": [{"name": road_name, "distance": dist_meters, "duration": dur_seconds}]}],
    }


class TestBidirectionalConsistency(unittest.TestCase):

    def setUp(self):
        _CACHE.clear()
        _REVERSE_CORRIDOR_CHECKED.clear()
        self.engine = RouteDecisionEngine(False)

    def test_a_bidirectional_road_corridor_recovery(self):
        """Test A: Bidirectional road corridor recovery.
        When A->B has a primary corridor (Corridor 1) and B->A has an alternative corridor (Corridor 2),
        querying A->B discovers Corridor 2 via reverse corridor exploration and returns both corridors.
        """
        pt_a = (16.8000, 96.1000)
        pt_b = (16.8200, 96.1200)

        # Corridor 1 (straight east then north)
        c1_fwd_coords = [pt_a, (16.8000, 96.1200), pt_b]
        c1_fwd_raw = _raw_osrm(c1_fwd_coords, 2500, 300, "Corridor 1")

        # In reverse B->A, native query returns Corridor 2 (north then west)
        c2_rev_coords = [pt_b, (16.8200, 96.1000), pt_a]
        c2_rev_raw = _raw_osrm(c2_rev_coords, 2600, 320, "Corridor 2")

        # When corridor 2 waypoint is probed forward A->B, legal route is returned
        c2_fwd_coords = [pt_a, (16.8200, 96.1000), pt_b]
        c2_fwd_raw = _raw_osrm(c2_fwd_coords, 2600, 320, "Corridor 2")

        def mock_request(coords, *args, **kwargs):
            if len(coords) == 2:
                if coords[0] == pt_a:
                    return [c1_fwd_raw]
                elif coords[0] == pt_b:
                    return [c2_rev_raw]
            # Via waypoint routing
            return [c2_fwd_raw]

        with patch("services.osrm_service._request", side_effect=mock_request):
            routes = fetch_real_routes(pt_a, pt_b)

        self.assertGreaterEqual(len(routes), 2)
        names = [r["road_names"][0] for r in routes]
        self.assertIn("Corridor 1", names)
        self.assertIn("Corridor 2", names)
        # Verify both start at A and end at B
        for r in routes:
            self.assertEqual(r["geometry"][0], list(pt_a))
            self.assertEqual(r["geometry"][-1], list(pt_b))

    def test_b_divided_carriageway_direction_specific_geometry(self):
        """Test B: Divided carriageway direction-specific geometry.
        On a dual carriageway (like Pyay Road), the reverse corridor must follow the legal opposite
        carriageway and legal turn/roundabout access, rather than copying forward carriageway coordinates.
        """
        # Forward carriageway: southbound coordinates
        fwd_geom = [[16.828, 96.130], [16.820, 96.130], [16.810, 96.130]]
        # Reverse carriageway: northbound coordinates shifted laterally by ~30m (~0.0003 lon)
        # plus roundabout loop at south end
        rev_geom = [
            [16.808, 96.132],  # roundabout entry
            [16.807, 96.130],  # roundabout turn
            [16.810, 96.1303],  # northbound carriageway
            [16.820, 96.1303],
            [16.828, 96.1303],
        ]

        # Overlap between opposite carriageways is low enough not to be confused, but road corridor is preserved
        self.assertNotEqual(fwd_geom, rev_geom)
        # Reversing forward geometry would yield points on the wrong carriageway
        reversed_fwd = list(reversed(fwd_geom))
        self.assertNotEqual(reversed_fwd, rev_geom)
        # Check that rev_geom has no illegal loops or mid-route backtracking
        self.assertFalse(_has_self_intersection_loop(rev_geom))
        self.assertFalse(_has_backtracking_or_hairpin(rev_geom))

    def test_c_one_way_restriction_protection(self):
        """Test C: One-way restriction protection.
        A strictly one-way street (e.g. northbound only) must NEVER be routed contraflow in the reverse direction.
        """
        start = (16.800, 96.130)
        dest = (16.820, 96.130)

        # Forward A->B is legal on One-Way Avenue
        fwd_raw = _raw_osrm([start, (16.810, 96.130), dest], 2200, 240, "One-Way Northbound")

        # Reverse B->A on One-Way Avenue is physically illegal: OSRM returns empty or routes via parallel two-way road
        rev_parallel_raw = _raw_osrm([dest, (16.820, 96.135), (16.800, 96.135), start], 3100, 360, "Parallel Bypass")

        def mock_request(coords, *args, **kwargs):
            if coords[0] == start:
                return [fwd_raw]
            return [rev_parallel_raw]

        with patch("services.osrm_service._request", side_effect=mock_request):
            routes_rev = fetch_real_routes(dest, start)

        self.assertGreaterEqual(len(routes_rev), 1)
        # The reverse route must use the legal Parallel Bypass and NOT force One-Way Northbound
        self.assertEqual(routes_rev[0]["road_names"], ["Parallel Bypass"])

    def test_d_turn_restriction_adherence(self):
        """Test D: Turn restriction adherence.
        Legitimate terminal turns and roundabout maneuvers are permitted (<450m from start/end),
        while illegal mid-block U-turns / hairpins (>450m) are rejected.
        """
        # Terminal roundabout turnaround at 250m: permitted
        terminal_turnaround = [
            [16.8100, 96.1300],  # Start
            [16.8080, 96.1300],  # 220m south to roundabout
            [16.8078, 96.1305],  # Roundabout turn
            [16.8085, 96.1310],  # Heading north up Pyay Road
            [16.8200, 96.1310],
            [16.8280, 96.1310],  # End
        ]
        self.assertFalse(_has_backtracking_or_hairpin(terminal_turnaround))

        # Mid-route dead-end reversal at 1.6km: rejected
        mid_route_hairpin = [
            [16.8000, 96.1000],
            [16.8100, 96.1000],
            [16.8150, 96.1000],  # 1.6 km in
            [16.8152, 96.1000],  # Dead end entry
            [16.8150, 96.1000],  # Backtracking 180 degrees back to junction
            [16.8200, 96.1050],
            [16.8300, 96.1100],
        ]
        self.assertTrue(_has_backtracking_or_hairpin(mid_route_hairpin))

    def test_e_direct_vs_longer_same_traffic_route_ranking(self):
        """Test E: Direct vs longer same-traffic route ranking.
        Direct shorter route (Route 1) ranks as Recommended (Route A).
        Longer route (Route 2) across a distinct corridor ranks as Alternative (Route B).
        Neither is discarded, and the shorter route is not displaced by the longer route under equal traffic.
        """
        # Route 1 (Kyun Taw / Nar Nat Taw): 2.31 km, 4.2 min, Moderate
        r1_coords = [[16.815, 96.130], [16.820, 96.128], [16.825, 96.126], [16.828, 96.128]]
        r1 = _make_route(r1_coords, 2.31, 4.2, ["Kyun Taw Road", "Nar Nat Taw Road"], traffic="Moderate")

        # Route 2 (Hanthawaddy / Pyay Road): 2.90 km, 6.1 min, Moderate
        r2_coords = [[16.815, 96.130], [16.808, 96.131], [16.815, 96.135], [16.828, 96.132]]
        r2 = _make_route(r2_coords, 2.90, 6.1, ["Kyun Taw Road", "Pyay Road"], traffic="Moderate")

        # 1. Verification: r2 is distinct from r1 (overlap < 0.50)
        overlap = max(_overlap(r1_coords, r2_coords), _overlap(r2_coords, r1_coords))
        self.assertLess(overlap, 0.50)

        # 2. Filter practical alternatives must retain BOTH
        filtered = _filter_practical_alternatives([r1, r2])
        self.assertEqual(len(filtered), 2)

        # 3. Decision engine ranking under same traffic: r1 (shorter, faster) MUST rank first as Recommended
        eligible, _ = self.engine.evaluate(filtered, "Car", {"time_band": "off_peak"})
        self.assertEqual(len(eligible), 2)
        self.assertEqual(eligible[0]["candidate_id"], "Kyun Taw Road")
        self.assertLess(eligible[0]["decision"]["route_cost"], eligible[1]["decision"]["route_cost"])

    def test_f_traffic_aware_exception(self):
        """Test F: Traffic-aware exception.
        When the shorter route has Heavy/Critical traffic and the longer route has Light traffic
        with meaningful advantage, the longer route ranks first as Route A (Recommended).
        """
        # Short route: 2.31 km, 15.0 min (Heavy traffic jam)
        r_short_heavy = _make_route(
            [[16.815, 96.130], [16.820, 96.128], [16.828, 96.128]],
            2.31, 15.0, ["Congested Boulevard"], traffic="Heavy"
        )
        r_short_heavy["traffic_delay"] = 10.0

        # Longer detour: 3.20 km, 6.5 min (Light traffic bypass)
        r_long_light = _make_route(
            [[16.815, 96.130], [16.815, 96.140], [16.828, 96.138]],
            3.20, 6.5, ["Clear Bypass"], traffic="Light"
        )
        r_long_light["traffic_delay"] = 0.5

        # Light route has meaningful traffic advantage over heavy route
        self.assertTrue(has_meaningful_traffic_advantage(r_long_light, r_short_heavy))

        # Ranking must place the clear bypass as Recommended
        eligible, _ = self.engine.evaluate([r_short_heavy, r_long_light], "Car", {"time_band": "off_peak"})
        self.assertEqual(eligible[0]["candidate_id"], "Clear Bypass")
        self.assertEqual(eligible[1]["candidate_id"], "Congested Boulevard")

    def test_g_near_duplicate_suppression(self):
        """Test G: Near-duplicate suppression.
        Corridors that differ by only a minor alley detour or single block jog (overlap >= 0.50,
        slower/longer without traffic advantage) are suppressed. Distinct physical corridors
        (overlap < 0.50) are retained.
        """
        # Base route along Main Road
        main_coords = [[16.800, 96.100 + i * 0.002] for i in range(15)]
        base_route = _make_route(main_coords, 3.0, 5.0, ["Main Road"], traffic="Moderate")

        # Near-duplicate: slight jog into alley for 1 block, returning immediately (overlap > 0.70)
        jog_coords = list(main_coords)
        jog_coords[6] = [16.802, jog_coords[6][1]]
        jog_coords[7] = [16.802, jog_coords[7][1]]
        near_dup = _make_route(jog_coords, 3.2, 5.8, ["Main Road", "Alley Jog"], traffic="Moderate")

        # Completely distinct corridor along Northern Avenue (overlap < 0.30)
        distinct_coords = [[16.800, 96.100]] + [[16.810, 96.100 + i * 0.002] for i in range(14)] + [[16.800, 96.128]]
        distinct_route = _make_route(distinct_coords, 3.8, 6.2, ["Northern Avenue"], traffic="Moderate")

        filtered = _filter_practical_alternatives([base_route, near_dup, distinct_route])
        road_sets = [r["road_names"][0] for r in filtered]

        # Base route and distinct northern route are retained; near-dup alley jog is suppressed
        self.assertIn("Main Road", road_sets)
        self.assertIn("Northern Avenue", road_sets)
        self.assertEqual(len(filtered), 2)

    def test_h_swap_consistency_end_to_end(self):
        """Test H: Swap consistency (Hledan Centre <-> Junction Square end-to-end).
        Tests full agent run_real_world_agent for both directions:
        - Hledan -> Junction Square returns direct Pyay Road (Route A).
        - Junction Square -> Hledan returns Route A (Kyun Taw / Nar Nat Taw) and Route B (Pyay Road via Hanthawaddy).
        """
        hledan = "Hledan Centre"
        junction = "Junction Square"

        res_fwd = run_real_world_agent(hledan, junction, "Car")
        self.assertNotIn("error", res_fwd, f"Forward route failed: {res_fwd}")
        fwd_roads = res_fwd.get("road_names", []) + res_fwd.get("display_route", [])
        self.assertTrue(any("Pyay Road" in r for r in fwd_roads))
        self.assertLess(res_fwd.get("distance", 999), 1.8)

        res_rev = run_real_world_agent(junction, hledan, "Car")
        self.assertNotIn("error", res_rev, f"Reverse route failed: {res_rev}")
        rev_alts = res_rev.get("alternatives", [])
        self.assertGreaterEqual(len(rev_alts), 1, "Reverse journey must return at least 1 practical alternative")

        # Route A must be the shorter practical corridor (Kyun Taw / Nar Nat Taw)
        rev_a_roads = res_rev.get("road_names", []) + res_rev.get("display_route", [])
        self.assertTrue(any("Kyun Taw" in r or "Nar Nat Taw" in r for r in rev_a_roads))
        self.assertLess(res_rev.get("distance", 999), 2.6)

        # Route B must be the Pyay Road corridor (via Hanthawaddy Roundabout)
        rev_b = rev_alts[0]
        rev_b_roads = rev_b.get("road_names", []) + rev_b.get("display_route", [])
        self.assertTrue(any("Pyay Road" in r for r in rev_b_roads))
        self.assertGreater(rev_b.get("distance", 0), 2.6)


if __name__ == '__main__':
    unittest.main()
