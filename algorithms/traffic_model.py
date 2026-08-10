import datetime


# Average speed per vehicle type (km/h)

VEHICLE_SPEED = {
    "Car": 40,
    "Taxi": 38,
    "Bus": 28,
    "Ambulance": 60,
    "Fire Truck": 55,
    "Police": 55
}


# Traffic multiplier per time-of-day period
# >1.0 = slower than free-flow, <1.0 = faster than free-flow

TRAFFIC_LEVEL = {
    "Morning": 1.3,
    "Afternoon": 1.1,
    "Evening": 1.5,
    "Night": 0.8
}


def get_time_period(hour=None):

    if hour is None:
        hour = datetime.datetime.now().hour

    if 6 <= hour < 10:
        return "Morning"

    elif 10 <= hour < 16:
        return "Afternoon"

    elif 16 <= hour < 20:
        return "Evening"

    else:
        return "Night"


def get_traffic_multiplier(hour=None):

    period = get_time_period(hour)

    return TRAFFIC_LEVEL[period]


def classify_traffic(multiplier):

    if multiplier >= 1.4:
        return "Heavy"

    elif multiplier >= 1.1:
        return "Moderate"

    else:
        return "Light"


def calculate_eta(distance, vehicle="Car", hour=None):
    """
    ETA (minutes) = (distance / vehicle speed) * 60 * traffic multiplier
    """

    speed = VEHICLE_SPEED.get(
        vehicle,
        VEHICLE_SPEED["Car"]
    )

    multiplier = get_traffic_multiplier(hour)

    base_time = (distance / speed) * 60

    eta = base_time * multiplier

    return {
        "eta": eta,
        "base_time": base_time,
        "multiplier": multiplier,
        "period": get_time_period(hour),
        "traffic": classify_traffic(multiplier)
    }