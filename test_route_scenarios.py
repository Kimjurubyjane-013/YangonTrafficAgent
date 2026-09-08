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
    def test_heavy_rain_recalculates_backend_values_and_is_simulated(self, _mock):
        api = Api()
        result = api.compare_route_scenario("Car", "Hledan Centre", "Junction Square", "heavy_rain")
        self.assertTrue(result["ok"])
        self.assertEqual(result["scenario_label"], "SIMULATED")
        self.assertFalse(result["is_live"])
        self.assertIn(result["after"]["traffic_source_label"], {"SIMULATED", "MIXED"})

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

    @patch("agent.real_world_agent._real_route_provider", side_effect=provider)
    def test_canonical_scenarios_contract_http_route(self, _mock):
        client = TestClient(app)
        scenarios = [
            ("Normal Conditions", "current"),
            ("Heavy Rain", "heavy_rain"),
            ("Rush Hour", "peak"),
            ("Off-Peak Hours", "off_peak"),
        ]
        for label, canonical in scenarios:
            # Dict conditions with traffic_scenario
            resp = client.post("/api/route", json={
                "vehicle": "Car", "start": "Hledan Centre", "destination": "Junction Square",
                "conditions": {"traffic_scenario": canonical},
            })
            self.assertEqual(resp.status_code, 200, f"{label} -> {canonical} dict failed with {resp.text}")
            data = resp.json()
            self.assertTrue(data.get("ok"), f"{label} -> {canonical} did not return ok: True")
            self.assertNotIn("Unknown scenario type.", resp.text)

            # String conditions
            resp_str = client.post("/api/route", json={
                "vehicle": "Car", "start": "Hledan Centre", "destination": "Junction Square",
                "conditions": canonical,
            })
            self.assertEqual(resp_str.status_code, 200, f"{label} -> {canonical} str failed with {resp_str.text}")
            self.assertNotIn("Unknown scenario type.", resp_str.text)

        # Invalid scenario must be rejected
        resp_invalid = client.post("/api/route", json={
            "vehicle": "Car", "start": "Hledan Centre", "destination": "Junction Square",
            "conditions": {"traffic_scenario": "invalid_scenario"},
        })
        self.assertEqual(resp_invalid.status_code, 400)
        self.assertEqual(resp_invalid.json().get("error_details", {}).get("code"), "invalid_scenario")

        # Harmless aliases must be normalized and accepted
        aliases = [
            ("normal", "current"),
            ("normal_conditions", "current"),
            ("rush_hour", "peak"),
            ("offpeak", "off_peak"),
        ]
        for alias, canonical in aliases:
            resp_alias = client.post("/api/route", json={
                "vehicle": "Car", "start": "Hledan Centre", "destination": "Junction Square",
                "conditions": {"traffic_scenario": alias},
            })
            self.assertEqual(resp_alias.status_code, 200)
            self.assertEqual(resp_alias.json().get("traffic_scenario"), canonical)

    @patch("agent.real_world_agent._real_route_provider", side_effect=provider)
    def test_canonical_scenarios_contract_http_scenario(self, _mock):
        client = TestClient(app)
        for canonical in ("current", "heavy_rain", "peak", "off_peak"):
            resp = client.post("/api/route/scenario", json={
                "vehicle": "Car", "start": "Hledan Centre", "destination": "Junction Square",
                "scenario_type": canonical,
            })
            self.assertEqual(resp.status_code, 200, f"scenario_type: {canonical} failed with {resp.text}")
            self.assertTrue(resp.json().get("ok"))
            self.assertNotIn("Unknown scenario type.", resp.text)

        # Invalid scenario must be rejected
        resp_invalid = client.post("/api/route/scenario", json={
            "vehicle": "Car", "start": "Hledan Centre", "destination": "Junction Square",
            "scenario_type": "invalid_scenario",
        })
        self.assertEqual(resp_invalid.status_code, 400)
        self.assertEqual(resp_invalid.json().get("error_details", {}).get("code"), "invalid_scenario")

    @patch("agent.real_world_agent._real_route_provider", side_effect=provider)
    def test_normal_conditions_regression_no_unknown_scenario_error(self, _mock):
        api = Api()
        # Direct find_route with current, normal, and normal_conditions
        for val in ("current", "normal", "normal_conditions", None):
            res = api.find_route("Car", "Hledan Centre", "Junction Square", {"traffic_scenario": val} if val else None)
            self.assertTrue(res.get("ok"))
            self.assertNotIn("error", res)
            self.assertNotIn("Unknown scenario type.", str(res))

        # compare_route_scenario with current
        res_comp = api.compare_route_scenario("Car", "Hledan Centre", "Junction Square", "current")
        self.assertTrue(res_comp.get("ok"))
        self.assertNotIn("error", res_comp)
        self.assertNotIn("Unknown scenario type.", str(res_comp))


if __name__ == "__main__":
    unittest.main()
