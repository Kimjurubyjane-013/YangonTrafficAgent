import unittest
from unittest.mock import patch
import requests

from services.osrm_service import (RoadRoutingUnavailable, _CACHE, _REVERSE_CORRIDOR_CHECKED,
                                   _decode_polyline6, _is_diverse, _request, fetch_real_routes)


def raw(points, distance=10000, duration=900, name="Main Road"):
    return {"distance":distance,"duration":duration,"geometry":{"coordinates":[[lon,lat] for lat,lon in points]},
        "legs":[{"steps":[{"name":name}]}]}


def encode6(points):
    output=[]; previous=[0,0]
    for point in points:
        current=[round(value*1_000_000) for value in point]
        for value,old in zip(current,previous):
            delta=value-old; encoded=~(delta<<1) if delta<0 else delta<<1
            while encoded>=0x20:
                output.append(chr((0x20|(encoded&0x1f))+63)); encoded>>=5
            output.append(chr(encoded+63))
        previous=current
    return "".join(output)


class OsrmAlternativeTests(unittest.TestCase):
    def test_same_displayed_road_sequence_is_not_an_alternative(self):
        primary={"geometry":[[16.80,96.10],[16.81,96.11]],"road_names":["Kun Chan Road"]}
        shifted={"geometry":[[16.80,96.10],[16.805,96.115],[16.81,96.11]],"road_names":["Kun Chan Rd"]}
        self.assertFalse(_is_diverse(shifted,[primary]))

    def test_different_road_and_geometry_is_a_real_alternative(self):
        primary={"geometry":[[16.80,96.10],[16.81,96.11]],"road_names":["Kun Chan Road"]}
        alternative={"geometry":[[16.80,96.10],[16.83,96.14],[16.81,96.11]],"road_names":["Bogyoke Road"]}
        self.assertTrue(_is_diverse(alternative,[primary]))

    def setUp(self):
        _CACHE.clear()
        _REVERSE_CORRIDOR_CHECKED.clear()

    def test_duplicate_native_is_removed_and_fresh_corridors_are_validated(self):
        primary=raw([(16.80,96.10),(16.80,96.15),(16.80,96.20)])
        duplicate=raw([(16.80,96.10),(16.80,96.15),(16.80,96.20)],10100,910)
        north=raw([(16.80,96.10),(16.82,96.15),(16.80,96.20)],12000,1050,"North Road")
        south=raw([(16.80,96.10),(16.78,96.15),(16.80,96.20)],12500,1100,"South Road")
        with patch("services.osrm_service._request",side_effect=[[primary,duplicate],[north],[south],[north],[south]]):
            routes=fetch_real_routes((16.80,96.10),(16.80,96.20))
        self.assertEqual(len(routes),3)
        self.assertEqual(routes[0]["source"],"osrm-native")
        self.assertEqual({route["source"] for route in routes[1:]},{"osrm-via-corridor"})
        for route in routes:
            self.assertEqual(route["geometry"][0],[16.80,96.10])
            self.assertEqual(route["geometry"][-1],[16.80,96.20])

    def test_native_provider_alternatives_are_parsed_when_distinct(self):
        primary=raw([(16.80,96.10),(16.80,96.15),(16.80,96.20)],name="Main Road")
        alternative=raw([(16.80,96.10),(16.83,96.15),(16.80,96.20)],12000,1050,"North Road")
        with patch("services.osrm_service._request",return_value=[primary,alternative]):
            routes=fetch_real_routes((16.80,96.10),(16.80,96.20))
        self.assertEqual(len(routes),2)
        self.assertEqual([route["road_names"] for route in routes],[["Main Road"],["North Road"]])

    def test_bidirectional_discovery_unions_corridors_eagerly(self):
        start, destination = (16.80,96.10), (16.82,96.20)
        forward=raw([start,(16.81,96.15),destination],9000,800,"Forward Road")
        reverse=raw([destination,(16.79,96.15),start],10500,950,"Reverse Road")
        validated=raw([start,(16.79,96.15),destination],10800,930,"Validated Road")
        
        def mock_req(coords, *args, **kwargs):
            if len(coords) == 2:
                return [forward] if coords[0] == start else [reverse]
            mid = coords[1]
            return [validated] if mid[0] < 16.805 else [forward]
            
        with patch("services.osrm_service._request", side_effect=mock_req):
            routes = fetch_real_routes(start,destination)
            
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0]["source"],"osrm-native")
        self.assertEqual(routes[1]["source"],"osrm-via-corridor")
        self.assertEqual(routes[1]["geometry"][0],list(start))
        self.assertEqual(routes[1]["geometry"][-1],list(destination))

    def test_looping_and_self_intersecting_route_is_rejected(self):
        from services.osrm_service import _has_self_intersection_loop
        normal_coords = [[16.80, 96.10], [16.81, 96.11], [16.82, 96.12]]
        self.assertFalse(_has_self_intersection_loop(normal_coords))
        # Self-intersecting figure-8 loop
        loop_coords = [[16.80, 96.10], [16.82, 96.12], [16.80, 96.12], [16.82, 96.10]]
        self.assertTrue(_has_self_intersection_loop(loop_coords))

    def test_excessive_detour_is_rejected(self):
        primary=raw([(16.80,96.10),(16.80,96.20)])
        huge=raw([(16.80,96.10),(17.10,96.15),(16.80,96.20)],30000,3000)
        with patch("services.osrm_service._request",side_effect=[[primary],[huge],[huge],[huge],[huge]]):
            routes=fetch_real_routes((16.80,96.10),(16.80,96.20))
        self.assertEqual(len(routes),1)

    def test_successful_routes_are_cached(self):
        primary=raw([(16.80,96.10),(16.80,96.20)])
        with patch("services.osrm_service._fetch_real_routes_uncached",return_value=[{"geometry":[[1,2],[3,4]]}]) as provider:
            first=fetch_real_routes((16.80,96.10),(16.80,96.20))
            first[0]["geometry"].append([9,9])
            second=fetch_real_routes((16.80,96.10),(16.80,96.20))
        self.assertEqual(provider.call_count,1)
        self.assertEqual(second[0]["geometry"],[[1,2],[3,4]])

    def test_provider_exception_is_not_leaked_to_user(self):
        with patch("services.osrm_service.requests.get",side_effect=requests.Timeout("secret socket details")):
            with self.assertRaises(RoadRoutingUnavailable) as raised:
                _request([(16.8,96.1),(16.9,96.2)],3,2)
        self.assertNotIn("secret",str(raised.exception))
        self.assertIn("temporarily unavailable",str(raised.exception))

    def test_road_and_rd_names_are_deduplicated(self):
        from services.osrm_service import _english_road_names
        route={"legs":[{"steps":[{"name":"Nar Nat Taw Road"},{"name":"Nar Nat Taw Rd"}]}]}
        self.assertEqual(_english_road_names(route),["Nar Nat Taw Road"])

    def test_valhalla_polyline6_geometry_decodes(self):
        points=[(16.8262,96.13049),(16.8258,96.1311),(16.8249,96.1320)]
        decoded=_decode_polyline6(encode6(points))
        for actual,expected in zip(decoded,points):
            self.assertAlmostEqual(actual[0],expected[0],places=6)
            self.assertAlmostEqual(actual[1],expected[1],places=6)


if __name__=="__main__": unittest.main()
