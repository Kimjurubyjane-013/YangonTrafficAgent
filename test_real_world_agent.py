import unittest
from unittest.mock import patch

from agent.real_world_agent import _coverage_from_sources, _weighted_level, run_real_world_agent
from algorithms.vehicle import calculate_real_route_time
from services.osrm_service import _english_road_names
from services.route_decision_engine import RouteDecisionEngine


def fake_provider(start, destination, alternatives=3):
    return [
        {"provider_id":0,"distance":5.2,"duration":9.0,"geometry":[[16.81,96.13],[16.82,96.14]],"road_names":["Pyay Road","University Avenue"]},
        {"provider_id":1,"distance":6.0,"duration":8.0,"geometry":[[16.81,96.13],[16.815,96.15],[16.82,96.14]],"road_names":["Hledan Road","Kabar Aye Pagoda Road"]},
    ]


class RealWorldPipelineTests(unittest.TestCase):
    def setUp(self):
        # Legacy provider fixtures do not contain live traffic evidence. Their
        # academic expectations are tested in the explicit simulation mode.
        self._mode = patch.dict("os.environ", {"TRAFFIC_MODE": "simulation"})
        self._mode.start()

    def tearDown(self):
        self._mode.stop()

    def test_requested_route_matrix_keeps_complete_trust_contract(self):
        journeys = [
            ("Hledan Centre", "Junction Square"),
            ("Myanmar Plaza", "Yangon General Hospital"),
            ("Yangon Airport", "Sule Pagoda"),
            ("Yangon Airport", "Junction City"),
        ]
        for start, destination in journeys:
            with self.subTest(start=start, destination=destination):
                result = run_real_world_agent(
                    start, destination, "Car", route_provider=fake_provider,
                    decision_engine=RouteDecisionEngine(False),
                )
                self.assertNotIn("error", result)
                self.assertEqual(result["route"], [start, destination])
                self.assertTrue(result["geometry"])
                self.assertTrue(result["alternatives"])
                self.assertIn(result["traffic"], {"Light", "Moderate", "Heavy"})
                # Source is now "Inferred Traffic Model" (was "Academic Simulation")
                self.assertIn(result["traffic_source"], ("Academic Simulation", "Inferred Traffic Model"))
                self.assertTrue(result["recommendation_reason"]["explanation"])

    def test_english_names_are_clean_and_deduplicated(self):
        route={"legs":[{"steps":[
            {"name":"နတ်မောက်လမ်း - Nar Nat Taw Road"},
            {"name":"Nar Nat Taw Road"},
            {"name":"ကမ္ဘာအေးဘုရားလမ်း"},
            {"name":"Hanthawaddy Road"},
            {"name":"Hanthawaddy Road"},
        ]}]}
        self.assertEqual(_english_road_names(route),["Nar Nat Taw Road","Hanthawaddy Road"])

    def test_vehicle_durations_are_distinct_and_realistic(self):
        car=calculate_real_route_time(10,8,"Car")
        bus=calculate_real_route_time(10,8,"Bus")
        ambulance=calculate_real_route_time(10,8,"Ambulance")
        fire=calculate_real_route_time(10,8,"Fire Truck")
        self.assertGreater(bus,car)
        self.assertLess(ambulance,car)
        self.assertGreater(fire,ambulance)
        self.assertEqual(len({car,bus,ambulance,fire}),4)

    def test_traffic_increases_real_route_eta(self):
        light=calculate_real_route_time(10,8,"Car","Light")
        moderate=calculate_real_route_time(10,8,"Car","Moderate")
        heavy=calculate_real_route_time(10,8,"Car","Heavy")
        self.assertLess(light,moderate)
        self.assertLess(moderate,heavy)

    def test_provider_routes_are_returned_without_graph_waypoints(self):
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",route_provider=fake_provider,decision_engine=RouteDecisionEngine(False))
        self.assertNotIn("error",result)
        self.assertEqual(result["routing_mode"],"real-world-only")
        self.assertEqual(result["route"],["Hledan Centre","Myanmar Plaza"])
        self.assertTrue(result["geometry"])
        self.assertTrue(result["alternatives"][0]["geometry"])
        self.assertIn("Pyay Road",result["display_route"]+result["alternatives"][0]["display_route"])
        self.assertIn(result["traffic"], {"Light", "Moderate", "Heavy"})
        self.assertFalse(result["traffic_data_available"])
        self.assertTrue(result["traffic_model_available"])
        self.assertTrue(result["traffic_snapshot_id"])
        # Source is now "Inferred Traffic Model" (was "Academic Simulation")
        self.assertIn(result["traffic_source"], ("Academic Simulation", "Inferred Traffic Model"))
        # Notice mentions HERE unavailability
        self.assertIn("here", result["provider_notice"].lower())

    def test_internal_provider_labels_are_not_displayed_as_roads(self):
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",route_provider=fake_provider,decision_engine=RouteDecisionEngine(False))
        displayed=" ".join(result["display_route"])
        self.assertNotIn("corridor",displayed.lower())
        self.assertNotIn("osrm alternative",displayed.lower())

    def test_provider_failure_is_non_graph_error(self):
        def failed(*args,**kwargs): raise RuntimeError("offline")
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",route_provider=failed)
        self.assertIn("error",result)
        self.assertEqual(result["routing_mode"],"real-world-only")

    def test_closed_road_excludes_only_matching_real_candidate(self):
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",
            {"closed_road":"Pyay Rd"},route_provider=fake_provider,decision_engine=RouteDecisionEngine(False))
        self.assertNotIn("error",result)
        self.assertIn("Hledan Road",result["road_names"])
        self.assertNotIn("Pyay Road",result["road_names"])
        self.assertEqual(result["evaluation"]["closure"]["matched_routes"],1)

    def test_unmatched_closure_is_reported_without_false_reroute_claim(self):
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",
            {"closed_road":"Bogyoke Aung San Road"},route_provider=fake_provider,decision_engine=RouteDecisionEngine(False))
        self.assertNotIn("error",result)
        self.assertEqual(result["evaluation"]["closure"]["matched_routes"],0)

    def test_all_routes_closed_returns_explicit_error(self):
        def blocked_provider(*args, **kwargs):
            routes=fake_provider(*args, **kwargs)
            for route in routes: route["road_names"]=["Pyay Road"]
            return routes
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",
            {"closed_road":"Pyay Road"},route_provider=blocked_provider,decision_engine=RouteDecisionEngine(False))
        self.assertIn("error",result)
        self.assertEqual(result["evaluation"]["eligible_candidates"],0)

    def test_evaluation_exposes_formula_and_ranked_options(self):
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",route_provider=fake_provider,
            decision_engine=RouteDecisionEngine(False))
        self.assertIn("traffic_adjusted_eta",result["evaluation"]["formula"])
        self.assertEqual(len(result["evaluation"]["options"]),2)

    def test_longer_route_wins_when_real_traffic_eta_is_lower(self):
        def traffic_provider(*args, **kwargs):
            return [
                {"provider_id":0,"distance":5.0,"duration":15.0,"base_duration":5.0,
                    "traffic_delay":10.0,"traffic_level":"Heavy","segment_traffic":["Heavy"],
                    "traffic_data_available":True,"traffic_source":"HERE live and historical traffic",
                    "retrieved_at":"2026-08-18T10:00:00+00:00","source":"here-traffic",
                    "geometry":[[16.81,96.13],[16.82,96.14]],"road_names":["Congested Road"]},
                {"provider_id":1,"distance":7.0,"duration":8.0,"base_duration":7.0,
                    "traffic_delay":1.0,"traffic_level":"Light","segment_traffic":["Light"],
                    "traffic_data_available":True,"traffic_source":"HERE live and historical traffic",
                    "retrieved_at":"2026-08-18T10:00:00+00:00","source":"here-traffic",
                    "geometry":[[16.81,96.13],[16.815,96.16],[16.82,96.14]],"road_names":["Clear Bypass"]},
            ]
        result=run_real_world_agent("Hledan Centre","Myanmar Plaza","Car",
            route_provider=traffic_provider,decision_engine=RouteDecisionEngine(False))
        self.assertEqual(result["road_names"],["Clear Bypass"])
        self.assertEqual(result["traffic_source"],"HERE Real-Time Traffic")
        self.assertTrue(result["traffic_data_available"])
        self.assertEqual(result["base_duration"], 7.0)
        self.assertEqual(result["traffic_time"], 8.0)
        self.assertEqual(result["traffic_delay"], 1.0)
        self.assertIsNone(result["provider_notice"])

    def test_hybrid_segment_contract_and_exact_coverage(self):
        self.assertEqual(_coverage_from_sources(["HERE", "INFERRED", "UNKNOWN"]), (33.3, 33.3, 33.4))
        level, score = _weighted_level(
            ["Heavy", "Light"],
            [[[16.8, 96.1], [16.8001, 96.1]], [[16.8, 96.1], [16.81, 96.1]]],
        )
        self.assertEqual(level, "Light")
        self.assertLess(score, 35)

    def test_partial_provider_route_is_labelled_mixed(self):
        def provider(*_args, **_kwargs):
            return [{"provider_id": 0, "distance": 4.0, "duration": 8.0,
                "traffic_level": "Moderate", "segment_traffic": ["Moderate", "Unknown"],
                "segment_sources": ["HERE", "UNKNOWN"], "traffic_data_available": True,
                "geometry": [[16.8262, 96.13049], [16.8172, 96.1314]],
                "traffic_geometry": [[[16.8262, 96.13049], [16.822, 96.131]],
                                     [[16.822, 96.131], [16.8172, 96.1314]]],
                "road_names": ["Pyay Road"], "source": "here-traffic"}]
        result = run_real_world_agent("Hledan Centre", "Junction Square", "Car",
            route_provider=provider, decision_engine=RouteDecisionEngine(False))
        self.assertEqual(result["traffic_source_label"], "MIXED")
        self.assertEqual(result["segment_sources"], ["HERE", "INFERRED"])
        self.assertEqual(result["provider_coverage_percent"], 50.0)
        self.assertEqual(result["inferred_coverage_percent"], 50.0)
        self.assertEqual(result["unknown_coverage_percent"], 0.0)

    def test_displayed_delay_never_exceeds_adjusted_eta(self):
        result = run_real_world_agent("Hledan Centre", "Myanmar Plaza", "Car",
            route_provider=fake_provider, decision_engine=RouteDecisionEngine(False))
        for option in [result, *result["alternatives"]]:
            self.assertGreaterEqual(option["traffic_delay"], 0)
            self.assertLessEqual(option["traffic_delay"], option["traffic_adjusted_eta"])
            self.assertAlmostEqual(option["traffic_delay"],
                max(0, option["traffic_adjusted_eta"] - option["free_flow_eta"]), places=2)

    def test_best_and_alternatives_share_normalized_contract(self):
        result = run_real_world_agent("Hledan Centre", "Myanmar Plaza", "Car",
            route_provider=fake_provider, decision_engine=RouteDecisionEngine(False))
        fields = {"route_id", "geometry", "road_names", "distance", "free_flow_eta",
                  "traffic_adjusted_eta", "traffic_delay", "overall_traffic",
                  "segment_traffic", "traffic_source", "provider_coverage",
                  "route_cost", "recommendation_reason", "direction_summary"}
        for option in [result, *result["alternatives"]]:
            self.assertTrue(fields.issubset(option))
            self.assertEqual(option["overall_traffic"], option["traffic"])
            self.assertEqual(option["direction_summary"]["origin"], "Hledan Centre")


if __name__ == "__main__": unittest.main()
