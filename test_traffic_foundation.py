import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from agent.traffic_agent import run_traffic_agent
from algorithms.graph import GRAPH
from api import Api
from services.road_repository import ROAD_REPOSITORY, RoadDataError, RoadRepository
from services.route_decision_engine import RouteDecisionEngine
from services.traffic_service import (
    TrafficEngine, classify_traffic, get_time_period, is_rush_hour,
    traffic_health_label,
)


class TrafficFoundationTests(unittest.TestCase):
    def setUp(self):
        self.engine = TrafficEngine(ROAD_REPOSITORY)
        self.daytime = datetime(2026, 8, 26, 12, 7)

    def test_time_period_boundaries_and_rush_hour(self):
        cases = [
            (datetime(2026,1,1,5,0), "EARLY_MORNING"),
            (datetime(2026,1,1,7,0), "MORNING_RUSH"),
            (datetime(2026,1,1,9,30), "DAYTIME"),
            (datetime(2026,1,1,16,0), "EVENING_RUSH"),
            (datetime(2026,1,1,19,30), "NIGHT"),
            (datetime(2026,1,1,2,0), "NIGHT"),
        ]
        for value, expected in cases:
            self.assertEqual(get_time_period(value), expected)
        self.assertTrue(is_rush_hour(datetime(2026,1,1,8,0)))
        self.assertFalse(is_rush_hour(datetime(2026,1,1,12,0)))

    def test_classification_thresholds(self):
        for score, expected in ((0,"Light"),(35,"Light"),(36,"Moderate"),(70,"Moderate"),(71,"Heavy"),(100,"Heavy")):
            self.assertEqual(classify_traffic(score), expected)

    def test_all_roads_have_bounded_explainable_analysis(self):
        snapshot = self.engine.get_snapshot(self.daytime)
        self.assertEqual(len(snapshot.roads), len(ROAD_REPOSITORY.roads))
        for state in snapshot.roads.values():
            self.assertGreaterEqual(state.traffic_score, 0)
            self.assertLessEqual(state.traffic_score, 100)
            self.assertGreater(state.average_speed_kmh, 0)
            self.assertGreaterEqual(state.estimated_delay_minutes, 0)
            self.assertTrue(state.reasons)
            self.assertEqual(classify_traffic(state.traffic_score), state.traffic_level)

    def test_snapshot_is_repeatable_and_internally_consistent(self):
        first = self.engine.get_snapshot(self.daytime)
        second = self.engine.get_snapshot(datetime(2026,8,26,12,14))
        self.assertIs(first, second)
        route = self.engine.route_state("Hledan Centre", "Myanmar Plaza", ["Pyay Road"], first)
        for road_id, level in zip(route["road_ids"], route["segment_traffic"]):
            self.assertEqual(level, first.roads[road_id].traffic_level)

    def test_overview_works_without_route_request(self):
        overview = self.engine.overview(self.daytime)
        self.assertEqual(overview["total_roads"], len(ROAD_REPOSITORY.roads))
        self.assertEqual(overview["light_count"] + overview["moderate_count"] + overview["heavy_count"], overview["total_roads"])
        self.assertEqual(overview["model_type"], "academic_simulation")
        self.assertTrue(overview["most_congested"])
        self.assertTrue(overview["best_flowing"])
        self.assertGreaterEqual(overview["traffic_health_score"], 0)
        self.assertLessEqual(overview["traffic_health_score"], 100)
        self.assertEqual(overview["source"], "academic_simulation")
        self.assertIn(overview["traffic_health_label"], {"Excellent", "Good", "Moderate", "Poor", "Severe"})

    def test_phase_two_network_size_context_and_connectivity(self):
        self.assertGreaterEqual(len(ROAD_REPOSITORY.locations), 25)
        self.assertLessEqual(len(ROAD_REPOSITORY.locations), 35)
        self.assertGreaterEqual(len(ROAD_REPOSITORY.roads), 30)
        self.assertLessEqual(len(ROAD_REPOSITORY.roads), 45)
        self.assertNotIn("Hledan Junction", ROAD_REPOSITORY.locations)
        self.assertEqual(len(ROAD_REPOSITORY.by_id), len(ROAD_REPOSITORY.roads))
        for road in ROAD_REPOSITORY.roads:
            self.assertGreaterEqual(road.commercial_activity, 0)
            self.assertLessEqual(road.commercial_activity, 1)
            self.assertGreaterEqual(road.rush_hour_sensitivity, 0.5)

    def test_hotspot_and_best_flow_rankings_are_deterministic(self):
        snapshot = self.engine.get_snapshot(self.daytime)
        first_hotspots = self.engine.congestion_hotspots(snapshot, 6)
        second_hotspots = self.engine.congestion_hotspots(snapshot, 6)
        self.assertEqual(first_hotspots, second_hotspots)
        self.assertEqual(
            [item["hotspot_rank_score"] for item in first_hotspots],
            sorted((item["hotspot_rank_score"] for item in first_hotspots), reverse=True),
        )
        best = self.engine.best_flowing_roads(snapshot, 6)
        self.assertEqual(
            [item["flow_rank_score"] for item in best],
            sorted(item["flow_rank_score"] for item in best),
        )

    def test_trend_and_pressure_are_bounded_and_explained(self):
        snapshot = self.engine.get_snapshot(self.daytime)
        for state in snapshot.roads.values():
            self.assertGreaterEqual(state.congestion_pressure, 0)
            self.assertLessEqual(state.congestion_pressure, 1.5)
            self.assertIn(state.trend, {"worsening", "improving", "stable"})
            self.assertTrue(state.summary_reason)
            self.assertEqual(state.source, "academic_simulation")
        for score, label in ((90, "Excellent"), (75, "Good"), (55, "Moderate"), (35, "Poor"), (10, "Severe")):
            self.assertEqual(traffic_health_label(score), label)

    def test_api_road_lookup_is_safe(self):
        api = Api(traffic_engine=self.engine)
        overview = api.get_traffic_overview()
        road_id = overview["roads"][0]["road_id"]
        self.assertEqual(api.get_road_traffic(road_id)["road_id"], road_id)
        self.assertEqual(api.get_road_traffic("missing")["error_details"]["code"], "unknown_road")
        self.assertEqual(api.get_road_traffic(None)["error_details"]["code"], "invalid_road_id")

    def test_legacy_route_uses_the_shared_snapshot(self):
        snapshot = self.engine.get_snapshot(self.daytime)
        result = run_traffic_agent(
            "Hledan Centre", "Myanmar Plaza", "Car",
            decision_engine=RouteDecisionEngine(False),
            traffic_engine=self.engine, traffic_snapshot=snapshot,
        )
        self.assertNotIn("error", result)
        expected = []
        for start, end in zip(result["route"], result["route"][1:]):
            road = ROAD_REPOSITORY.by_edge[(start, end)]
            expected.append(snapshot.roads[road.id].traffic_level)
        self.assertEqual(result["segment_traffic"], expected)

    def test_repository_rejects_malformed_and_empty_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            locations = root / "locations.json"
            roads = root / "roads.json"
            locations.write_text(json.dumps([{"name":"A","lat":1,"lon":2}]), encoding="utf-8")
            roads.write_text("[]", encoding="utf-8")
            with self.assertRaises(RoadDataError):
                RoadRepository(roads, locations)

    def test_repository_skips_one_bad_road_when_valid_data_remains(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            locations = root / "locations.json"
            roads = root / "roads.json"
            locations.write_text(json.dumps([
                {"name":"A","lat":1,"lon":2}, {"name":"B","lat":1.001,"lon":2.001}
            ]), encoding="utf-8")
            valid = {"id":"valid","from":"A","to":"B","road_name":"Main Road","road_type":"main","distance_km":1,"base_congestion":40}
            roads.write_text(json.dumps([valid, {"id":"bad","from":"A"}]), encoding="utf-8")
            repository = RoadRepository(roads, locations)
            self.assertEqual([road.id for road in repository.roads], ["valid"])
            self.assertTrue(repository.errors)
            roads.write_text(json.dumps([{"id":"x","from":"A","to":"B","road_name":"Bad","road_type":"unknown","distance_km":1,"base_congestion":10}]), encoding="utf-8")
            with self.assertRaises(RoadDataError):
                RoadRepository(roads, locations)

    def test_repository_rejects_disconnected_network_and_bad_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            locations = root / "locations.json"
            roads = root / "roads.json"
            locations.write_text(json.dumps([
                {"name":"A","lat":1,"lon":2}, {"name":"B","lat":1.001,"lon":2.001},
                {"name":"C","lat":1.002,"lon":2.002},
            ]), encoding="utf-8")
            roads.write_text(json.dumps([
                {"id":"ab","from":"A","to":"B","road_name":"Main Road","road_type":"main","distance_km":1,"base_congestion":40}
            ]), encoding="utf-8")
            with self.assertRaisesRegex(RoadDataError, "disconnected"):
                RoadRepository(roads, locations)
            locations.write_text(json.dumps([
                {"name":"A","lat":1,"lon":2}, {"name":"B","lat":1.001,"lon":2.001},
            ]), encoding="utf-8")
            roads.write_text(json.dumps([
                {"id":"ab","from":"A","to":"B","road_name":"Main Road","road_type":"main","distance_km":1,"base_congestion":40,"bidirectional":"false"}
            ]), encoding="utf-8")
            with self.assertRaises(RoadDataError):
                RoadRepository(roads, locations)

    def test_lower_capacity_increases_congestion_pressure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            locations = root / "locations.json"
            roads = root / "roads.json"
            locations.write_text(json.dumps([
                {"name":"A","lat":1,"lon":2}, {"name":"B","lat":1.001,"lon":2.001},
                {"name":"C","lat":1.002,"lon":2.002},
            ]), encoding="utf-8")
            common = {"road_name":"Test Road","road_type":"main","distance_km":1,"base_speed_kmh":40,"base_congestion":55}
            roads.write_text(json.dumps([
                {**common,"id":"low","from":"A","to":"B","capacity":35},
                {**common,"id":"high","from":"B","to":"C","capacity":90},
            ]), encoding="utf-8")
            snapshot = TrafficEngine(RoadRepository(roads, locations)).get_snapshot(self.daytime)
            self.assertGreater(snapshot.roads["low"].congestion_pressure, snapshot.roads["high"].congestion_pressure)
            self.assertGreater(snapshot.roads["low"].traffic_score, snapshot.roads["high"].traffic_score)

    def test_graph_is_derived_from_road_repository(self):
        for road in ROAD_REPOSITORY.roads:
            self.assertEqual(GRAPH[road.start][road.end], road.distance_km)
            if road.bidirectional:
                self.assertEqual(GRAPH[road.end][road.start], road.distance_km)


if __name__ == "__main__":
    unittest.main()
