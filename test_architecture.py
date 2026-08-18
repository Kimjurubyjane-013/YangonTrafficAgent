import unittest
from pathlib import Path

from api import Api
from algorithms.graph import GRAPH, validate_graph
from app.models import RouteRequest
from app.serialization import serialize_route_result
from app.validation import validate_route_request


class FakeRouteService:
    def find(self, request):
        option={"route":[request.start,request.destination],"display_route":[request.start,request.destination],
            "geometry":[[1,2],[3,4]],"road_names":[],"distance":2,"time":3,"traffic":"Light",
            "segment_traffic":["Light"],"decision":{"total_score":3}}
        return {**option,"alternatives":[dict(option)],"ai_message":"ok"}


class ArchitectureTests(unittest.TestCase):
    def test_graph_is_valid(self):
        self.assertEqual(validate_graph(GRAPH),[])

    def test_verified_shopping_centre_locations(self):
        from algorithms.graph import LOCATION_COORDS
        self.assertNotIn("Hledan Junction",LOCATION_COORDS)
        lat,lon=LOCATION_COORDS["Hledan Centre"]
        self.assertAlmostEqual(lat,16.8262,places=4)
        self.assertAlmostEqual(lon,96.13049,places=4)
        city_lat,city_lon=LOCATION_COORDS["Junction City"]
        self.assertAlmostEqual(city_lat,16.77896,places=4)
        self.assertAlmostEqual(city_lon,96.15427,places=4)

    def test_graph_validation_reports_bad_neighbor(self):
        self.assertTrue(validate_graph({"A":{"B":-1}}))

    def test_request_validation(self):
        request,error=validate_route_request("Car","Hledan Centre","Inya Lake",{"weather":"rain","ignored":1})
        self.assertIsNone(error); self.assertEqual(request.conditions,{"weather":"rain"})
        self.assertIsNotNone(validate_route_request("Jet","Hledan Centre","Inya Lake")[1])
        request,error=validate_route_request("Car","Hledan Centre","Inya Lake",{"closed_road":"Pyay Road","incident":"major"})
        self.assertIsNone(error); self.assertEqual(request.conditions["closed_road"],"Pyay Road")
        self.assertIsNotNone(validate_route_request("Car","Hledan Centre","Inya Lake",{"closed_road":"\u4e2d\u6587"})[1])
        self.assertIsNotNone(validate_route_request("Car","Hledan Centre","Inya Lake",{"time_band":"tomorrow"})[1])

    def test_best_and_alternative_contracts_match(self):
        api=Api(FakeRouteService()); result=api.find_route("Car","Hledan Centre","Inya Lake")
        self.assertTrue(result["ok"])
        for key in ("route","display_route","geometry","road_names","distance","time","traffic","segment_traffic","decision"):
            self.assertIn(key,result); self.assertIn(key,result["alternatives"][0])

    def test_structured_api_error(self):
        result=Api(FakeRouteService()).find_route("invalid","Hledan Centre","Inya Lake")
        self.assertEqual(result["error_details"]["code"],"unknown_vehicle")

    def test_home_agent_and_theme_controls_are_present(self):
        root=Path(__file__).parent
        html=(root/"web"/"app.html").read_text(encoding="utf-8")
        css=(root/"web"/"styles.css").read_text(encoding="utf-8")
        for element_id in ("home-view","planner-view","home-plan-route","theme-toggle","ai-text","decision-details-text",
            "scenario-mode","departure-band","incident-level","closed-road","analysis-view","analysis-btn",
            "analysis-back","route-provenance","route-comparison"):
            self.assertIn(f'id="{element_id}"',html)
        self.assertNotIn('id="evaluation-toggle"',html)
        self.assertNotIn('id="evaluation-dashboard"',html)
        self.assertNotIn("No meaningfully different real-road alternative",html)
        self.assertIn("body[data-theme=dark]",css)
        self.assertNotIn("OpenStreetMap routing</div>",html)
        self.assertIn("function ensureMapInitialized()",html)
        self.assertNotIn("pywebviewready', () => {\n        initMap();",html)

    def test_browser_transport_and_vercel_entrypoint_are_present(self):
        root=Path(__file__).parent
        api_js=(root/"web"/"api.js").read_text(encoding="utf-8")
        web_api=(root/"web_api.py").read_text(encoding="utf-8")
        vercel=(root/"vercel.json").read_text(encoding="utf-8")
        self.assertIn("fetch(`/api/${path}`",api_js)
        self.assertIn("app = FastAPI",web_api)
        self.assertIn('"src": "web_api.py"',vercel)
        self.assertNotIn("import webview",web_api)


if __name__ == "__main__": unittest.main()
