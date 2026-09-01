import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from app.runtime_config import app_timezone
from services.traffic_prediction import PREDICTION_PERIODS, predict_route_traffic, predict_traffic, prediction_series
from web_api import app


class TrafficPredictionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 1, 14, 0, tzinfo=app_timezone())

    def test_all_prediction_periods_are_deterministic_and_honestly_labelled(self):
        for period in PREDICTION_PERIODS:
            with self.subTest(period=period):
                first = predict_traffic(period, now=self.now)
                second = predict_traffic(period, now=self.now)
                self.assertEqual(first, second)
                self.assertEqual(first["traffic_source"], "INFERRED")
                self.assertEqual(first["forecast_type"], "INFERRED_FORECAST")
                self.assertFalse(first["is_live"])

    def test_series_uses_yangon_timezone(self):
        result = prediction_series(now=self.now)
        self.assertEqual(result["timezone"], "Asia/Yangon")
        self.assertEqual(len(result["predictions"]), 4)

    def test_invalid_period_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_traffic("tomorrow", now=self.now)

    def test_http_prediction_contract_and_validation(self):
        client = TestClient(app)
        response = client.get("/api/traffic/prediction", params={"period": "plus_30"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["forecast_type"], "INFERRED_FORECAST")
        invalid = client.get("/api/traffic/prediction", params={"period": "tomorrow"})
        self.assertEqual(invalid.status_code, 400)

    def test_selected_route_outlook_preserves_current_route_truth(self):
        route = {"time": 11.0, "free_flow_eta": 9.0, "traffic_score": 55.0}
        current = predict_route_traffic(route, "now", now=self.now)
        self.assertEqual(current["traffic"], "Moderate")
        self.assertEqual(current["estimated_eta"], 11.0)
        self.assertEqual(current["forecast_type"], "CURRENT_ROUTE")
        future = predict_route_traffic(route, "evening_rush", now=self.now)
        self.assertEqual(future["forecast_type"], "INFERRED_ROUTE_FORECAST")
        self.assertFalse(future["is_live"])

    def test_http_selected_route_outlook_contract(self):
        client = TestClient(app)
        response = client.post("/api/traffic/route-outlook", json={
            "period": "plus_30",
            "route": {"time": 11.0, "free_flow_eta": 9.0, "traffic_score": 55.0},
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json()["traffic"], {"Light", "Moderate", "Heavy"})
        self.assertGreater(response.json()["estimated_eta"], 0)


if __name__ == "__main__":
    unittest.main()
