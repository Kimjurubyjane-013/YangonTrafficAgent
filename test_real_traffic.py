import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from agent.real_world_agent import run_real_world_agent
from app.runtime_config import traffic_mode, yangon_now
from services.here_flow_service import (
    HereFlowTrafficService,
    HereFlowUnavailable,
    classify_provider_flow,
)
from services.route_decision_engine import RouteDecisionEngine
from services.traffic_backend import TrafficBackend
from services.traffic_service import get_time_period


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _payload(jam=2.0, speed=12.0, free_flow=16.0):
    return {
        "sourceUpdated": "2026-08-29T07:00:00Z",
        "results": [{
            "location": {"description": "Pyay Road", "shape": {"links": [{"points": [
                {"lat": 16.8262, "lng": 96.13049},
                {"lat": 16.8172, "lng": 96.1314},
            ]}]}},
            "currentFlow": {"jamFactor": jam, "speed": speed, "freeFlow": free_flow, "confidence": 0.9},
        }],
    }


class RealTrafficTests(unittest.TestCase):
    def test_default_mode_is_real_and_invalid_value_is_safe(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(traffic_mode(), "real")
        with patch.dict(os.environ, {"TRAFFIC_MODE": "invented"}):
            self.assertEqual(traffic_mode(), "real")

    def test_yangon_timezone_and_request_time_period(self):
        converted = yangon_now(datetime(2026, 8, 29, 1, 0, tzinfo=timezone.utc))
        self.assertEqual((converted.hour, converted.minute), (7, 30))
        self.assertEqual(converted.utcoffset().total_seconds(), 6.5 * 3600)
        self.assertEqual(get_time_period(datetime(2026, 8, 29, 13, 52)), "DAYTIME")
        self.assertEqual(get_time_period(datetime(2026, 8, 29, 7, 30)), "MORNING_RUSH")
        self.assertEqual(get_time_period(datetime(2026, 8, 29, 17, 30)), "EVENING_RUSH")

    def test_provider_classification_contract(self):
        self.assertEqual(classify_provider_flow(1, 15, 16), "Light")
        self.assertEqual(classify_provider_flow(5, 9, 16), "Moderate")
        self.assertEqual(classify_provider_flow(9, 3, 16), "Heavy")
        self.assertIsNone(classify_provider_flow(None, None, None))

    def test_flow_is_geographically_matched_and_timestamped(self):
        calls = []
        service = HereFlowTrafficService(request_get=lambda *a, **kw: calls.append((a, kw)) or _Response(_payload()))
        with patch.dict(os.environ, {"HERE_API_KEY": "test-key"}):
            snapshot = service.refresh()
        matched = [road for road in snapshot["roads"] if road["matched"]]
        self.assertTrue(matched)
        self.assertLess(len(matched), len(snapshot["roads"]))
        self.assertEqual(matched[0]["traffic_source"], "HERE")
        self.assertEqual(matched[0]["provider_updated_at"], "2026-08-29T07:00:00Z")
        self.assertEqual(len(calls), 1)
        self.assertIn("bbox:", calls[0][1]["params"]["in"])

    def test_cache_and_force_refresh(self):
        ticks = [0.0]
        calls = []
        service = HereFlowTrafficService(
            request_get=lambda *a, **kw: calls.append(1) or _Response(_payload()),
            clock=lambda: ticks[0],
        )
        with patch.dict(os.environ, {"HERE_API_KEY": "test-key", "TRAFFIC_CACHE_SECONDS": "60"}):
            service.refresh()
            ticks[0] = 30
            service.refresh()
            ticks[0] = 61
            service.refresh()
            service.refresh(force=True)
        self.assertEqual(len(calls), 3)

    def test_dark_theme_and_unavailable_route_use_semantic_colors(self):
        with open("web/styles.css", encoding="utf-8") as handle:
            css = handle.read()
        with open("web/app.html", encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn("--text-primary", css)
        self.assertIn("--surface-raised", css)
        self.assertIn("body[data-theme=dark]", css)
        self.assertIn("|| 'Unavailable'", html)
        self.assertNotIn("normalize(option.traffic) || 'Light'", html)

    def test_real_mode_does_not_silently_fallback(self):
        class Missing:
            def refresh(self, force=False):
                raise HereFlowUnavailable("provider unavailable")
        backend = TrafficBackend(real_service=Missing())
        with patch.dict(os.environ, {"TRAFFIC_MODE": "real"}):
            result = backend.overview()
        self.assertFalse(result["available"])
        self.assertEqual(result["roads"], [])
        self.assertEqual(result["traffic_source"], "unavailable")

    def test_explicit_simulation_mode_remains_available(self):
        backend = TrafficBackend()
        with patch.dict(os.environ, {"TRAFFIC_MODE": "simulation"}):
            result = backend.overview()
        self.assertTrue(result["available"])
        self.assertEqual(result["traffic_source"], "Academic Simulation")
        self.assertTrue(result["roads"])

    def test_osrm_route_in_real_mode_keeps_traffic_unavailable(self):
        provider = lambda *_args, **_kwargs: [{
            "provider_id": 0, "distance": 2.0, "duration": 4.0,
            "geometry": [[16.8262, 96.13049], [16.8172, 96.1314]],
            "road_names": ["Pyay Road"], "source": "osrm-native",
        }]
        with patch.dict(os.environ, {"TRAFFIC_MODE": "real"}):
            result = run_real_world_agent(
                "Hledan Centre", "Junction Square", "Car",
                route_provider=provider, decision_engine=RouteDecisionEngine(False),
            )
        self.assertEqual(result["traffic"], "Unavailable")
        self.assertFalse(result["traffic_data_available"])
        self.assertFalse(result["traffic_model_available"])
        self.assertIsNone(result["traffic_delay"])


if __name__ == "__main__":
    unittest.main()
