def calculate_time(distance, speed, traffic_factor):
    """
    Calculate estimated travel time.

    distance: kilometers
    speed: km/h
    traffic_factor:
        Low = 1.0
        Medium = 1.3
        High = 1.7
    """

    if speed <= 0:
        return 0

    time_hours = distance / speed
    time_minutes = time_hours * 60
    estimated_time = time_minutes * traffic_factor

    return round(estimated_time, 1)