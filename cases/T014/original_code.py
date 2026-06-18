from collections import deque
def topological_sort(graph: dict) -> list:
    in_degree = {node: 0 for node in graph}
    for node in graph:
        for nei in graph[node]:
            in_degree[nei] = in_degree.get(nei, 0) + 1
    q = deque([n for n, deg in in_degree.items() if deg == 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for nei in graph.get(node, []):
            in_degree[nei] += 1  # BUG: должно быть -= 1
            if in_degree[nei] == 0:
                q.append(nei)
    return order
