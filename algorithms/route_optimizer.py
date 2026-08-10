from algorithms.graph import GRAPH, LOCATION_COORDS
from algorithms.astar import astar
from algorithms.traffic import get_route_traffic, get_multiplier
from algorithms.vehicle import calculate_time


def find_optimal_route(vehicle, start, destination):

    path, distance = astar(
        GRAPH,
        LOCATION_COORDS,
        start,
        destination
    )

    if path is None:
        raise ValueError(
            f"No route found between {start} and {destination}."
        )

    traffic = get_route_traffic(path)
    multiplier = get_multiplier(traffic)

    time = calculate_time(distance, vehicle, multiplier)

    return {
        "vehicle": vehicle,
        "route": path,
        "distance": distance,
        "time": time,
        "traffic": traffic
    }