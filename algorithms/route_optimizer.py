from algorithms.route_finder import find_best_route


def find_optimal_route(vehicle, start, destination):

    result = find_best_route(vehicle, start, destination)

    if result is None:
        raise ValueError(
            f"No route found between {start} and {destination}."
        )

    best, alternatives = result

    best = dict(best)
    best["vehicle"] = vehicle
    best["alternatives"] = alternatives

    return best