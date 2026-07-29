from datetime import datetime

# Traffic multipliers
TRAFFIC_MULTIPLIER = {
    "Light": 1.0,
    "Moderate": 1.3,
    "Heavy": 1.7,
}


def get_current_traffic():
    """
    Simulate Yangon traffic based on the current time.
    """

    hour = datetime.now().hour

    # Morning rush hour
    if 7 <= hour < 9:
        return "Heavy"

    # Working hours
    elif 9 <= hour < 17:
        return "Moderate"

    # Evening rush hour
    elif 17 <= hour < 19:
        return "Heavy"

    # Night
    return "Light"


def get_route_traffic(route):
    """
    Currently every road uses the same traffic level
    according to the current time.
    Later we can make each road different.
    """
    return get_current_traffic()


def get_multiplier(level):
    return TRAFFIC_MULTIPLIER[level]