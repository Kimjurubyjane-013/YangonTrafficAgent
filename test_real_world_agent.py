import unittest

from agent.real_world_agent import run_real_world_agent
from algorithms.vehicle import calculate_real_route_time
from services.osrm_service import _english_road_names
from services.route_decision_engine import RouteDecisionEngine


def fake_provider(start, destination, alternatives=3):
    return [
        {"provider_id":0,"distance":5.2,"duration":9.0,"geometry":[[16.81,96.13],[16.82,96.14]],"road_names":["Pyay Road","University Avenue"]},
        {"provider_id":1,"distance":6.0,"duration":8.0,"geometry":[[16.81,96.13],[16.815,96.15],[16.82,96.14]],"road_names":["Hledan Road","Kabar Aye Pagoda Road"]},
    ]


class RealWorldPipelineTests(unittest.TestCase):
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
        self.assertIn("0.35",result["evaluation"]["formula"])
        self.assertEqual(len(result["evaluation"]["options"]),2)


if __name__ == "__main__": unittest.main()
