import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api import Api
from web_api import app


def provider(_start, _destination, alternatives=3):
    return [{
        "provider_id": "a", "road_names": ["Pyay Road"], "distance": 5.0,
        "duration": 10.0, "base_duration": 9.0,
        "geometry": [[16.82, 96.13], [16.80, 96.15]],
        "traffic_geometry": [[[16.82, 96.13], [16.80, 96.15]]],
        "segment_traffic": [], "segment_sources": [], "traffic_data_available": False,
        "source": "OSRM", "provider": "OSRM", "retrieved_at": "test",
    }]


class RouteScenarioTests(unittest.TestCase):
    @patch("agent.real_world_agent._real_route_provider", side_effect=provider)
    def test_accident_recalculates_backend_values_and_is_simulated(self, _mock):
        api = Api()
        result = api.compare_route_scenario("Car", "Hledan Centre", "Junction Square", "accident", "Pyay Road")
        self.assertTrue(result["ok"])
        self.assertEqual(result["scenario_label"], "SIMULATED")
        self.assertFalse(result["is_live"])
        self.assertGreater(result["after"]["time"], result["before"]["time"])
        self.assertIn(result["after"]["traffic_source_label"], {"SIMULATED", "MIXED"})
        self.assertIn("incident_avoidance_penalty", result["after"]["rules_fired"])

    def test_scenario_validation(self):
        api = Api()
        self.assertEqual(api.compare_route_scenario("Car", "Hledan Centre", "Junction Square", "fake")["error_details"]["code"], "invalid_scenario")
        self.assertEqual(api.compare_route_scenario("Car", "Hledan Centre", "Junction Square", "road_closed")["error_details"]["code"], "invalid_scenario")

    def test_http_scenario_validation_contract(self):
        response = TestClient(app).post("/api/route/scenario", json={
            "vehicle": "Car", "start": "Hledan Centre", "destination": "Junction Square",
            "scenario_type": "road_closed",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_details"]["code"], "invalid_scenario")


if __name__ == "__main__":
    unittest.main()
