from algorithms.route_optimizer import find_optimal_route
from algorithms.vehicle import format_duration
from services.prolog_service import get_ai_recommendation


def run_traffic_agent(start, destination, vehicle):

    result = find_optimal_route(
        vehicle=vehicle,
        start=start,
        destination=destination
    )

    if result is None:
        return {"error": "No route found"}

    route = result["route"]
    distance = result["distance"]
    traffic = result["traffic"]
    time = result["time"]

    formatted_time = format_duration(time)

    ai_message = get_ai_recommendation(
        vehicle=vehicle,
        traffic=traffic,
        distance=distance,
        time=formatted_time
    )

    return {
        "vehicle": vehicle,
        "route": route,
        "distance": distance,
        "traffic": traffic,
        "time": time,
        "ai_message": ai_message
    }