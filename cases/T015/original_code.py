from collections import deque

def shortest_path_bfs(graph: dict, start: str, goal: str) -> int:
    q = deque([(start, 0)])
    visited = set()
    while q:
        node, dist = q.popleft()
        if node in visited:
            continue
        visited.add(node)
        if node == goal:
            return dist
        for nei in graph.get(node, []):
            q.append((nei, dist + 1))
    return -1