import unittest

from services.route_comparison import annotate_route_comparison


class RouteComparisonTests(unittest.TestCase):
    def test_metric_labels_and_rank_names_are_backend_owned(self):
        routes = [
            {"time": 10, "distance": 6, "traffic_score": 60, "traffic_delay": 2,
             "traffic_source_label": "INFERRED", "inferred_coverage_percent": 100,
             "unknown_coverage_percent": 0, "geometry": [[0, 0]] * 30, "road_names": ["A"]},
            {"time": 12, "distance": 5, "traffic_score": 25, "traffic_delay": 1,
             "traffic_source_label": "INFERRED", "inferred_coverage_percent": 100,
             "unknown_coverage_percent": 0, "geometry": [[0, 0]] * 30, "road_names": ["B"]},
        ]
        annotate_route_comparison(routes)
        self.assertEqual(routes[0]["route_label"], "Route A")
        self.assertEqual(routes[1]["route_label"], "Route B")
        self.assertIn("FASTEST", routes[0]["characteristics"])
        self.assertIn("SHORTEST", routes[1]["characteristics"])
        self.assertIn("LEAST_CONGESTED", routes[1]["characteristics"])
        self.assertTrue(20 <= routes[0]["confidence"] <= 96)

    def test_confidence_is_deterministic_and_provider_coverage_is_stronger(self):
        inferred = {"traffic_source_label": "INFERRED", "inferred_coverage_percent": 100,
                    "unknown_coverage_percent": 0, "geometry": [[0, 0]] * 20, "road_names": ["A"]}
        provider = {**inferred, "traffic_source_label": "HERE", "provider_coverage_percent": 100,
                    "inferred_coverage_percent": 0}
        first = annotate_route_comparison([{**inferred}])[0]["confidence"]
        second = annotate_route_comparison([{**inferred}])[0]["confidence"]
        provider_score = annotate_route_comparison([provider])[0]["confidence"]
        self.assertEqual(first, second)
        self.assertGreater(provider_score, first)


if __name__ == "__main__":
    unittest.main()
