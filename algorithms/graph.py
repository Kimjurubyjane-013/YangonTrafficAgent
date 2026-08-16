GRAPH = {
    "Hledan Junction": {
        "Junction Square": 2,
        "Inya Lake": 3,
    },

    "Junction Square": {
        "Hledan Junction": 2,
        "Myanmar Plaza": 4,
        "Yangon General Hospital": 5,
    },

    "Inya Lake": {
        "Hledan Junction": 3,
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
    },

    "Yangon Central Station": {
        "Yangon General Hospital": 4,
        "Sule Pagoda": 2,
    },

    "Sule Pagoda": {
        "Yangon Central Station": 2,
        "Myanmar Plaza": 6,
    },

    "Yangon Airport": {
        "Myanmar Plaza": 5,
        "Inya Lake": 8,
    }
}

LOCATION_COORDS = {
    "Hledan Junction": (16.8168, 96.1297),
    "Junction Square": (16.8172, 96.1314),
    "Inya Lake": (16.8368, 96.1452),
    "Myanmar Plaza": (16.8282, 96.1550),
    "Yangon General Hospital": (16.7789, 96.1481),
    "Yangon Central Station": (16.7817, 96.1613),
    "Sule Pagoda": (16.7744, 96.1588),
    "Yangon Airport": (16.9072, 96.1331),
}


def get_locations():
    return list(GRAPH.keys())