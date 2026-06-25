"""
Mock backend - deterministic responses without an API key.
Сценарии берутся из configs/mock.yaml (или дефолтные).
"""
import yaml
import os

# Сценарии: какой тир решает какую задачу
# human всегда решает — он дорогой надёжный фоллбэк (правка 0.1)
_DEFAULT_SCENARIOS = {
    "T001": {"weak": "solve",  "strong": "solve"},
    "T002": {"weak": "fail",   "strong": "solve"},
    "T003": {"weak": "fail",   "strong": "fail"},
    "T004": {"weak": "fail",   "strong": "solve"},
    "T005": {"weak": "solve",  "strong": "solve"},
    "T006": {"weak": "fail",   "strong": "solve"},
    "T007": {"weak": "fail",   "strong": "fail"},
    "T008": {"weak": "solve",  "strong": "solve"},
    "T009": {"weak": "fail",   "strong": "solve"},
    "T010": {"weak": "fail",   "strong": "fail"},
    "T011": {"weak": "fail",   "strong": "fail"},
    "T012": {"weak": "fail",   "strong": "solve"},
    "T013": {"weak": "fail",   "strong": "solve"},
    "T014": {"weak": "fail",   "strong": "fail"},
    "T015": {"weak": "fail",   "strong": "fail"},
}

# Готовые фиксы для каждой задачи
_FIXES = {
    "T001": "def sum_positive(numbers):\n    return sum(x for x in numbers if x > 0)\n",
    "T002": "def count_vowels(text):\n    return sum(1 for c in text if c in 'aeiouAEIOU')\n",
    "T003": "def is_palindrome(s):\n    s = s.lower()\n    return s == s[::-1]\n",
    "T004": "def reverse_words(text):\n    return ' '.join(text.split()[::-1])\n",
    "T005": "def find_max(numbers):\n    if not numbers:\n        raise ValueError('empty list')\n    return max(numbers)\n",
    "T006": "import time\nclass TTLCache:\n    def __init__(self, ttl):\n        self.ttl = ttl\n        self.store = {}\n    def set(self, key, value):\n        self.store[key] = (value, time.time())\n    def get(self, key):\n        if key not in self.store:\n            return None\n        value, ts = self.store[key]\n        if time.time() - ts > self.ttl:\n            del self.store[key]\n            return None\n        return value\n",
    "T007": "def flatten_dict(d, parent_key=''):\n    items = {}\n    for k, v in d.items():\n        new_key = f'{parent_key}_{k}' if parent_key else k\n        if isinstance(v, dict):\n            items.update(flatten_dict(v, new_key))\n        else:\n            items[new_key] = v\n    return items\n",
    "T008": "def most_frequent(items):\n    if not items:\n        return None\n    counts = {}\n    for item in items:\n        counts[item] = counts.get(item, 0) + 1\n    return max(counts, key=counts.get)\n",
    "T009": "def chunk_list(lst, size):\n    if size <= 0:\n        raise ValueError('size > 0')\n    return [lst[i:i+size] for i in range(0, len(lst), size)]\n",
    "T010": "def normalize_scores(scores):\n    if not scores:\n        return []\n    mn, mx = min(scores), max(scores)\n    if mx == mn:\n        return [0.0 for _ in scores]\n    return [(x - mn) / (mx - mn) for x in scores]\n",
    "T011": "import time\nfrom collections import deque\nclass RateLimiter:\n    def __init__(self, max_calls, window_seconds):\n        self.max_calls = max_calls\n        self.window = window_seconds\n        self.calls = deque()\n    def is_allowed(self):\n        now = time.time()\n        cutoff = now - self.window\n        while self.calls and self.calls[0] < cutoff:\n            self.calls.popleft()\n        if len(self.calls) >= self.max_calls:\n            return False\n        self.calls.append(now)\n        return True\n",
    "T012": "from collections import OrderedDict\nclass LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.cache = OrderedDict()\n    def get(self, key):\n        if key not in self.cache:\n            return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n    def put(self, key, value):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)\n",
    "T013": "def merge_intervals(intervals):\n    if not intervals:\n        return []\n    intervals = sorted(intervals)\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n        if start <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged\n",
    "T014": "from collections import deque\ndef topological_sort(graph):\n    in_degree = {node: 0 for node in graph}\n    for node in graph:\n        for nei in graph[node]:\n            in_degree[nei] = in_degree.get(nei, 0) + 1\n    q = deque([n for n, d in in_degree.items() if d == 0])\n    order = []\n    while q:\n        node = q.popleft()\n        order.append(node)\n        for nei in graph.get(node, []):\n            in_degree[nei] -= 1\n            if in_degree[nei] == 0:\n                q.append(nei)\n    return order\n",
    "T015": "from collections import deque\ndef shortest_path_bfs(graph, start, goal):\n    visited = {start}\n    q = deque([(start, 0)])\n    while q:\n        node, dist = q.popleft()\n        if node == goal:\n            return dist\n        for nei in graph.get(node, []):\n            if nei not in visited:\n                visited.add(nei)\n                q.append((nei, dist + 1))\n    return -1\n",
}

_BROKEN_CODE = "# mock: broken code\ndef placeholder(): raise NotImplementedError\n"


class MockBackend:
    def __init__(self, config_path: str = "configs/mock.yaml"):
        self.scenarios = _DEFAULT_SCENARIOS.copy()
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "mock_scenarios" in data:
                self.scenarios.update(data["mock_scenarios"])

    def generate(self, task_id: str, tier: str, prompt: str = "") -> str:
        # human всегда решает
        if tier == "human":
            return _FIXES.get(task_id, _BROKEN_CODE)

        scenario = self.scenarios.get(task_id, {})
        outcome = scenario.get(tier, "fail")
        if outcome == "solve":
            return _FIXES.get(task_id, _BROKEN_CODE)
        return _BROKEN_CODE

    def review(self, task_id: str, code: str, tier: str = "weak") -> dict:
        """Детерминированный review в зависимости от tier."""
        # human всегда даёт высокий confidence
        if tier == "human":
            return {"issues": [], "confidence": 1.0, "approved": True}

        scenario = self.scenarios.get(task_id, {})
        outcome = scenario.get(tier, "fail")
        if outcome == "solve":
            return {"issues": [], "confidence": 0.9, "approved": True}
        return {
            "issues": ["Logic error detected by mock reviewer"],
            "confidence": 0.3,
            "approved": False,
        }