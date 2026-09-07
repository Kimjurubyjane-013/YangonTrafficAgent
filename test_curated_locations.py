"""Comprehensive tests verifying curated Yangon location dataset and township grouping."""
import json
import unittest
from pathlib import Path

from algorithms.graph import LOCATION_COORDS, get_locations, get_location_records
from services.road_repository import ROAD_REPOSITORY
from agent.real_world_agent import run_real_world_agent


REJECTED_LOCATIONS = [
    "Yangon United Sports Complex",
    "Hlaing Market",
    "Thiri Myaing Railway Station",
    "Inya Lake \u2013 Hlaing-side access point",
    "Inya Lake",
    "Novotel Yangon Max",
    "Practising High School, Kamayut (TTC Yangon)",
    "Judson Chapel",
    "Yangon University Convocation Hall",
    "Yangon University Arts Hall",
    "Sanchaung Market",
    "Mahar Myaing Hospital",
    "BEHS (1) Dagon",
    "Bogyoke Aung San Museum",
    "Yankin Children\u2019s Hospital",
    "Golden City",
    "The Central",
    "Yankin Market",
    "Guanyin Gumiao Temple",
    "Kheng Hock Keong Temple",
    "BEHS (1) Latha",
    "BEHS (2) Latha",
    "Cholia Jamah Mosque",
    "Myanma Insurance",
    "Holy Trinity Cathedral",
    "British Council Yangon",
    "Pansodan Ferry Terminal",
    "Pansodan Jetty",
    "Yangon City Hall",
    "Shwe Pu Zun Cafeteria & Bakery",
    "Chinatown-related Lanmadaw-side landmark",
    "Junction Maw Tin",
    "Kyimyindaing Railway Station",
    "Kyimyindaing Night Market",
    # Area/township names removed as start/destination:
    "Sanchaung",
    "Lanmadaw",
    "Latha",
    "Ahlone",
    "Kandawgyi",
    "Bahan",
    "Tamwe",
    "Thingangyun",
    "South Okkalapa",
    "Waizayantar",
    "Parami",
    "Yankin",
    "Kabar Aye Pagoda",
    "Mayangone",
    "8 Mile Junction",
    "Thamine",
    "Bayint Naung Junction",
    "North Okkalapa",
    "Yangon Airport",
    "Yangon Central Station",
]

APPROVED_TOWNSHIPS = {
    "Hlaing Township": [
        "University of Information Technology (UIT)",
        "MICT Park",
        "LOTTE Hotel Yangon",
        "Okkyin Railway Station",
        "Thiri Mingalar Market",
    ],
    "Kamayut Township": [
        "University of Yangon",
        "Hledan Centre",
        "Junction Square",
        "American Center Yangon",
    ],
    "Sanchaung Township": [
        "Myaynigone",
        "Dagon Centre I",
        "Dagon Centre II",
        "Happy Zone Amusement Center",
    ],
    "Dagon Township": [
        "Shwedagon Pagoda",
        "Maha Wizaya Pagoda",
        "National Museum of Myanmar",
        "National Theatre of Yangon",
        "People's Park",
        "Happy World Amusement Park",
        "Thamada Cinema",
    ],
    "Bahan Township": [
        "Myanmar Plaza",
        "Chaukhtatgyi Buddha Temple",
        "Ngahtatgyi Buddha Temple",
    ],
    "Yankin Township": [
        "Sedona Hotel Yangon",
        "Yankin Centre",
    ],
    "Latha Township": [
        "Theingyi Market",
        "Chinatown Night Market",
    ],
    "Pabedan Township": [
        "Junction City",
        "Bogyoke Aung San Market",
    ],
    "Kyauktada Township": [
        "Sule Pagoda",
        "Maha Bandula Park",
    ],
    "Lanmadaw Township": [
        "City Mall St. John",
        "Yangon General Hospital",
    ],
    "Mingalar Taung Nyunt Township": [
        "Yangon Zoological Gardens",
        "Mingalar Market",
    ],
}


class CuratedLocationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loc_file = Path(__file__).parent / "data" / "locations.json"
        with open(loc_file, "r", encoding="utf-8") as f:
            cls.raw_locations = json.load(f)
        cls.loc_names = [item["name"] for item in cls.raw_locations]
        cls.loc_map = {item["name"]: item for item in cls.raw_locations}

    def test_removed_locations_are_absent(self):
        """Verify all rejected POIs and vague names are absent from locations.json."""
        for rejected in REJECTED_LOCATIONS:
            self.assertNotIn(rejected, self.loc_names, f"Rejected location '{rejected}' must not be present")
            self.assertNotIn(rejected, LOCATION_COORDS, f"Rejected location '{rejected}' must not be in LOCATION_COORDS")

    def test_approved_locations_remain(self):
        """Verify all 35 approved locations are present."""
        for township, expected_pois in APPROVED_TOWNSHIPS.items():
            for poi in expected_pois:
                self.assertIn(poi, self.loc_names, f"Approved POI '{poi}' in {township} is missing")
                self.assertEqual(self.loc_map[poi].get("township"), township, f"POI '{poi}' has wrong township")

    def test_uit_remains_in_hlaing_township(self):
        """Verify UIT exact name, coordinates, township, and availability."""
        uit_name = "University of Information Technology (UIT)"
        self.assertIn(uit_name, self.loc_names)
        self.assertIn(uit_name, LOCATION_COORDS)
        record = self.loc_map[uit_name]
        self.assertEqual(record["township"], "Hlaing Township")
        lat, lon = record["lat"], record["lon"]
        self.assertTrue(16.85 <= lat <= 16.86, f"UIT latitude {lat} out of expected range")
        self.assertTrue(96.13 <= lon <= 96.14, f"UIT longitude {lon} out of expected range")

    def test_no_duplicate_names_or_coordinates(self):
        """Verify all location display names and coordinates are unique."""
        self.assertEqual(len(self.loc_names), len(set(self.loc_names)), "Duplicate location names found")
        coords = [(item["lat"], item["lon"]) for item in self.raw_locations]
        self.assertEqual(len(coords), len(set(coords)), "Duplicate coordinates found")

    def test_every_location_has_valid_coordinates_and_township(self):
        """Verify every location has valid lat/lon in Yangon bounding box and valid township."""
        for item in self.raw_locations:
            name = item["name"]
            self.assertTrue(item.get("township"), f"Location '{name}' missing township")
            self.assertIn(item["township"], APPROVED_TOWNSHIPS, f"Location '{name}' has unknown township '{item.get('township')}'")
            lat = item["lat"]
            lon = item["lon"]
            self.assertTrue(16.7 <= lat <= 16.95, f"Location '{name}' latitude {lat} out of Yangon bounds")
            self.assertTrue(96.05 <= lon <= 96.25, f"Location '{name}' longitude {lon} out of Yangon bounds")

    def test_start_and_destination_use_same_authoritative_dataset(self):
        """Verify ROAD_REPOSITORY, LOCATION_COORDS, and get_locations share the exact same dataset."""
        repo_names = set(ROAD_REPOSITORY.locations.keys())
        coord_names = set(LOCATION_COORDS.keys())
        func_names = set(get_locations())
        file_names = set(self.loc_names)
        self.assertEqual(repo_names, file_names)
        self.assertEqual(coord_names, file_names)
        self.assertEqual(func_names, file_names)

    def test_html_dropdowns_group_by_township_with_optgroup(self):
        """Verify app.html static HTML and JS use optgroup grouping for all 11 townships."""
        app_html = (Path(__file__).parent / "web" / "app.html").read_text(encoding="utf-8")
        for township in APPROVED_TOWNSHIPS:
            self.assertIn(f'optgroup label="{township}"', app_html, f"app.html missing optgroup for {township}")
        for rejected in ["Inya Lake", "Yangon Airport", "Yangon Central Station", "Sanchaung Market"]:
            self.assertNotIn(f'value="{rejected}"', app_html, f"app.html contains rejected value '{rejected}'")

    def test_representative_cross_township_routes_succeed(self):
        """Verify routing succeeds for the required representative journeys."""
        test_pairs = [
            ("University of Information Technology (UIT)", "Junction Square"),
            ("Junction Square", "University of Information Technology (UIT)"),
            ("Hledan Centre", "Shwedagon Pagoda"),
            ("Shwedagon Pagoda", "Hledan Centre"),
            ("Junction City", "Sule Pagoda"),
            ("Myanmar Plaza", "People's Park"),
        ]
        for start, dest in test_pairs:
            with self.subTest(start=start, dest=dest):
                res = run_real_world_agent(start, dest, "Car")
                self.assertNotIn("error", res, f"Route from {start} to {dest} failed: {res.get('error')}")
                self.assertGreater(res.get("distance", 0), 0)
                self.assertGreater(res.get("time", 0), 0)
                self.assertTrue(res.get("geometry"), f"Route {start} -> {dest} missing geometry")


if __name__ == "__main__":
    unittest.main()
