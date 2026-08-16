import hashlib
from datetime import datetime

from algorithms.graph import GRAPH
from algorithms.route_finder import find_all_simple_paths
from algorithms.vehicle import calculate_time


TRAFFIC_MULTIPLIER = {
    "Light": 1.0,
    "Moderate": 1.4,
    "Heavy": 1.9
}

MAX_ROUTE_OPTIONS = 4


def _segment_traffic_for_edge(place_a, place_b, weight):
    """
    Deterministic traffic level for a single edge: the same edge,
    in the same hour, always returns the same result — no more
    "changes every time you click" behavior. It only shifts once
    the real-world hour changes, giving a stable but still
    time-of-day-aware traffic pattern instead of pure randomness.
    """

    hour_bucket = datetime.now().strftime("%Y-%m-%d-%H")
    seed_key = f"{place_a}|{place_b}|{hour_bucket}"

    digest = hashlib.sha256(seed_key.encode()).hexdigest()
    roll = int(digest[:8], 16) / 0xFFFFFFFF  # deterministic float in [0, 1)

    if weight <= 3:
        thresholds = [0.6, 0.9]   # Light, Moderate, Heavy

    elif weight <= 6:
        thresholds = [0.35, 0.75]

    else:
        thresholds = [0.2, 0.55]

    if roll < thresholds[0]:
        return "Light"

    if roll < thresholds[1]:
        return "Moderate"

    return "Heavy"


def _build_route_option(path, distance, vehicle):

    segment_traffic = [
        _segment_traffic_for_edge(path[i], path[i + 1], GRAPH[path[i]][path[i + 1]])
        for i in range(len(path) - 1)
    ]

    avg_multiplier = sum(
        TRAFFIC_MULTIPLIER[t] for t in segment_traffic
    ) / len(segment_traffic)

    # Worst segment sets the overall traffic label — a single
    # heavy leg is worth calling out even if the rest is clear
    overall_traffic = max(
        segment_traffic,
        key=lambda t: TRAFFIC_MULTIPLIER[t]
    )

    base_time = calculate_time(distance, vehicle)
    adjusted_time = round(base_time * avg_multiplier, 1)

    # Ranking cost: favors routes that avoid traffic, not just
    # the shortest distance
    cost = distance * avg_multiplier

    return {
        "route": path,
        "distance": round(distance, 1),
        "time": adjusted_time,
        "traffic": overall_traffic,
        "segment_traffic": segment_traffic,
        "_cost": cost
    }


def _get_ai_message(vehicle, best, num_alternatives):

    traffic = best["traffic"]
    distance = best["distance"]
    time = best["time"]

    lines = [
        "🎯 Route Assessment",
        "",
        f"Vehicle: {vehicle.lower()}",
        f"Traffic Condition: {traffic.lower()}",
        f"Distance: {distance} km",
        f"Estimated Time: {round(time)} min",
        ""
    ]

    lines.append("- Priority Action")

    if traffic == "Heavy":
        lines.append("Consider an alternative route or delay travel if possible.")

    elif traffic == "Moderate":
        lines.append("Fastest available route, moderate delays possible.")

    else:
        lines.append("Fastest available route.")

    lines.append("")
    lines.append("- Distance Insight")

    if distance <= 4:
        lines.append("Short trip - minimal travel time expected.")

    elif distance <= 8:
        lines.append("Medium-length trip - plan for normal travel time.")

    else:
        lines.append("Longer trip - allow extra time.")

    lines.append("")
    lines.append("- Safety Note")

    if traffic == "Heavy":
        lines.append("Drive cautiously, congestion increases accident risk.")

    else:
        lines.append("Traffic conditions are favorable for normal driving.")

    if num_alternatives > 0:
        lines.append("")
        lines.append(f"- {num_alternatives} alternative route(s) available in the panel.")

    return "\n".join(lines)


def run_traffic_agent(start, destination, vehicle):
    """
    Returns:
    {
        route, distance, time, traffic, segment_traffic,
        alternatives: [ {route, distance, time, traffic, segment_traffic}, ... ],
        ai_message
    }
    or {"error": "..."} if no route exists.
    """

    if start == destination:
        return {"error": "Start and destination must be different."}

    if start not in GRAPH or destination not in GRAPH:
        return {"error": "Unknown location."}

    raw_paths = find_all_simple_paths(GRAPH, start, destination)

    if not raw_paths:
        return {
            "error": f"No route found between {start} and {destination}."
        }

    options = [
        _build_route_option(path, distance, vehicle)
        for path, distance in raw_paths
    ]

    # Best (lowest traffic-adjusted cost) first
    options.sort(key=lambda o: o["_cost"])

    options = options[:MAX_ROUTE_OPTIONS]

    for option in options:
        option.pop("_cost", None)

    best = options[0]
    alternatives = options[1:]

    ai_message = _get_ai_message(vehicle, best, len(alternatives))

    return {
        "route": best["route"],
        "distance": best["distance"],
        "time": best["time"],
        "traffic": best["traffic"],
        "segment_traffic": best["segment_traffic"],
        "alternatives": alternatives,
        "ai_message": ai_message
    }