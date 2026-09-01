import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch

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
        request,error=validate_route_request("Car","Hledan Centre","Inya Lake",{"traffic_scenario":"off_peak"})
        self.assertIsNone(error); self.assertEqual(request.conditions["traffic_scenario"],"off_peak")
        self.assertIsNotNone(validate_route_request("Car","Hledan Centre","Inya Lake",{"traffic_scenario":"weekend"})[1])

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
            "scenario-mode","departure-band","closed-road","analysis-view","analysis-btn",
            "analysis-back","route-provenance","route-comparison","nav-dashboard","dashboard-view",
            "health-score","hotspot-list","best-flow-list","route-why","forecast-period","forecast-result",
            "dashboard-available","dashboard-error-row","retry-traffic","refresh-traffic",
            "coverage-bars","provider-status-note"):
            self.assertIn(f'id="{element_id}"',html)
        for removed_id in ("nav-traffic","nav-simulation","traffic-map-view","dashboard-map","legacy-home-view"):
            self.assertNotIn(f'id="{removed_id}"',html)
        self.assertIn('<main class="home-view" id="home-view">', html)
        self.assertIn('<main class="traffic-dashboard" id="dashboard-view" hidden>', html)
        self.assertNotIn('id="evaluation-toggle"',html)
        self.assertNotIn('id="evaluation-dashboard"',html)
        self.assertNotIn("No meaningfully different real-road alternative",html)
        self.assertIn("body[data-theme=dark]",css)
        self.assertNotIn("OpenStreetMap routing</div>",html)
        self.assertIn("function ensureMapInitialized()",html)
        self.assertIn("result.recommendation_reason?.explanation",html)
        self.assertNotIn("Compared with Alternative 1:",html)
        self.assertNotIn("pywebviewready', () => {\n        initMap();",html)
        self.assertIn("Yangon Traffic Intelligence",html)
        self.assertIn('<script src="./dashboard.js"></script>',html)

    def test_dashboard_uses_the_shared_backend_snapshot(self):
        root=Path(__file__).parent
        dashboard=(root/"web"/"dashboard.js").read_text(encoding="utf-8")
        html=(root/"web"/"app.html").read_text(encoding="utf-8")
        css=(root/"web"/"styles.css").read_text(encoding="utf-8")
        self.assertIn("YangonApi.trafficOverview()",dashboard)
        self.assertIn("data.roads",dashboard)
        self.assertNotIn("Math.random",dashboard)
        self.assertNotIn("L.map",dashboard)
        self.assertNotIn("dashboard-traffic-map",dashboard)
        self.assertNotIn("dashboard-traffic-map",html)
        self.assertNotIn("dashboard-map-wrap",css)
        self.assertNotIn("dashboard-map-legend",css)
        self.assertIn('id="dashboard-error-row"',html)
        self.assertIn("data.unknown_coverage_percent",dashboard)
        self.assertIn("byId('dashboard-available').hidden = true",dashboard)

    def test_browser_transport_and_vercel_entrypoint_are_present(self):
        root=Path(__file__).parent
        api_js=(root/"web"/"api.js").read_text(encoding="utf-8")
        web_api=(root/"web_api.py").read_text(encoding="utf-8")
        vercel=(root/"vercel.json").read_text(encoding="utf-8")
        self.assertIn("fetch(`/api/${path}`",api_js)
        self.assertIn("trafficOverview",api_js)
        self.assertIn("roadTraffic",api_js)
        self.assertIn("app = FastAPI",web_api)
        self.assertIn('"src": "web_api.py"',vercel)
        self.assertNotIn("import webview",web_api)

    def test_railway_uses_the_http_entrypoint_not_the_desktop_entrypoint(self):
        root=Path(__file__).parent
        railway=(root/"railway.json").read_text(encoding="utf-8")
        main=(root/"main.py").read_text(encoding="utf-8")
        web_api=(root/"web_api.py").read_text(encoding="utf-8")
        self.assertIn('"startCommand": "uvicorn web_api:app --host 0.0.0.0 --port $PORT"',railway)
        self.assertIn('"healthcheckPath": "/health"',railway)
        self.assertIn('app = FastAPI(',web_api)
        self.assertIn('@app.get("/health"',web_api)
        self.assertNotIn('app = FastAPI(',main)
        self.assertIn('if __name__ == "__main__":',main)

    def test_desktop_startup_wires_pywebview_without_opening_a_window(self):
        if importlib.util.find_spec("webview") is None:
            self.skipTest("optional pywebview desktop runtime is not installed")
        from app.startup import run
        with patch("webview.create_window") as create_window, patch("webview.start") as start:
            run()
        create_window.assert_called_once()
        start.assert_called_once()

    def test_leaflet_and_three_assets_remain_available(self):
        root=Path(__file__).parent
        for path in ("web/lib/leaflet.js","web/lib/leaflet.css","web/lib/three.min.js","web/simulation3d.js",
            "web/traffic-colors.js"):
            self.assertTrue((root/path).is_file(), path)

    def test_traffic_colors_are_shared_by_map_badges_and_simulation(self):
        root=Path(__file__).parent
        html=(root/"web"/"app.html").read_text(encoding="utf-8")
        css=(root/"web"/"styles.css").read_text(encoding="utf-8")
        simulation=(root/"web"/"simulation3d.js").read_text(encoding="utf-8")
        palette=(root/"web"/"traffic-colors.js").read_text(encoding="utf-8")

        for level, color in (("Light", "#2F9E68"), ("Moderate", "#D88918"), ("Heavy", "#D94B42")):
            self.assertIn(f"{level}: Object.freeze({{ css: '{color}'", palette)
            self.assertIn(f"var(--traffic-{level.lower()})", css)
        self.assertIn("Unknown: Object.freeze({ css: '#71808A'", palette)
        self.assertIn("getTrafficColor: css", palette)

        self.assertLess(html.index('./traffic-colors.js'), html.index('./simulation3d.js'))
        self.assertIn("YangonTrafficColors.css(traffic)", html)
        self.assertIn("segmentTraffic = selected.levels", html)
        self.assertIn("currentSegmentTraffic = segmentTraffic", html)
        self.assertIn("traffic_geometry: result.traffic_geometry", html)
        self.assertIn("YangonTrafficColors.getTrafficColor(level)", html)
        self.assertIn("YangonTrafficColors.three(traffic[index])", simulation)
        self.assertNotIn("Light: 0x2ecc71", simulation)

    def test_mixed_route_geometry_is_split_into_traffic_colored_legs(self):
        html=(Path(__file__).parent/"web"/"app.html").read_text(encoding="utf-8")
        self.assertIn("function splitPolylineForTraffic(points, requestedParts)", html)
        self.assertIn("const effective = levels.length ? levels : [overall]", html)
        self.assertIn("const legs = splitPolylineForTraffic(option.geometry, effective.length)", html)
        self.assertIn("for (let i = 0; i < legs.length; i++)", html)
        self.assertIn("routeLayers.forEach(l => map.removeLayer(l))", html)

    def test_route_comparisons_and_simulation_traffic_use_backend_contract(self):
        html=(Path(__file__).parent/"web"/"app.html").read_text(encoding="utf-8")
        self.assertIn("opt.comparison_to_recommended?.explanation", html)
        self.assertNotIn("const etaDifference = Number(opt.time)", html)
        self.assertIn("function trafficAtMapDistance(distanceKm, segmentBreaks)", html)
        self.assertIn("simulation.segmentBreaks", html)
        self.assertIn("currentRouteLegs || []", html)

    def test_route_cards_have_structured_readable_metadata(self):
        root=Path(__file__).parent
        html=(root/"web"/"app.html").read_text(encoding="utf-8")
        css=(root/"web"/"styles.css").read_text(encoding="utf-8")
        for token in ("route-option-header", "route-option-path", "route-option-metrics",
                      "route-option-badges", "addMetric('Travel Time'", "traffic_adjusted_eta", "free_flow_eta"):
            self.assertIn(token, html)
        self.assertNotIn("addMetric('Delay'", html)
        self.assertIn(".traffic-stat>span,.traffic-stat>strong,.traffic-stat>small{display:block", css)
        self.assertIn(".traffic-dashboard{margin-inline:auto", css)
        self.assertIn("setState('', 'ready')", (root/"web"/"dashboard.js").read_text(encoding="utf-8"))

    def test_scenario_and_normal_result_ui_are_truthful_and_clean(self):
        html=(Path(__file__).parent/"web"/"app.html").read_text(encoding="utf-8")
        self.assertIn('<option value="current">No Scenario</option>', html)
        self.assertIn('<option value="peak">Rush Hour</option>', html)
        self.assertIn('conditions.traffic_scenario', html)
        self.assertIn('id="r-scenario"', html)
        self.assertIn('id="unknown-legend-item" hidden', html)
        self.assertIn("document.getElementById('unknown-legend-item').hidden", html)
        self.assertIn("provenance.hidden = true", html)
        self.assertNotIn("`Traffic Source: ${srcLabel}`", html)
        self.assertNotIn("provenance.hidden = false", html)

    def test_source_badges_have_central_light_and_dark_contrast_styles(self):
        root=Path(__file__).parent
        css=(root/"web"/"styles.css").read_text(encoding="utf-8")
        html=(root/"web"/"app.html").read_text(encoding="utf-8")
        dashboard=(root/"web"/"dashboard.js").read_text(encoding="utf-8")
        for source in ("here", "inferred", "mixed", "unknown"):
            self.assertIn(f"--source-{source}-bg:", css)
            self.assertIn(f"--source-{source}-text:", css)
            self.assertIn(f"--source-{source}-border:", css)
            self.assertIn(f"src-badge-{source}", css)
        self.assertNotIn("route-src-${sourceKind}", html)
        self.assertNotIn("srcBadge.style.background", html)
        for badge_id in ("hotspot-source-badge", "best-flow-source-badge",
                         "health-source-badge", "coverage-source-badge"):
            self.assertIn(badge_id, dashboard)

    def test_outlook_renders_structured_fields_without_object_stringification(self):
        root = Path(__file__).parent
        app = (root / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("typeof data !== 'object'", app)
        self.assertIn("Number(data.estimated_eta)", app)
        self.assertIn("Number(data.expected_delay)", app)
        self.assertNotIn("JSON.stringify(data)", app)
        self.assertNotIn("[object Object]", app)

    def test_best_flow_title_handles_all_heavy_snapshot(self):
        dashboard=(Path(__file__).parent/"web"/"dashboard.js").read_text(encoding="utf-8")
        self.assertIn("best.every(road => trafficLevel(road.traffic_level) === 'Heavy')", dashboard)
        self.assertIn("'Best Available Flow'", dashboard)


if __name__ == "__main__": unittest.main()
