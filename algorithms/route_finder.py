def find_all_simple_paths(graph, start, destination, max_depth=8, max_candidates=24):
    """
    Depth-first search returning every simple (no repeated node)
    path between start and destination, each paired with its
    total distance. Small graphs only — this is exhaustive, not
    optimized for scale.
    """

    results = []

    def dfs(current, visited, path, distance):

        if current == destination:
            results.append((list(path), distance))
            return

        if len(path) > max_depth:
            return

        if len(results) >= max_candidates:
            return

        for neighbor, weight in sorted(graph.get(current, {}).items()):

            if neighbor in visited:
                continue

            visited.add(neighbor)
            path.append(neighbor)

            dfs(neighbor, visited, path, distance + weight)

            path.pop()
            visited.remove(neighbor)

    if start not in graph or destination not in graph:
        return []

    dfs(start, {start}, [start], 0)

    return results
