"""Compatibility metadata derived from the canonical road repository."""
from services.road_repository import ROAD_REPOSITORY


DEFAULT_ROAD = {"road_class": "arterial", "preferred": False, "one_way": False}
ROAD_METADATA = {}
for road in ROAD_REPOSITORY.roads:
    attributes = {
        "road_id": road.id,
        "road_name": road.road_name,
        "road_class": road.road_type,
        "preferred": road.preferred,
        "one_way": not road.bidirectional,
    }
    ROAD_METADATA[(road.start, road.end)] = attributes
    if road.bidirectional:
        ROAD_METADATA[(road.end, road.start)] = attributes


def road_attributes(start, end, metadata=None):
    source = metadata if metadata is not None else ROAD_METADATA
    attributes = dict(DEFAULT_ROAD)
    attributes.update(source.get((start, end), {}))
    attributes["one_way_ok"] = not attributes.get("one_way", False) or attributes.get("allowed_direction", True)
    return attributes
