# algorithms/vehicle.py


# Average speed (km/h)
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



def get_vehicle_speed(vehicle):

    """
    Get average speed of selected vehicle.

    Returns:
        speed in km/h
    """

    return VEHICLE_SPEED.get(
        vehicle,
        30
    )



def calculate_time(
        distance,
        vehicle,
        multiplier=1.0
):

    """
    Calculate estimated travel time.

    Args:
        distance:
            distance in km

        vehicle:
            vehicle type

        multiplier:
            traffic effect

            Example:
            Light traffic = 1.0
            Medium traffic = 1.2
            Heavy traffic = 1.5


    Returns:
        travel time in minutes
    """


    if distance <= 0:

        return 0



    speed = get_vehicle_speed(
        vehicle
    )


    minutes = (
        distance / speed
    ) * 60


    minutes *= multiplier


    return round(
        minutes,
        1
    )



def format_duration(minutes):

    """
    Convert minutes into human readable format.

    Example:

    7.5  -> 8 min

    65   -> 1 hr 5 min

    """


    if minutes is None:

        return "Unknown"



    minutes = float(minutes)



    if minutes < 1:

        seconds = int(
            minutes * 60
        )

        return f"{seconds} sec"



    total_minutes = round(
        minutes
    )


    hours = total_minutes // 60

    remaining = total_minutes % 60



    if hours > 0:

        if remaining > 0:

            return (
                f"{hours} hr "
                f"{remaining} min"
            )

        else:

            return (
                f"{hours} hr"
            )



    return f"{remaining} min"