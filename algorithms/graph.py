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


# Latitude, Longitude
LOCATION_COORDS = {
    "Hledan Junction": (16.8225, 96.1372),
    "Junction Square": (16.8175, 96.1436),
    "Inya Lake": (16.8235, 96.1602),
    "Myanmar Plaza": (16.8083, 96.1547),
    "Yangon General Hospital": (16.7961, 96.1483),
    "Yangon Central Station": (16.7834, 96.1425),
    "Sule Pagoda": (16.7742, 96.1592),
    "Yangon Airport": (16.9073, 96.1332),
}


def get_locations():
    return list(GRAPH.keys())