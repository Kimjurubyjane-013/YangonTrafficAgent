VEHICLE_SPEED = {
    "Car": 40,
    "Bus": 25,
    "Taxi": 35,
    "Ambulance": 60,
    "Fire Truck": 50,
    "Police": 55,
    "Motorcycle": 45,
    "Bicycle": 15,
    "Walking": 5
}

# Multipliers apply to the routing provider's normal-car duration. Fixed and
# per-km allowances model boarding, dispatch, manoeuvring, or slower modes.
REAL_ROUTE_TIME_PROFILE = {
    "Car": (1.00, 0.0, 0.00),
    "Taxi": (1.04, 0.5, 0.03),
    "Bus": (1.55, 2.0, 0.18),
    "Ambulance": (0.78, 0.3, 0.00),
    "Fire Truck": (0.90, 0.8, 0.04),
    "Police": (0.84, 0.3, 0.00),
    "Motorcycle": (0.92, 0.0, 0.00),
    "Bicycle": (2.80, 0.0, 0.10),
    "Walking": (7.00, 0.0, 0.25),
}

TRAFFIC_TIME_MULTIPLIER = {
    "Light": 1.00,
    "Moderate": 1.18,
    "Heavy": 1.45,
}


def calculate_real_route_time(provider_minutes, distance_km, vehicle, traffic_level="Light"):
    """Estimate ETA from provider road time, vehicle behaviour, and traffic."""
    factor, fixed_minutes, per_km = REAL_ROUTE_TIME_PROFILE.get(vehicle, REAL_ROUTE_TIME_PROFILE["Car"])
    traffic_factor = TRAFFIC_TIME_MULTIPLIER.get(traffic_level, TRAFFIC_TIME_MULTIPLIER["Light"])
    vehicle_adjusted = float(provider_minutes) * factor + fixed_minutes + float(distance_km) * per_km
    free_flow_floor = float(distance_km) / VEHICLE_SPEED.get(vehicle, VEHICLE_SPEED["Car"]) * 60
    return round(max(0.5, free_flow_floor, vehicle_adjusted) * traffic_factor, 1)


def calculate_time(distance, vehicle, traffic_multiplier=1.0):

    speed = VEHICLE_SPEED.get(vehicle, 40)

    time_in_hours = distance / speed

    time_in_minutes = time_in_hours * 60 * traffic_multiplier

    return round(time_in_minutes, 1)


def format_duration(time_in_minutes):

    total_seconds = round(time_in_minutes * 60)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        if minutes > 0:
            return f"{hours} hr {minutes} min"
        return f"{hours} hr"

    if minutes > 0:
        if seconds > 0:
            return f"{minutes} min {seconds} sec"
        return f"{minutes} min"

    return f"{seconds} sec"
