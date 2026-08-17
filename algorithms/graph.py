GRAPH = {
    "Hledan Centre": {
        "Junction Square": 1.3,
        "Inya Lake": 3,
    },

    "Junction Square": {
        "Hledan Centre": 1.3,
        "Myanmar Plaza": 4,
        "Yangon General Hospital": 5,
    },

    "Inya Lake": {
        "Hledan Centre": 3,
        "Myanmar Plaza": 3,
        "Yangon Airport": 8,
    },

    "Myanmar Plaza": {
        "Junction Square": 4,
        "Inya Lake": 3,
        "Yangon Airport": 5,
        "Sule Pagoda": 6,
    },

    "Yangon General Hospital": {
        "Junction Square": 5,
        "Yangon Central Station": 4,
        "Junction City": 1,
    },

    "Yangon Central Station": {
        "Yangon General Hospital": 4,
        "Sule Pagoda": 2,
        "Junction City": 1.5,
    },

    "Sule Pagoda": {
        "Yangon Central Station": 2,
        "Myanmar Plaza": 6,
        "Junction City": 1,
    },

    "Junction City": {
        "Yangon General Hospital": 1,
        "Yangon Central Station": 1.5,
        "Sule Pagoda": 1,
    },

    "Yangon Airport": {
        "Myanmar Plaza": 5,
        "Inya Lake": 8,
    }
}

LOCATION_COORDS = {
    # Verified shopping-centre locations from public map records.
    "Hledan Centre": (16.8262, 96.13049),
    "Junction Square": (16.8172, 96.1314),
    "Inya Lake": (16.8368, 96.1452),
    "Myanmar Plaza": (16.8282, 96.1550),
    "Yangon General Hospital": (16.7789, 96.1481),
    "Yangon Central Station": (16.7817, 96.1613),
    "Sule Pagoda": (16.7744, 96.1588),
    "Yangon Airport": (16.9072, 96.1331),
    "Junction City": (16.77896, 96.15427),
}


def get_locations():
    return list(GRAPH.keys())


def validate_graph(graph=GRAPH):
    """Return modelling errors instead of failing later during path traversal."""
    errors = []
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
