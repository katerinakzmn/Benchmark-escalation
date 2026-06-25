from collections import deque

def topological_sort(graph: dict) -> list:
    in_degree = {}
    for node in graph:
        if node not in in_degree:
            in_degree[node] = 0
        for nei in graph[node]:
            in_degree[nei] = in_degree.get(nei, 0) + 1

    # стартуем с узлов у которых in_degree > 0 — неверно, нужно == 0
    q = deque([n for n, deg in in_degree.items() if deg > 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for nei in graph.get(node, []):
            in_degree[nei] += 1  # неверно: нужно -= 1
            if in_degree[nei] == 0:
                q.append(nei)
    return order
