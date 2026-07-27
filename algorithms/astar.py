import heapq
from math import radians, sin, cos, sqrt, atan2


EARTH_RADIUS_KM = 6371.0


def haversine_distance(coord1, coord2):
    """
    Great-circle distance in kilometers between two
    (latitude, longitude) points. Used as the A* heuristic,
    matching the unit (km) of the graph's edge weights.
    """

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def astar(graph, coords, start, destination):
    """
    A* search over `graph` (adjacency dict of edge weights),
    using straight-line haversine distance from `coords` as the
    heuristic. Returns (path, distance), or (None, None) if no
    path exists.
    """

    open_set = [(0, start)]

    g_score = {
        node: float("inf")
        for node in graph
    }

    g_score[start] = 0

    previous = {}

    visited = set()

    while open_set:

        _, current_node = heapq.heappop(open_set)

        if current_node in visited:
            continue

        visited.add(current_node)

        if current_node == destination:
            break

        for neighbor, weight in graph[current_node].items():

            tentative_g = g_score[current_node] + weight

            if tentative_g < g_score[neighbor]:

                g_score[neighbor] = tentative_g
                previous[neighbor] = current_node

                heuristic = haversine_distance(
                    coords[neighbor],
                    coords[destination]
                )

                f_score = tentative_g + heuristic

                heapq.heappush(
                    open_set,
                    (f_score, neighbor)
                )

    if g_score[destination] == float("inf"):
        # No path exists between start and destination
        return None, None

    path = []

    current = destination

    while current in previous:

        path.insert(0, current)

        current = previous[current]

    path.insert(0, start)

    return path, g_score[destination]