import os
import webview

from algorithms.graph import LOCATION_COORDS


HTML_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "web",
    "map.html"
)


class WebMapPanel:

    def __init__(self):
        self.window = webview.create_window(
            "Yangon Route Map",
            HTML_PATH,
            width=800,
            height=700
        )

    def update_route(self, route, vehicle_speed=40):

        if not route:
            self.window.evaluate_js("clearRoute()")
            return

        coords = [list(LOCATION_COORDS[place]) for place in route]

        self.window.evaluate_js(f"showRoute({coords}, {vehicle_speed})")

    def reset(self):
        self.window.evaluate_js("clearRoute()")