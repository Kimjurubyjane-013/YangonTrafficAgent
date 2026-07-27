from algorithms.route_optimizer import find_optimal_route


def find_route_tool(vehicle, start, destination):
    """
    Tool used by AI Agent to find routes.
    """

    result = find_optimal_route(
        vehicle,
        start,
        destination
    )

    return result