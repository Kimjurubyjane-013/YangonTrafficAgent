from algorithms.astar import astar
from algorithms.graph import GRAPH, LOCATION_COORDS
from algorithms.traffic import (
    get_route_traffic,
    get_multiplier,
)
from algorithms.vehicle import calculate_time


def optimize_route(route, distance, vehicle):
    """
    Apply simulated traffic conditions and estimate travel time.
    """

    traffic = get_route_traffic(route)

    multiplier = get_multiplier(traffic)

    estimated_time = calculate_time(
        distance,
        vehicle,
        multiplier,
    )

    return {
        "vehicle": vehicle,
        "route": route,
        "distance": distance,
        "traffic": traffic,
        "time": estimated_time,
    }


def find_optimal_route(vehicle, start, destination):
    """
    Find the best route using A*,
    then apply simulated traffic conditions.
    """

    if start not in GRAPH:
        raise ValueError(f"Unknown start location: {start}")

    if destination not in GRAPH:
        raise ValueError(f"Unknown destination: {destination}")

    if start == destination:
        raise ValueError("Start and destination cannot be the same.")

    route, distance = astar(
        GRAPH,
        LOCATION_COORDS,
        start,
        destination,
    )

    if route is None:
        raise ValueError(
            f"No available route from '{start}' to '{destination}'."
        )

    return optimize_route(
        route,
        distance,
        vehicle,
    )