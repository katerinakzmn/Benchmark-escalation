"""
llm_client.py - legacy chat client for the original MAS runner.

Backend through the LLM_BACKEND environment variable:
  LLM_BACKEND=mock    - no API key, useful for local checks
  LLM_BACKEND=openai  - OpenAI provider, used by default

If OPENAI_API_KEY is missing, the client falls back to mock.
"""

import os
import json
import random
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

MODEL_WEAK   = "gpt-4o-mini"
MODEL_STRONG = "gpt-4o"
MODEL_REVIEW = "gpt-4o-mini"

_BACKEND = os.getenv("LLM_BACKEND", "openai").lower()

_client = None


def get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY не найден.\n"
                "Используй mock: LLM_BACKEND=mock python mas_runner.py"
            )
        _client = OpenAI(api_key=api_key)
    return _client


_MOCK_FIXES_BY_ENTRY_POINT = {
    "sum_positive": "def sum_positive(numbers):\n    return sum(x for x in numbers if x > 0)\n",
    "count_vowels": "def count_vowels(text):\n    return sum(1 for c in text if c in 'aeiouAEIOU')\n",
    "is_palindrome": "def is_palindrome(s):\n    s = s.lower()\n    return s == s[::-1]\n",
    "reverse_words": "def reverse_words(text):\n    return ' '.join(text.split()[::-1])\n",
    "find_max": "def find_max(numbers):\n    if not numbers:\n        raise ValueError('empty list')\n    return max(numbers)\n",
    "TTLCache": "import time\nclass TTLCache:\n    def __init__(self, ttl):\n        self.ttl = ttl\n        self.store = {}\n    def set(self, key, value):\n        self.store[key] = (value, time.time())\n    def get(self, key):\n        if key not in self.store:\n            return None\n        value, ts = self.store[key]\n        if time.time() - ts > self.ttl:\n            del self.store[key]\n            return None\n        return value\n",
    "flatten_dict": "def flatten_dict(d, parent_key=''):\n    items = {}\n    for k, v in d.items():\n        new_key = f'{parent_key}_{k}' if parent_key else k\n        if isinstance(v, dict):\n            items.update(flatten_dict(v, new_key))\n        else:\n            items[new_key] = v\n    return items\n",
    "most_frequent": "def most_frequent(items):\n    if not items:\n        return None\n    counts = {}\n    for item in items:\n        counts[item] = counts.get(item, 0) + 1\n    return max(counts, key=counts.get)\n",
    "chunk_list": "def chunk_list(lst, size):\n    if size <= 0:\n        raise ValueError('size > 0')\n    return [lst[i:i+size] for i in range(0, len(lst), size)]\n",
    "normalize_scores": "def normalize_scores(scores):\n    if not scores:\n        return []\n    mn, mx = min(scores), max(scores)\n    if mx == mn:\n        return [0.0 for _ in scores]\n    return [(x - mn) / (mx - mn) for x in scores]\n",
    "RateLimiter": "import time\nfrom collections import deque\nclass RateLimiter:\n    def __init__(self, max_calls, window_seconds):\n        self.max_calls = max_calls\n        self.window = window_seconds\n        self.calls = deque()\n    def is_allowed(self):\n        now = time.time()\n        cutoff = now - self.window\n        while self.calls and self.calls[0] < cutoff:\n            self.calls.popleft()\n        if len(self.calls) >= self.max_calls:\n            return False\n        self.calls.append(now)\n        return True\n",
    "LRUCache": "from collections import OrderedDict\nclass LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.cache = OrderedDict()\n    def get(self, key):\n        if key not in self.cache:\n            return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n    def put(self, key, value):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)\n",
    "merge_intervals": "def merge_intervals(intervals):\n    if not intervals:\n        return []\n    intervals = sorted(intervals)\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n        if start <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged\n",
    "topological_sort": "from collections import deque\ndef topological_sort(graph):\n    in_degree = {node: 0 for node in graph}\n    for node in graph:\n        for nei in graph[node]:\n            in_degree[nei] = in_degree.get(nei, 0) + 1\n    q = deque([n for n, d in in_degree.items() if d == 0])\n    order = []\n    while q:\n        node = q.popleft()\n        order.append(node)\n        for nei in graph.get(node, []):\n            in_degree[nei] -= 1\n            if in_degree[nei] == 0:\n                q.append(nei)\n    return order\n",
    "shortest_path_bfs": "from collections import deque\ndef shortest_path_bfs(graph, start, goal):\n    visited = {start}\n    q = deque([(start, 0)])\n    while q:\n        node, dist = q.popleft()\n        if node == goal:\n            return dist\n        for nei in graph.get(node, []):\n            if nei not in visited:\n                visited.add(nei)\n                q.append((nei, dist + 1))\n    return -1\n",
}


def _mock_chat(model: str, system_prompt: str, user_prompt: str) -> str:
    sp = system_prompt.lower()

    if "review" in sp or "ревью" in sp or "качеств" in sp:
        return json.dumps({
            "quality_score":      0.65,
            "issues_found":       ["mock_minor_issue"],
            "recommendation":     "approve",
            "hint_for_developer": "Mock reviewer: looks mostly fine.",
        }, ensure_ascii=False)

    if "developer" in sp or "код" in sp or "исправ" in sp:
        confidence = 0.80 if model == MODEL_STRONG else 0.55
        confidence += random.uniform(-0.05, 0.05)
        fixed_code = _select_mock_fix(user_prompt)
        return json.dumps({
            "fixed_code":  fixed_code,
            "confidence":  round(confidence, 2),
            "cant_solve":  False,
            "explanation": "Mock developer response.",
            "attempt":     1,
        }, ensure_ascii=False)

    return json.dumps({"result": "mock"})


def _select_mock_fix(user_prompt: str) -> str:
    for entry_point, code in _MOCK_FIXES_BY_ENTRY_POINT.items():
        if entry_point in user_prompt:
            return code
    return "def solution(*args, **kwargs):\n    return None\n"


def chat(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    backend = _BACKEND

    if backend == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("[llm_client] OPENAI_API_KEY is missing; using mock backend")
        backend = "mock"

    if backend == "mock":
        return _mock_chat(model, system_prompt, user_prompt)

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()