VEHICLE_SPEED = {
    "Car": 40,
    "Taxi": 40,
    "Bus": 25,
    "Motorcycle": 45,
    "Ambulance": 60,
    "Fire Truck": 55,
    "Police": 60,
    "Bicycle": 15,
    "Walking": 5
}


def calculate_time(distance, vehicle, multiplier=1.0):

    speed = VEHICLE_SPEED.get(vehicle, 30)

    minutes = (distance / speed) * 60

    return round(minutes * multiplier, 1)


def format_duration(minutes):

    if minutes < 60:
        return f"{minutes:.1f} min"

    hours = int(minutes // 60)

    mins = int(minutes % 60)

    return f"{hours} hr {mins} min"