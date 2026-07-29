from algorithms.route_optimizer import find_optimal_route
from agent.llm import ask_llm


def run_traffic_agent(
        start,
        destination,
        vehicle
):

    # 1. Get optimal route using A*
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
    time = result["time"]


    # 2. Ask AI to explain traffic
    prompt = f"""
You are a Yangon traffic management AI agent.

Vehicle:
{vehicle}

Route:
{route}

Distance:
{distance} km

Estimated time:
{time} minutes


Analyze traffic conditions in Yangon.
Give a short recommendation.
"""


    ai_response = ask_llm(prompt)


    # 3. Return complete result

    return {

        "route": route,

        "distance": distance,

        "time": time,

        "ai_message": ai_response

    }