from agent.traffic_agent import run_traffic_agent
from algorithms.graph import get_locations, GRAPH, LOCATION_COORDS
from algorithms.vehicle import VEHICLE_SPEED


class Api:

    def __init__(self):
        self.last_result = None

    def get_locations(self):
        return get_locations()

    def get_vehicles(self):
        return list(VEHICLE_SPEED.keys())[:6]

    def get_graph_data(self):
        """
        Returns coordinates and edges so the frontend never
        needs its own hardcoded copy that could drift out of
        sync with the real graph.
        """

        edges = []
        seen = set()

        for a, neighbors in GRAPH.items():
            for b in neighbors:
                pair = tuple(sorted([a, b]))
                if pair not in seen:
                    seen.add(pair)
                    edges.append([a, b])

        return {
            "coords": {name: list(coord) for name, coord in LOCATION_COORDS.items()},
            "edges": edges
        }

    def find_route(self, vehicle, start, destination):

        try:
            result = run_traffic_agent(start, destination, vehicle)

        except Exception as e:
            return {"error": str(e)}

        if result.get("error"):
            return result

        self.last_result = result
        return result

    def get_last_result(self):
        return self.last_result