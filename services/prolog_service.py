"""Backward-compatible recommendation helper.

Core route decisions live in RouteDecisionEngine. This legacy function remains
for older UI/tests and deliberately has no hard dependency on PySwip.
"""


def get_ai_recommendation(vehicle, traffic, distance, time):
    vehicle = str(vehicle).strip().title()
    traffic = str(traffic).strip().title()
    action = {
        "Heavy": "Prefer a lower-congestion eligible route.",
        "Moderate": "Allow for moderate delays.",
        "Light": "Normal routing conditions apply.",
    }.get(traffic, "Use standard route caution.")
    return (
        "Route Assessment\n\n"
        f"Vehicle: {vehicle}\nTraffic Condition: {traffic}\n"
        f"Distance: {float(distance):.1f} km\nEstimated Time: {time}\n\n"
        f"- Priority Action\n{action}"
    )
