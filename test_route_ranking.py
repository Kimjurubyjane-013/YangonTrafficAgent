import unittest

from agent.real_world_agent import run_real_world_agent
from services.route_decision_engine import RouteDecisionEngine
from services.route_ranking import is_route_dominated


def candidate(candidate_id, distance, eta, traffic="Light", levels=None, **extra):
    levels = levels or [traffic]
    return {
        "candidate_id": candidate_id,
        "route": ["A", "D"], "display_route": ["A", "D"],
        "distance": distance, "time": eta, "traffic": traffic,
        "segment_traffic": levels, "traffic_delay": extra.pop("traffic_delay", 0),
        "traffic_score": extra.pop("traffic_score", {"Light": 25, "Moderate": 55, "Heavy": 82}[traffic]),
        "segments": [
            {"index": index, "road_class": "arterial", "traffic": level.lower(),
             "preferred": extra.pop("preferred", False), "one_way_ok": True}
            for index, level in enumerate(levels)
        ],
        **extra,
    }


class RouteRankingTests(unittest.TestCase):
    def setUp(self):
        self.engine = RouteDecisionEngine(False)

    def rank(self, *routes, vehicle="Car"):
        eligible, _ = self.engine.evaluate(list(routes), vehicle, {"time_band":"off_peak"})
        return eligible

    def test_observed_longer_slower_heavy_route_cannot_win(self):
        slower = candidate("route-a", 8.07, 17.6, "Heavy", preferred=True)
        faster = candidate("route-b", 7.32, 15.9, "Heavy")
        ranked = self.rank(slower, faster)
        self.assertEqual(ranked[0]["candidate_id"], "route-b")
        self.assertTrue(ranked[1]["decision"]["dominated"])
        self.assertTrue(is_route_dominated(slower, faster))

    def test_longer_but_substantially_faster_may_win(self):
        ranked = self.rank(
            candidate("short-slow", 5.0, 15.0, "Heavy", ["Heavy", "Heavy"]),
            candidate("long-fast", 7.0, 8.0, "Light"),
        )
        self.assertEqual(ranked[0]["candidate_id"], "long-fast")

    def test_shorter_but_much_slower_loses(self):
        ranked = self.rank(candidate("short", 4, 20, "Heavy"), candidate("fast", 6, 12, "Moderate"))
        self.assertEqual(ranked[0]["candidate_id"], "fast")

    def test_same_eta_fewer_heavy_segments_wins(self):
        ranked = self.rank(
            candidate("dirty", 6, 10, "Heavy", ["Heavy", "Heavy"]),
            candidate("cleaner", 6, 10, "Heavy", ["Heavy", "Moderate"]),
        )
        self.assertEqual(ranked[0]["candidate_id"], "cleaner")

    def test_same_eta_and_traffic_shorter_route_wins(self):
        ranked = self.rank(candidate("long", 7, 10), candidate("short", 6, 10))
        self.assertEqual(ranked[0]["candidate_id"], "short")

    def test_moderate_route_can_beat_heavy_route_with_negligible_eta_gap(self):
        ranked = self.rank(candidate("heavy", 6, 10.0, "Heavy"), candidate("moderate", 6, 10.05, "Moderate"))
        self.assertEqual(ranked[0]["candidate_id"], "moderate")

    def test_emergency_vehicle_still_rejects_dominated_route(self):
        ranked = self.rank(candidate("slow", 8, 12, "Heavy"), candidate("fast", 7, 10, "Heavy"), vehicle="Ambulance")
        self.assertEqual(ranked[0]["candidate_id"], "fast")

    def test_repeated_ranking_is_deterministic(self):
        routes = [candidate("b", 6, 10), candidate("a", 6, 10)]
        first = [item["candidate_id"] for item in self.rank(*routes)]
        second = [item["candidate_id"] for item in self.rank(*routes)]
        self.assertEqual(first, second)

    def test_real_pipeline_returns_truthful_structured_comparison(self):
        def provider(*_args, **_kwargs):
            common = {
                "base_duration": 12.0, "traffic_level":"Heavy", "segment_traffic":["Heavy"],
                "traffic_data_available":True, "traffic_source":"HERE traffic",
                "retrieved_at":"2026-08-26T10:00:00+00:00", "source":"here-traffic",
            }
            return [
                {**common,"provider_id":"a","distance":8.07,"duration":17.6,"traffic_delay":5.6,
                 "geometry":[[16.8,96.1],[16.81,96.11]],"road_names":["Long Road"]},
                {**common,"provider_id":"b","distance":7.32,"duration":15.9,"traffic_delay":3.9,
                 "geometry":[[16.8,96.1],[16.81,96.11]],"road_names":["Fast Road"]},
            ]
        result = run_real_world_agent(
            "Hledan Centre", "Myanmar Plaza", "Car", route_provider=provider,
            decision_engine=self.engine,
        )
        self.assertEqual(result["road_names"], ["Fast Road"])
        reason = result["recommendation_reason"]
        self.assertEqual(reason["primary_reason"], "lowest_traffic_adjusted_eta")
        self.assertGreater(reason["eta_advantage_minutes"], 0)
        self.assertLess(reason["distance_difference_km"], 0)
        self.assertIn("faster", reason["explanation"])
        self.assertIn("shorter", reason["explanation"])
        self.assertNotIn("slower", reason["explanation"])


if __name__ == "__main__":
    unittest.main()
