"""Deterministic road attributes used by both decision-engine backends.

These are project modelling facts, not claims of live geographic accuracy.
"""

DEFAULT_ROAD = {"road_class": "arterial", "preferred": False, "one_way": False}

ROAD_METADATA = {
    ("Hledan Centre", "Junction Square"): {"road_class": "arterial", "preferred": True},
    ("Junction Square", "Hledan Centre"): {"road_class": "arterial", "preferred": True},
    ("Hledan Centre", "Inya Lake"): {"road_class": "arterial", "preferred": True},
    ("Inya Lake", "Hledan Centre"): {"road_class": "arterial", "preferred": True},
    ("Junction Square", "Myanmar Plaza"): {"road_class": "arterial", "preferred": True},
    ("Myanmar Plaza", "Junction Square"): {"road_class": "arterial", "preferred": True},
    ("Junction Square", "Yangon General Hospital"): {"road_class": "local", "preferred": False},
    ("Yangon General Hospital", "Junction Square"): {"road_class": "local", "preferred": False},
    ("Inya Lake", "Myanmar Plaza"): {"road_class": "arterial", "preferred": True},
    ("Myanmar Plaza", "Inya Lake"): {"road_class": "arterial", "preferred": True},
    ("Inya Lake", "Yangon Airport"): {"road_class": "highway", "preferred": True},
    ("Yangon Airport", "Inya Lake"): {"road_class": "highway", "preferred": True},
    ("Myanmar Plaza", "Yangon Airport"): {"road_class": "highway", "preferred": True},
    ("Yangon Airport", "Myanmar Plaza"): {"road_class": "highway", "preferred": True},
    ("Junction City", "Sule Pagoda"): {"road_class": "arterial", "preferred": True},
    ("Sule Pagoda", "Junction City"): {"road_class": "arterial", "preferred": True},
    ("Junction City", "Yangon General Hospital"): {"road_class": "local", "preferred": True},
    ("Yangon General Hospital", "Junction City"): {"road_class": "local", "preferred": True},
}


def road_attributes(start, end, metadata=None):
    source = metadata if metadata is not None else ROAD_METADATA
    attributes = dict(DEFAULT_ROAD)
    attributes.update(source.get((start, end), {}))
    attributes["one_way_ok"] = not attributes.get("one_way", False) or attributes.get("allowed_direction", True)
    return attributes
