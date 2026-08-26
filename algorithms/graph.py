"""Compatibility graph derived from the canonical JSON road repository."""
from services.road_repository import ROAD_REPOSITORY


LOCATION_COORDS = dict(ROAD_REPOSITORY.locations)
GRAPH = {name: {} for name in LOCATION_COORDS}
for road in ROAD_REPOSITORY.roads:
    GRAPH[road.start][road.end] = road.distance_km
    if road.bidirectional:
        GRAPH[road.end][road.start] = road.distance_km


def get_locations():
    return list(LOCATION_COORDS)


def validate_graph(graph=GRAPH):
    """Return modelling errors instead of failing later during traversal."""
    errors = []
    if not isinstance(graph, dict) or not graph:
        return ["graph must be a non-empty mapping"]
    for start, neighbors in graph.items():
        if not isinstance(neighbors, dict):
            errors.append(f"{start}: neighbors must be a mapping")
            continue
        for end, distance in neighbors.items():
            if end not in graph:
                errors.append(f"{start}: unknown neighbor {end}")
            if not isinstance(distance, (int, float)) or distance <= 0:
                errors.append(f"{start}->{end}: distance must be positive")
    return errors
