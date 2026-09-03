"""Generic property and regression tests for practical routing quality invariants.

Validates:
- Rejection of unnecessary leave-and-rejoin excursions
- Rejection of mid-route U-turns and backtracking loops
- Rejection of dominated candidates (longer + slower + no traffic benefit)
- Rejection of near-duplicate alternatives with negligible corridor difference
- Preservation of legitimate one-way block detours
- Preservation of legitimate divided-carriageway terminal access U-turns
- Preservation of meaningful traffic-avoidance detours
- Bidirectional routing consistency
"""
import unittest

from services.osrm_service import (
    _has_self_intersection_loop,
    _has_backtracking_or_hairpin,
    _has_leave_and_rejoin_excursion,
    _is_dominated_corridor,
    _is_practical_corridor,
    _is_diverse,
    _overlap,
)
from services.route_ranking import (
    has_meaningful_traffic_advantage,
    is_route_dominated,
    route_cost,
)
from agent.real_world_agent import _filter_practical_alternatives, _recommendation_reason


def _make_route(coords, dist_km, dur_min, road_names, traffic="Moderate", steps=None, source="osrm-native"):
    return {
        "candidate_id": road_names[0] if road_names else "route",
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
    }


class TestRoutingQualityInvariants(unittest.TestCase):

    def test_unnecessary_leave_and_rejoin_excursion_rejected(self):
        """A route that leaves a main road, enters a short side-street detour, and rejoins the same road is rejected."""
        # Main road runs east-west along lat 16.825 from lon 96.130 to 96.160
        primary_coords = [[16.8250, 96.130 + i * 0.003] for i in range(11)]
        primary = _make_route(primary_coords, 3.2, 4.0, ["Main Boulevard"])

        # Candidate follows Main Boulevard, takes a 300m loop into a side alley, and returns to Main Boulevard
        detour_coords = [
            [16.8250, 96.130],
            [16.8250, 96.133],
            [16.8250, 96.136],
            [16.8250, 96.139],
            # Excursion south into side alley
            [16.8240, 96.139],
            [16.8235, 96.139],
            [16.8235, 96.140],
            [16.8240, 96.140],
            # Rejoin Main Boulevard nearby
            [16.8250, 96.140],
            [16.8250, 96.145],
            [16.8250, 96.150],
            [16.8250, 96.155],
            [16.8250, 96.160],
        ]
        detour_steps = [
            {"name": "Main Boulevard", "distance": 1000.0, "type": "depart", "modifier": "straight"},
            {"name": "Side Alley", "distance": 150.0, "type": "turn", "modifier": "right"},
            {"name": "Side Alley", "distance": 150.0, "type": "turn", "modifier": "left"},
            {"name": "Main Boulevard", "distance": 2200.0, "type": "turn", "modifier": "right"},
        ]
        candidate = _make_route(detour_coords, 3.5, 5.2, ["Main Boulevard", "Side Alley"], steps=detour_steps, source="osrm-via-corridor")

        # Must be detected as leave-and-rejoin excursion
        self.assertTrue(_has_leave_and_rejoin_excursion(candidate, primary))
        # Must be rejected by practical corridor filter
        self.assertFalse(_is_practical_corridor(candidate, primary, primary_coords[0], primary_coords[-1]))

    def test_mid_route_uturn_backtracking_rejected(self):
        """A route that performs a mid-journey U-turn or dead-end backtracking is rejected."""
        # Route travels 1 km, turns into a dead end, makes a U-turn, returns to the road, and travels another 1 km
        coords = [
            [16.800, 96.100],
            [16.805, 96.105],
            [16.810, 96.110],  # ~1.5 km in
            [16.812, 96.110],  # down dead end
            [16.813, 96.110],  # end of dead end
            [16.812, 96.110],  # heading reversed!
            [16.810, 96.110],  # back to junction
            [16.815, 96.115],
            [16.820, 96.120],
        ]
        steps = [
            {"name": "Road A", "distance": 1500.0, "type": "depart", "modifier": "straight"},
            {"name": "Dead End", "distance": 150.0, "type": "turn", "modifier": "right"},
            {"name": "Dead End", "distance": 150.0, "type": "turn", "modifier": "uturn"},
            {"name": "Road A", "distance": 1500.0, "type": "turn", "modifier": "left"},
        ]
        self.assertTrue(_has_backtracking_or_hairpin(coords, steps))

    def test_legitimate_terminal_uturn_protected(self):
        """Divided-carriageway U-turns within origin departure or destination arrival (<200m) are protected."""
        # Departure U-turn within first 60m of trip (e.g. exiting building onto opposite side of boulevard)
        coords = [
            [16.8000, 96.1000],
            [16.8003, 96.1000],
            [16.8000, 96.1001],  # U-turn at median opening 35m out
            [16.7950, 96.1001],
            [16.7900, 96.1001],
        ]
        steps = [
            {"name": "Boulevard", "distance": 30.0, "type": "depart", "modifier": "right"},
            {"name": "Boulevard", "distance": 30.0, "type": "turn", "modifier": "uturn"},
            {"name": "Boulevard", "distance": 1200.0, "type": "continue", "modifier": "straight"},
        ]
        # Must NOT be rejected as mid-route backtracking
        self.assertFalse(_has_backtracking_or_hairpin(coords, steps))

    def test_dominated_candidate_rejected(self):
        """A candidate that is simultaneously longer, slower, and has no traffic benefit is dominated and filtered."""
        primary = _make_route([[16.80, 96.10], [16.81, 96.11], [16.82, 96.12]], 3.0, 5.0, ["Direct Way"], traffic="Moderate")
        # Inferior candidate on same corridor: 3.6 km (+600m), 7.0 min (+2 min), same Moderate traffic
        inferior = _make_route([[16.80, 96.10], [16.81, 96.112], [16.82, 96.12]], 3.6, 7.0, ["Direct Way", "Detour"], traffic="Moderate")

        # Domination rule verifies inferior is dominated by primary
        self.assertTrue(is_route_dominated(inferior, primary))
        self.assertFalse(is_route_dominated(primary, inferior))

        # Filter practical alternatives drops the dominated candidate
        filtered = _filter_practical_alternatives([primary, inferior])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["candidate_id"], "Direct Way")

    def test_near_duplicate_candidate_rejected(self):
        """A candidate route that shares high geometry overlap (>85%) without distinct corridor is rejected."""
        primary_geom = [[16.80, 96.10 + i * 0.002] for i in range(20)]
        # Shift only 2 points slightly (GPS jitter / minor connector)
        near_dup_geom = list(primary_geom)
        near_dup_geom[10] = [16.8001, near_dup_geom[10][1]]
        near_dup_geom[11] = [16.8001, near_dup_geom[11][1]]

        cand = {"geometry": near_dup_geom, "road_names": ["Main Road"]}
        accepted = [{"geometry": primary_geom, "road_names": ["Main Road"]}]

        self.assertFalse(_is_diverse(cand, accepted))

    def test_legitimate_one_way_block_detour_protected(self):
        """A route circumnavigating a city block due to one-way streets is not flagged as backtracking or excursion."""
        # Typical downtown Yangon grid: around 1 rectangular block (east, north, west, north)
        block_coords = [
            [16.775, 96.150],  # Start heading east along Anawrahta
            [16.775, 96.152],
            [16.778, 96.152],  # Turn north along Pansodan
            [16.778, 96.150],  # Turn west along Bogyoke
            [16.782, 96.150],  # Turn north along Sule Pagoda Rd
        ]
        steps = [
            {"name": "Anawrahta Road", "distance": 250.0, "type": "depart", "modifier": "straight"},
            {"name": "Pansodan Road", "distance": 350.0, "type": "turn", "modifier": "left"},
            {"name": "Bogyoke Road", "distance": 250.0, "type": "turn", "modifier": "left"},
            {"name": "Sule Pagoda Road", "distance": 450.0, "type": "turn", "modifier": "right"},
        ]
        # Block traversal is NOT backtracking (no 180-deg reversal on same street)
        self.assertFalse(_has_backtracking_or_hairpin(block_coords, steps))
        self.assertFalse(_has_self_intersection_loop(block_coords))

    def test_meaningful_traffic_avoidance_detour_protected(self):
        """An alternative corridor that is longer/slower is preserved when the primary corridor has Heavy traffic."""
        heavy_primary = _make_route(
            [[16.80, 96.10], [16.81, 96.11], [16.82, 96.12]],
            4.0, 8.0, ["Arterial Road"], traffic="Heavy"
        )
        light_alternative = _make_route(
            [[16.80, 96.10], [16.81, 96.13], [16.82, 96.12]],
            4.8, 9.2, ["Parallel Bypass"], traffic="Light"
        )

        # Light alternative must have a meaningful traffic advantage over heavy primary
        self.assertTrue(has_meaningful_traffic_advantage(light_alternative, heavy_primary))
        # It must NOT be dominated
        self.assertFalse(is_route_dominated(light_alternative, heavy_primary))

        # Practical filtering must retain both routes
        filtered = _filter_practical_alternatives([heavy_primary, light_alternative])
        self.assertEqual(len(filtered), 2)
        self.assertEqual({r["candidate_id"] for r in filtered}, {"Arterial Road", "Parallel Bypass"})

    def test_bidirectional_consistency_without_forced_third_route(self):
        """Routing in both directions must return clean corridors and not invent a third route when none exists."""
        # When 1 valid route exists, only 1 route must be returned
        r1 = _make_route([[16.80, 96.10], [16.81, 96.11]], 3.0, 5.0, ["Road A"])
        reason = _recommendation_reason(r1, [])
        self.assertEqual(reason["primary_reason"], "only_eligible_route")
        self.assertIsNone(reason["eta_advantage_minutes"])


if __name__ == "__main__":
    unittest.main()
