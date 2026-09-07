import unittest
from api import Api
from services.road_repository import ROAD_REPOSITORY

class DashboardCoverageTests(unittest.TestCase):
    def setUp(self):
        self.api = Api()

    def test_dashboard_township_count_matches_dataset(self):
        overview = self.api.get_traffic_overview()
        self.assertEqual(overview["supported_townships"], len(ROAD_REPOSITORY.townships))



    def test_no_average_speed_in_overview(self):
        overview = self.api.get_traffic_overview()
        self.assertNotIn("average_speed_kmh", overview)
        self.assertNotIn("average_speed", overview)

    def test_overall_condition_exists(self):
        overview = self.api.get_traffic_overview()
        self.assertIn("overall_condition", overview)
        self.assertIn(overview["overall_condition"], ["Light", "Moderate", "Heavy"])

    def test_inferred_traffic_is_labelled_honestly(self):
        overview = self.api.get_traffic_overview()
        self.assertIn(overview["traffic_mode_label"], ["Inferred", "Mixed", "Real-Time", "Unknown"])

    def test_dashboard_does_not_claim_yangon_wide(self):
        overview = self.api.get_traffic_overview()
        self.assertEqual(overview.get("coverage_label"), "Supported Township Coverage")

if __name__ == "__main__":
    unittest.main()
