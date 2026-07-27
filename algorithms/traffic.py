import random


def get_traffic_level():
    levels = {
        "Low": 1.0,
        "Medium": 1.3,
        "High": 1.7
    }

    level = random.choice(list(levels.keys()))

    return level, levels[level]