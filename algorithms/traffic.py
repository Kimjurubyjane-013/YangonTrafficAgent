# algorithms/traffic.py


TRAFFIC_MULTIPLIER = {

    "Light": 1.0,

    "Moderate": 1.2,

    "Heavy": 1.5

}



def get_route_traffic(route):

    """
    Simulate traffic condition.

    Later this can be replaced
    with real traffic API data.
    """

    route_length = len(route)


    if route_length <= 2:

        return "Light"


    elif route_length <= 4:

        return "Moderate"


    else:

        return "Heavy"



def get_multiplier(traffic):

    return TRAFFIC_MULTIPLIER.get(
        traffic,
        1.0
    )