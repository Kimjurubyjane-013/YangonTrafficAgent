from algorithms.route_optimizer import find_optimal_route
from algorithms.traffic import (
    get_multiplier
)
from algorithms.vehicle import (
    calculate_time
)



def generate_ai_recommendation(
        vehicle,
        route,
        distance,
        traffic,
        time
):

    if traffic == "Light":

        advice = (
            "Traffic condition is light. "
            "This route is suitable for normal travel."
        )


    elif traffic == "Moderate":

        advice = (
            "Moderate traffic detected. "
            "Consider leaving earlier to avoid delays."
        )


    else:

        advice = (
            "Heavy traffic detected. "
            "Consider another departure time "
            "or alternative transportation."
        )


    return f"""Route Analysis:

✓ Vehicle: {vehicle}

✓ Distance: {distance:.1f} km

✓ Traffic Condition: {traffic}

✓ Estimated Arrival: {time}


Recommendation:

{advice}
"""




def run_traffic_agent(
        start,
        destination,
        vehicle
):


    # 1. Find optimal route using A*

    result = find_optimal_route(
        vehicle=vehicle,
        start=start,
        destination=destination
    )


    if result is None:

        return {
            "error": "No route found"
        }



    route = result["route"]

    distance = result["distance"]

    traffic = result.get(
        "traffic",
        "Light"
    )



    # 2. Recalculate ETA with traffic

    multiplier = get_multiplier(
        traffic
    )


    time = calculate_time(
        distance,
        vehicle,
        multiplier
    )



    # 3. Generate AI recommendation

    ai_message = generate_ai_recommendation(
        vehicle,
        route,
        distance,
        traffic,
        time
    )



    # 4. Return final result

    return {

        "vehicle": vehicle,

        "route": route,

        "distance": distance,

        "traffic": traffic,

        "time": time,

        "ai_message": ai_message
    }