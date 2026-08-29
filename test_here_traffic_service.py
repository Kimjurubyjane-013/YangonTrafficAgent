import os
import unittest
from unittest.mock import patch

from agent.real_world_agent import _real_route_provider
from services.here_traffic_service import (
    TrafficDataUnavailable,
    _route_record,
    decode_flexible_polyline,
    fetch_traffic_aware_routes,
)


class HereTrafficServiceTests(unittest.TestCase):
    def test_missing_here_service_falls_back_to_real_osrm_roads(self):
        fallback = [{"source": "osrm-native", "geometry": [[16.8, 96.1], [16.9, 96.2]]}]
        with patch("agent.real_world_agent.fetch_traffic_aware_routes", side_effect=TrafficDataUnavailable("missing")), \
             patch("agent.real_world_agent.fetch_real_routes", return_value=fallback) as osrm:
            self.assertEqual(_real_route_provider((16.8, 96.1), (16.9, 96.2)), fallback)
            osrm.assert_called_once()

    def test_official_flexible_polyline_example_decodes(self):
        points = decode_flexible_polyline("BFoz5xJ67i1B1B7PzIhaxL7Y")
        self.assertEqual(len(points), 4)
        self.assertAlmostEqual(points[0][0], 50.10228, places=5)
        self.assertAlmostEqual(points[0][1], 8.69821, places=5)

    def test_api_key_is_required_instead_of_fabricating_traffic(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(TrafficDataUnavailable):
                fetch_traffic_aware_routes((16.8,96.1),(16.9,96.2))

    def test_record_uses_provider_duration_and_base_duration(self):
        route={"sections":[{"polyline":"encoded","summary":{"length":7000,"duration":720,"baseDuration":420},
            "actions":[{"nextRoad":{"name":[{"value":"Pyay Road"}]}}]}]}
        with patch("services.here_traffic_service.decode_flexible_polyline",return_value=[[16.8,96.1],[16.9,96.2]]):
            record=_route_record(route,0,"2026-08-18T10:00:00+00:00")
        self.assertEqual(record["distance"],7.0)
        self.assertEqual(record["duration"],12.0)
        self.assertEqual(record["base_duration"],7.0)
        self.assertEqual(record["traffic_delay"],5.0)
        self.assertEqual(record["traffic_level"],"Heavy")
        self.assertEqual(record["road_names"],["Pyay Road"])

    def test_route_traffic_aggregates_provider_section_durations(self):
        route = {"sections": [
            {"polyline": "a", "summary": {"length": 1000, "duration": 300, "baseDuration": 290}},
            {"polyline": "b", "summary": {"length": 1000, "duration": 360, "baseDuration": 300}},
            {"polyline": "c", "summary": {"length": 1000, "duration": 500, "baseDuration": 300}},
        ]}
        shapes = [
            [[16.80, 96.10], [16.81, 96.11]],
            [[16.81, 96.11], [16.82, 96.12]],
            [[16.82, 96.12], [16.83, 96.13]],
        ]
        with patch("services.here_traffic_service.decode_flexible_polyline", side_effect=shapes):
            record = _route_record(route, 0, "2026-08-29T07:00:00Z")
        self.assertEqual(record["segment_traffic"], ["Light", "Moderate", "Heavy"])
        self.assertEqual(record["traffic_level"], "Moderate")
        self.assertEqual(record["route_duration_seconds"], 1160)
        self.assertEqual(record["base_duration_seconds"], 890)
        self.assertEqual(record["traffic_delay_seconds"], 270)
        self.assertEqual(len(record["traffic_geometry"]), 3)
        self.assertEqual(record["traffic_geometry"][1][0], [16.81, 96.11])


if __name__ == "__main__": unittest.main()
