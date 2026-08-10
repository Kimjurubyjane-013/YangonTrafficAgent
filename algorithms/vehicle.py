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