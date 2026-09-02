import unittest
from datetime import datetime
from app.runtime_config import app_timezone
from algorithms.graph import LOCATION_COORDS
from agent.real_world_agent import run_real_world_agent, _comparison_to_recommended, _recommendation_reason
from services.osrm_service import (
    fetch_real_routes, _has_self_intersection_loop, _is_practical_corridor, _is_diverse, _CACHE
)
from services.route_ranking import candidate_metrics, has_meaningful_traffic_advantage, is_route_dominated, route_cost
from services.traffic_prediction import predict_route_traffic, predict_traffic, prediction_series
from services.traffic_service import TrafficEngine


class PracticalRoutingAndTrafficTests(unittest.TestCase):
    def setUp(self):
        _CACHE.clear()

    def test_loop_detection_rejects_self_intersecting_geometry(self):
        clean = [[16.8262, 96.1304], [16.8200, 96.1310], [16.8172, 96.1314]]
        self.assertFalse(_has_self_intersection_loop(clean))

        loop = [
            [16.8262, 96.1304],
            [16.8200, 96.1310],
            [16.8180, 96.1330],
            [16.8220, 96.1320],
            [16.8190, 96.1290],
            [16.8172, 96.1314],
        ]
        self.assertTrue(_has_self_intersection_loop(loop))

    def test_traffic_first_ranking_prefers_light_over_moderate_with_small_cost(self):
        route_a = {
            "candidate_id": "route-a",
            "time": 4.0,
            "distance": 2.0,
            "traffic": "Moderate",
            "segment_traffic": ["Moderate"],
            "traffic_score": 55.0,
            "traffic_delay": 0.5,
            "heavy_segments": 0,
            "critical_segments": 0,
            "cumulative_traffic_impact": 10.0,
            "average_congestion_pressure": 0.5,
        }
        route_b = {
            "candidate_id": "route-b",
            "time": 4.5,
            "distance": 2.2,
            "traffic": "Light",
            "segment_traffic": ["Light"],
            "traffic_score": 25.0,
            "traffic_delay": 0.0,
            "heavy_segments": 0,
            "critical_segments": 0,
            "cumulative_traffic_impact": 2.0,
            "average_congestion_pressure": 0.2,
        }

        self.assertTrue(has_meaningful_traffic_advantage(route_b, route_a))
        self.assertFalse(is_route_dominated(route_b, route_a))

        cost_a, _ = route_cost(route_a, {}, "car")
        cost_b, _ = route_cost(route_b, {}, "car")
        self.assertLess(cost_b, cost_a)

    def test_traffic_first_ranking_rejects_excessive_detour_even_if_light(self):
        route_a = {
            "candidate_id": "route-a",
            "time": 4.0,
            "distance": 2.0,
            "traffic": "Moderate",
            "segment_traffic": ["Moderate"],
            "traffic_score": 55.0,
            "traffic_delay": 0.5,
            "heavy_segments": 0,
            "critical_segments": 0,
            "cumulative_traffic_impact": 10.0,
            "average_congestion_pressure": 0.5,
        }
        route_b = {
            "candidate_id": "route-b",
            "time": 12.0,
            "distance": 6.0,
            "traffic": "Light",
            "segment_traffic": ["Light"],
            "traffic_score": 25.0,
            "traffic_delay": 0.0,
            "heavy_segments": 0,
            "critical_segments": 0,
            "cumulative_traffic_impact": 2.0,
            "average_congestion_pressure": 0.2,
        }
        cost_a, _ = route_cost(route_a, {}, "car")
        cost_b, _ = route_cost(route_b, {}, "car")
        self.assertLess(cost_a, cost_b)

    def test_no_micro_comparison_sentences_generated(self):
        best = {"candidate_id": "r1", "time": 4.0, "distance": 2.0, "traffic": "Moderate", "heavy_segments": 0}
        alt = {"candidate_id": "r2", "time": 4.5, "distance": 2.17, "traffic": "Moderate", "heavy_segments": 0}
        comp = _comparison_to_recommended(best, alt)
        explanation = comp["explanation"]

        self.assertNotIn("sec", explanation.lower())
        self.assertNotIn("0.17", explanation)
        self.assertIn("similar traffic", explanation.lower())

    def test_traffic_outlook_returns_strictly_primitives_no_objects(self):
        route = {
            "time": 4.5,
            "distance": 2.2,
            "traffic": "Moderate",
            "traffic_score": 50.0,
            "traffic_delay": 0.3,
        }
        for period in ("now", "plus_30", "plus_60", "evening_rush"):
            result = predict_route_traffic(route, period)
            self.assertIsInstance(result["period"], str)
            self.assertIsInstance(result["traffic"], str)
            self.assertIsInstance(result["estimated_eta"], (int, float))
            self.assertIsInstance(result["expected_delay"], (int, float))
            self.assertIsInstance(result["reason"], str)
            self.assertNotIn("[object", str(result))
            self.assertNotIn("Expected period: Night", result["reason"])
            self.assertGreaterEqual(result["expected_delay"], 0.0)

    def test_directional_inferred_traffic_is_deterministic_and_consistent(self):
        engine = TrafficEngine()
        fixed_time = datetime(2026, 9, 2, 10, 30, 0, tzinfo=app_timezone())
        snapshot = engine.get_snapshot(at=fixed_time)

        road_id = "pyay_hledan_junction_square"
        road_state = snapshot.roads[road_id]
        self.assertIsNotNone(road_state)

        state_fwd = engine.route_state("Hledan Centre", "Junction Square", ["Pyay Road"], snapshot)
        state_rev = engine.route_state("Junction Square", "Hledan Centre", ["Pyay Road"], snapshot)

        self.assertEqual(state_fwd["traffic_level"], state_rev["traffic_level"])
        self.assertEqual(state_fwd["average_score"], state_rev["average_score"])

    def test_real_world_agent_end_to_end_has_clean_road_names_and_reasons(self):
        res = run_real_world_agent("Hledan Centre", "Junction Square", "Car")
        self.assertNotIn("error", res)
        self.assertIn("route_label", res)
        self.assertIn("display_route", res)
        self.assertIn("Pyay Road", res["display_route"])
        roads = res["display_route"]
        for i in range(len(roads) - 1):
            self.assertNotEqual(roads[i], roads[i + 1])
        self.assertTrue(len(res["recommendation_reason"]["explanation"]) > 5)
        self.assertNotIn("[object", str(res))


if __name__ == "__main__":
    unittest.main()
