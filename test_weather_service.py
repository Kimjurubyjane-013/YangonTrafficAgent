import unittest
from unittest.mock import Mock

import requests

from services.weather_service import WeatherService, WeatherUnavailable, classify_weather_risk


def payload(**overrides):
    current = {
        "time": "2026-09-01T11:05",
        "temperature_2m": 29.4,
        "relative_humidity_2m": 84,
        "precipitation": 1.2,
        "rain": 1.2,
        "weather_code": 61,
        "wind_speed_10m": 12.5,
    }
    current.update(overrides)
    return {"current": current}


class WeatherServiceTests(unittest.TestCase):
    def response(self, data):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = data
        return response

    def test_normalizes_live_yangon_weather_and_rule_risk(self):
        get = Mock(return_value=self.response(payload()))
        result = WeatherService(get).current()
        self.assertEqual(result["source"], "Open-Meteo")
        self.assertEqual(result["status"], "live")
        self.assertEqual(result["timezone"], "Asia/Yangon")
        self.assertEqual(result["condition"], "Rain")
        self.assertEqual(result["traffic_impact"]["prolog_weather"], "rain")
        self.assertEqual(result["traffic_impact"]["source"], "INFERRED / RULE-BASED")
        self.assertTrue(result["observed_at"].endswith("+06:30"))

    def test_cache_avoids_duplicate_provider_requests(self):
        get = Mock(return_value=self.response(payload()))
        service = WeatherService(get, cache_seconds=600)
        first, second = service.current(), service.current()
        self.assertEqual(first, second)
        get.assert_called_once()

    def test_force_refresh_retrieves_new_observation(self):
        get = Mock(side_effect=[self.response(payload()), self.response(payload(temperature_2m=31))])
        service = WeatherService(get)
        self.assertEqual(service.current()["temperature_c"], 29.4)
        self.assertEqual(service.current(force=True)["temperature_c"], 31.0)
        self.assertEqual(get.call_count, 2)

    def test_timeout_and_malformed_response_are_unavailable(self):
        for get in (Mock(side_effect=requests.Timeout()), Mock(return_value=self.response({"current": {}}))):
            with self.subTest(get=get):
                with self.assertRaises(WeatherUnavailable):
                    WeatherService(get).current()

    def test_weather_risk_thresholds_are_conservative_and_deterministic(self):
        self.assertEqual(classify_weather_risk(0, 0, 0, 8).prolog_atom, "clear")
        self.assertEqual(classify_weather_risk(61, 0.3, 0.3, 8).prolog_atom, "rain")
        self.assertEqual(classify_weather_risk(95, 0, 0, 8).prolog_atom, "storm")
        self.assertEqual(classify_weather_risk(1, 8, 8, 8).prolog_atom, "storm")


if __name__ == "__main__":
    unittest.main()
