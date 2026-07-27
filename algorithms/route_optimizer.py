from algorithms.graph import GRAPH, LOCATION_COORDS
from algorithms.astar import astar
from algorithms.vehicle import VEHICLE_SPEED
from algorithms.time_estimator import calculate_time
from algorithms.traffic import get_traffic_level


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

    traffic_level, traffic_factor = get_traffic_level()

    speed = VEHICLE_SPEED.get(vehicle, 40)

    time = calculate_time(
        distance,
        speed,
        traffic_factor
    )

    return {
        "vehicle": vehicle,
        "route": path,
        "distance": distance,
        "time": time,
        "traffic": traffic_level
    }