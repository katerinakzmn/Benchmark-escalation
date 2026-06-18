# T015 original buggy code

from collections import deque
def shortest_path_bfs(graph: dict, start: str, goal: str) -> int:
    q = deque([(start, 0)])
    visited = set()
    while q:
        node, dist = q.popleft()
        if node == goal:
            return dist
        visited.add(node)  # BUG: должно быть перед добавлением в очередь
        for nei in graph.get(node, []):
            if nei not in visited:
                q.append((nei, dist + 1))
    return -1
