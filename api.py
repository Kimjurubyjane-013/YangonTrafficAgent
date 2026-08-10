from agent.traffic_agent import run_traffic_agent
from algorithms.graph import get_locations
from algorithms.vehicle import VEHICLE_SPEED


class Api:

    def __init__(self):
        self.last_result = None

    def get_locations(self):
        return get_locations()

    def get_vehicles(self):
        return list(VEHICLE_SPEED.keys())[:6]

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