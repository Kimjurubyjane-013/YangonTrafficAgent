import importlib.util
import unittest


HTTP_TEST_AVAILABLE = (
    importlib.util.find_spec("fastapi") is not None
    and importlib.util.find_spec("httpx") is not None
)


@unittest.skipUnless(HTTP_TEST_AVAILABLE, "FastAPI/httpx test dependencies are not installed")
class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from web_api import app

        cls.client = TestClient(app)

    def test_health_and_reference_data(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        self.assertIn("Hledan Centre", self.client.get("/api/locations").json())
        self.assertIn("Car", self.client.get("/api/vehicles").json())
        graph = self.client.get("/api/graph").json()
        self.assertIn("coords", graph)
        self.assertIn("edges", graph)
        self.assertIn("roads", graph)

    def test_traffic_overview_and_road_detail(self):
        overview = self.client.get("/api/traffic")
        self.assertEqual(overview.status_code, 200)
        payload = overview.json()
        self.assertGreater(payload["total_roads"], 0)
        road_id = payload["roads"][0]["road_id"]
        detail = self.client.get(f"/api/traffic/{road_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["road_id"], road_id)
        self.assertEqual(self.client.get("/api/traffic/not-a-road").status_code, 404)

    def test_phase_two_ranked_traffic_endpoints(self):
        hotspots = self.client.get("/api/traffic/hotspots?limit=3")
        self.assertEqual(hotspots.status_code, 200)
        self.assertEqual(len(hotspots.json()["hotspots"]), 3)
        self.assertEqual(hotspots.json()["source"], "academic_simulation")
        best = self.client.get("/api/traffic/best-flowing?limit=4")
        self.assertEqual(best.status_code, 200)
        self.assertEqual(len(best.json()["roads"]), 4)

    def test_invalid_route_is_structured_http_error(self):
        response = self.client.post("/api/route", json={
            "vehicle": "Jet", "start": "Hledan Centre", "destination": "Inya Lake",
            "conditions": {},
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_details"]["code"], "unknown_vehicle")

    def test_valid_route_uses_existing_facade_contract(self):
        from unittest.mock import patch
        from api import Api
        import web_api

        class RouteServiceStub:
            def find(self, request):
                option = {
                    "route": [request.start, request.destination],
                    "display_route": [request.start, request.destination],
                    "geometry": [[16.82, 96.13], [16.83, 96.14]],
                    "road_names": ["Pyay Road"], "distance": 2.0, "time": 4.0,
                    "traffic": "Light", "segment_traffic": ["Light"],
                    "decision": {"total_score": 3.4},
                }
                return {**option, "alternatives": []}

        with patch.object(web_api, "application_api", Api(RouteServiceStub())):
            response = self.client.post("/api/route", json={
                "vehicle": "Car", "start": "Hledan Centre", "destination": "Inya Lake",
                "conditions": {"time_band": "off_peak"},
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["road_names"], ["Pyay Road"])

    def test_frontend_is_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Yangon Traffic Agent", response.text)


if __name__ == "__main__":
    unittest.main()
